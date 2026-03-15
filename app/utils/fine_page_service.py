from collections import defaultdict
from datetime import datetime
import json
import os

from flask import current_app
from sqlalchemy import desc, func

from app.models import CashTransaction, Fine, FineVote, User, VoteHistory, db
from app.utils.fine_service import calculate_vote_quorum, check_and_apply_late_fees, check_and_close_expired_votes, get_eligible_voter_ids


def _approved_fines_filter():
    return (Fine.pending_approval == False) | (Fine.pending_approval == None)


def _resolve_month_range(filter_month, now):
    if filter_month != 'all':
        try:
            year, month = map(int, filter_month.split('-'))
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            return start, end, filter_month
        except ValueError:
            pass

    start = datetime(now.year, now.month, 1)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1)
    else:
        end = datetime(now.year, now.month + 1, 1)
    return start, end, now.strftime('%Y-%m')


def build_fines_page_context(current_user, filter_month='all', filter_person='all', now=None):
    now = now or datetime.now()
    # Questo context è anche il punto di "manutenzione" della pagina multe:
    # prima di renderizzare, applica more automatiche e chiude eventuali votazioni scadute.
    check_and_apply_late_fees()
    check_and_close_expired_votes()

    approved_fines_filter = _approved_fines_filter()

    totale_pagate = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        approved_fines_filter,
    ).scalar() or 0.0

    totale_contanti = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        Fine.payment_method == 'contanti',
        approved_fines_filter,
    ).scalar() or 0.0

    totale_paypal = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        Fine.payment_method == 'paypal',
        approved_fines_filter,
    ).scalar() or 0.0

    totale_cassa = db.session.query(func.sum(Fine.amount)).filter(
        approved_fines_filter,
    ).scalar() or 0.0

    registro_query = Fine.query.filter(approved_fines_filter)

    if filter_month != 'all':
        try:
            year, month = map(int, filter_month.split('-'))
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1)
            else:
                last_day = datetime(year, month + 1, 1)
            registro_query = registro_query.filter(Fine.date >= first_day, Fine.date < last_day)
        except ValueError:
            pass

    if filter_person != 'all':
        try:
            registro_query = registro_query.filter(Fine.user_id == int(filter_person))
        except ValueError:
            pass

    registro_multe = registro_query.order_by(Fine.paid.asc(), desc(Fine.date)).all()
    has_regulation = os.path.exists(os.path.join(current_app.config['FILES_UPLOAD_FOLDER'], 'regolamento.pdf'))

    denunce_in_attesa = Fine.query.filter(Fine.pending_approval == True).order_by(desc(Fine.date)).all()
    denunce_in_votazione = Fine.query.filter(Fine.voting_active == True).order_by(desc(Fine.voting_end)).all()
    # Precarichiamo i denuncianti in blocco per evitare lookup puntuali dal template.
    denunciante_ids = {denuncia.denunciante_id for denuncia in denunce_in_attesa if denuncia.denunciante_id}
    denuncianti_by_id = {}
    if denunciante_ids:
        denuncianti_by_id = {
            user.id: user
            for user in User.query.filter(User.id.in_(denunciante_ids)).all()
        }

    user_votes = {}
    vote_counts = {}
    excluded_voters_data = {}
    quorum_per_vote = {}
    eligible_voter_ids = get_eligible_voter_ids()
    eligible_voters = len(eligible_voter_ids)

    for denuncia in denunce_in_votazione:
        user_vote = FineVote.query.filter_by(fine_id=denuncia.id, user_id=current_user.id).first()
        user_votes[denuncia.id] = user_vote.vote if user_vote else None

        vote_counts[denuncia.id] = {
            'approve': FineVote.query.filter_by(fine_id=denuncia.id, vote=True).count(),
            'reject': FineVote.query.filter_by(fine_id=denuncia.id, vote=False).count(),
        }

        quorum_value, excluded = calculate_vote_quorum(denuncia, eligible_voter_ids)
        excluded_voters_data[denuncia.id] = excluded
        quorum_per_vote[denuncia.id] = quorum_value

    # Il quorum standard è ancora utile alla UI per spiegare la regola generale,
    # ma ogni singola votazione usa quorum_per_vote perché gli esclusi possono cambiare il conteggio.
    quorum = max(1, ((eligible_voters - 1) // 2) + 1)

    last_dates_query = db.session.query(func.strftime('%Y-%m-%d', Fine.date)).filter(
        approved_fines_filter,
    ).distinct().order_by(desc(func.strftime('%Y-%m-%d', Fine.date))).limit(2).all()
    last_dates = [item[0] for item in last_dates_query]

    if last_dates:
        ultime_sanzioni = Fine.query.filter(
            func.strftime('%Y-%m-%d', Fine.date).in_(last_dates),
            approved_fines_filter,
            (Fine.voting_active == False) | (Fine.voting_active == None),
        ).order_by(desc(Fine.date)).all()
    else:
        ultime_sanzioni = []

    months_with_fines = db.session.query(
        func.strftime('%Y-%m', Fine.date).label('month')
    ).distinct().order_by(desc('month')).all()
    available_months = [item[0] for item in months_with_fines]

    classifica_generale = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        approved_fines_filter,
    ).group_by(User.id).order_by(desc('total')).all()

    m_start, m_end, month_label = _resolve_month_range(filter_month, now)
    classifica_mensile = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        Fine.date >= m_start,
        Fine.date < m_end,
        approved_fines_filter,
    ).group_by(User.id).order_by(desc('total')).all()

    transazioni = CashTransaction.query.order_by(desc(CashTransaction.date)).all()
    totale_uscite = db.session.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == 'uscita'
    ).scalar() or 0.0
    totale_entrate_manuali = db.session.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == 'entrata'
    ).scalar() or 0.0
    saldo_cassa = totale_pagate + totale_entrate_manuali - totale_uscite

    elenco_giocatori = User.query.order_by(User.nome_completo).all()
    votanti_eleggibili = User.query.filter(
        User.is_coach.isnot(True),
        User.is_presidente.isnot(True),
    ).order_by(User.nome_completo).all()

    storico_votazioni = VoteHistory.query.order_by(desc(VoteHistory.closed_at)).all()
    for storico in storico_votazioni:
        try:
            storico.non_voters_list = json.loads(storico.non_voters or '[]')
        except (TypeError, ValueError, json.JSONDecodeError):
            storico.non_voters_list = []

    return {
        'totale_cassa': totale_cassa,
        'totale_pagate': totale_pagate,
        'totale_contanti': totale_contanti,
        'totale_paypal': totale_paypal,
        'saldo_cassa': saldo_cassa,
        'totale_uscite': totale_uscite,
        'totale_entrate_manuali': totale_entrate_manuali,
        'transazioni': transazioni,
        'registro_multe': registro_multe,
        'ultime_sanzioni': ultime_sanzioni,
        'denunce_in_attesa': denunce_in_attesa,
        'denunce_in_votazione': denunce_in_votazione,
        'denuncianti_by_id': denuncianti_by_id,
        'user_votes': user_votes,
        'vote_counts': vote_counts,
        'eligible_voters': eligible_voters,
        'quorum': quorum,
        'excluded_voters_data': excluded_voters_data,
        'quorum_per_vote': quorum_per_vote,
        'votanti_eleggibili': votanti_eleggibili,
        'storico_votazioni': storico_votazioni,
        'elenco_giocatori': elenco_giocatori,
        'now': now,
        'has_regulation': has_regulation,
        'filter_month': filter_month,
        'filter_person': filter_person,
        'available_months': available_months,
        'classifica_generale': classifica_generale,
        'classifica_mensile': classifica_mensile,
        'month_label': month_label,
    }


def build_fine_stats_context():
    approved_fines = Fine.query.filter(_approved_fines_filter()).all()

    fines_per_month = defaultdict(lambda: {'count': 0, 'total': 0})
    for fine in approved_fines:
        month_key = fine.date.strftime('%Y-%m')
        fines_per_month[month_key]['count'] += 1
        fines_per_month[month_key]['total'] += fine.amount

    sorted_months = sorted(fines_per_month.keys(), reverse=True)[:12]
    sorted_months.reverse()

    fines_per_player = db.session.query(
        User.soprannome, User.nome_completo, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        _approved_fines_filter(),
    ).group_by(User.id).order_by(desc('total')).all()

    top_reporters = db.session.query(
        User.soprannome, User.nome_completo, func.count(Fine.id).label('count')
    ).join(Fine, Fine.denunciante_id == User.id).filter(
        Fine.denunciante_id != None,
    ).group_by(User.id).order_by(desc('count')).limit(5).all()

    fine_ranges = {
        '€0-5': 0,
        '€5-10': 0,
        '€10-20': 0,
        '€20+': 0,
    }
    for fine in approved_fines:
        if fine.amount < 5:
            fine_ranges['€0-5'] += 1
        elif fine.amount < 10:
            fine_ranges['€5-10'] += 1
        elif fine.amount < 20:
            fine_ranges['€10-20'] += 1
        else:
            fine_ranges['€20+'] += 1

    return {
        'mesi_multe': sorted_months,
        'multe_count_per_mese': [fines_per_month[month]['count'] for month in sorted_months],
        'multe_importo_per_mese': [fines_per_month[month]['total'] for month in sorted_months],
        'multe_per_giocatore': fines_per_player,
        'denunciatori': top_reporters,
        'multa_ranges': fine_ranges,
    }
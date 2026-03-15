import json
from datetime import datetime, timedelta

from sqlalchemy import desc, func

from app.models import Fine, FineVote, GlobalSettings, Notification, User, db
from app.utils.fine_report_service import build_fine_change_details, build_fine_snapshot, log_fine_report_event
from app.utils.main_services import ValidationError, normalize_payment_method, parse_denuncia_form
from app.utils.notifications import crea_notifica, get_nome_giocatore


class FineWorkflowError(ValueError):
    pass


def submit_denuncia(actor, form, now=None, notifier=crea_notifica):
    now = now or datetime.now()
    denuncia_data = parse_denuncia_form(form)

    # Il limite giornaliero va verificato sulla data di creazione della denuncia,
    # non sulla data dell'infrazione, altrimenti sarebbe aggirabile con date retroattive.
    today_key = f'denunce_daily_count_{actor.id}_{now.date().isoformat()}'
    daily_counter = GlobalSettings.query.filter_by(key=today_key).first()
    denunce_oggi = int((daily_counter.value or '0').strip()) if daily_counter and daily_counter.value else 0

    if denunce_oggi >= 3:
        raise FineWorkflowError('Hai raggiunto il limite massimo di 3 denunce per oggi!')

    fine = Fine(
        user_id=denuncia_data['user'].id,
        amount=denuncia_data['amount'],
        reason=denuncia_data['reason'],
        date=denuncia_data['date'],
        deadline=denuncia_data['deadline'],
        pending_approval=True,
        denunciante_id=actor.id,
        note=denuncia_data['note'],
    )
    db.session.add(fine)
    if not daily_counter:
        daily_counter = GlobalSettings(key=today_key)
        db.session.add(daily_counter)
    daily_counter.value = str(denunce_oggi + 1)
    db.session.commit()

    denunciato_nome = get_nome_giocatore(denuncia_data['user'])
    denunciante_nome = get_nome_giocatore(actor)
    message = f"⚖️ {denunciante_nome} ha denunciato {denunciato_nome}. Motivazione: {denuncia_data['reason']}"
    if denuncia_data['note']:
        message += f" | Note: {denuncia_data['note']}"
    message += ' (in attesa di approvazione)'

    notifier('denuncia', message, icon='⚖️')
    return fine, denuncia_data['user']


def mark_fine_paid(fine, actor, payment_method_value, notifier=crea_notifica):
    metodo = normalize_payment_method(payment_method_value, required=True)
    before_snapshot = build_fine_snapshot(fine)

    fine.paid = True
    fine.payment_method = metodo
    giocatore = db.session.get(User, fine.user_id)
    after_snapshot = build_fine_snapshot(fine)
    log_fine_report_event(
        'mark_fine_paid',
        actor=actor,
        fine=fine,
        target_user=giocatore,
        details={
            'before': before_snapshot,
            'after': after_snapshot,
            'changes': build_fine_change_details(before_snapshot, after_snapshot),
        },
    )
    db.session.commit()
    _notify_donator_rankings(fine, notifier=notifier)
    return metodo


def approve_denuncia(fine, actor, notifier=crea_notifica):
    if not fine or not fine.pending_approval:
        raise FineWorkflowError('Denuncia non trovata o già elaborata.')

    before_snapshot = build_fine_snapshot(fine)
    fine.pending_approval = False

    multato = db.session.get(User, fine.user_id)
    if multato:
        multato.current_streak = 0

    after_snapshot = build_fine_snapshot(fine)
    log_fine_report_event(
        'approve_denuncia',
        actor=actor,
        fine=fine,
        target_user=multato,
        details={
            'before': before_snapshot,
            'after': after_snapshot,
            'changes': build_fine_change_details(before_snapshot, after_snapshot),
        },
    )
    db.session.commit()

    notifier(
        'denuncia_approvata',
        f"✅ La denuncia contro {get_nome_giocatore(multato)} è stata approvata. Motivazione: {fine.reason}",
        icon='✅',
    )
    return multato


def reject_denuncia(fine, actor, notifier=crea_notifica):
    if not fine or not fine.pending_approval:
        raise FineWorkflowError('Denuncia non trovata o già elaborata.')

    multato = db.session.get(User, fine.user_id)
    log_fine_report_event(
        'reject_denuncia',
        actor=actor,
        fine_id=fine.id,
        target_user=multato,
        details={'before': build_fine_snapshot(fine)},
    )
    reason = fine.reason
    multato_nome = get_nome_giocatore(multato)

    db.session.delete(fine)
    db.session.commit()

    notifier(
        'denuncia_rifiutata',
        f"❌ La denuncia contro {multato_nome} è stata rifiutata. Motivazione originale: {reason}",
        icon='❌',
    )
    return multato_nome, reason


def withdraw_denuncia(fine, actor, withdrawal_note, notifier=crea_notifica):
    if not fine or not fine.pending_approval or fine.denunciante_id != actor.id:
        raise FineWorkflowError('Non puoi ritirare questa denuncia.')

    multato = db.session.get(User, fine.user_id)
    multato_nome = get_nome_giocatore(multato)
    denunciante_nome = get_nome_giocatore(actor)
    reason = fine.reason
    withdrawal_note = (withdrawal_note or '').strip()

    db.session.delete(fine)
    db.session.commit()

    message = f"🔙 {denunciante_nome} ha ritirato la denuncia contro {multato_nome}. Motivazione originale: {reason}"
    if withdrawal_note:
        message += f" | Motivo del ritiro: {withdrawal_note}"
    notifier('denuncia_ritirata', message, icon='🔙')
    return message


def start_denuncia_vote(fine, actor, now=None, notifier=crea_notifica):
    if not fine or not fine.pending_approval:
        raise FineWorkflowError('Denuncia non trovata o già elaborata.')

    now = now or datetime.now()
    before_snapshot = build_fine_snapshot(fine)
    # Quando la denuncia entra in votazione la togliamo dallo stato "pending":
    # resta comunque reversibile perché un eventuale annullo rimette tutto in attesa.
    fine.voting_active = True
    fine.voting_start = now
    fine.voting_end = now + timedelta(hours=24)
    fine.pending_approval = False

    multato = db.session.get(User, fine.user_id)
    after_snapshot = build_fine_snapshot(fine)
    log_fine_report_event(
        'start_denuncia_vote',
        actor=actor,
        fine=fine,
        target_user=multato,
        details={
            'before': before_snapshot,
            'after': after_snapshot,
            'changes': build_fine_change_details(before_snapshot, after_snapshot),
        },
    )
    db.session.commit()

    notifier(
        'denuncia_votazione',
        f"🗳️ Votazione aperta: multa a {get_nome_giocatore(multato)} per '{fine.reason}'. Vota entro 24h!",
        icon='🗳️',
    )
    return fine.voting_end


def cast_denuncia_vote(fine, voter, vote_raw, now=None):
    if voter.is_coach or voter.is_presidente:
        raise FineWorkflowError('Non puoi votare sulle multe.')
    if not fine or not fine.voting_active:
        raise FineWorkflowError('Votazione non attiva.')

    excluded = _parse_excluded_ids(fine.excluded_voters)
    if voter.id in excluded:
        raise FineWorkflowError('Sei stato escluso da questa votazione.')
    if voter.id == fine.user_id:
        raise FineWorkflowError('Non puoi votare sulla tua stessa multa.')

    # Manteniamo un solo voto per utente e permettiamo la modifica esplicita:
    # evita duplicati e lascia traccia temporale dell'ultimo cambio di scelta.
    vote_value = str(vote_raw) == '1'
    existing_vote = FineVote.query.filter_by(fine_id=fine.id, user_id=voter.id).first()
    if existing_vote:
        if existing_vote.vote != vote_value:
            existing_vote.vote = vote_value
            existing_vote.voted_at = now or datetime.now()
            db.session.commit()
            return 'Voto modificato!', 'success'
        return 'Hai già votato così.', 'info'

    db.session.add(FineVote(fine_id=fine.id, user_id=voter.id, vote=vote_value))
    db.session.commit()
    return 'Voto registrato!', 'success'


def update_vote_exclusions(fine, excluded_user_ids):
    if not fine or not fine.voting_active:
        raise FineWorkflowError('Votazione non trovata o non attiva.')

    normalized_ids = []
    for user_id in excluded_user_ids:
        try:
            normalized_ids.append(int(user_id))
        except (TypeError, ValueError):
            continue

    fine.excluded_voters = json.dumps(sorted(set(normalized_ids)))
    db.session.commit()
    return len(sorted(set(normalized_ids)))


def cancel_denuncia_vote(fine, notifier=crea_notifica):
    if not fine or not fine.voting_active:
        raise FineWorkflowError('Votazione non trovata o non attiva.')

    FineVote.query.filter_by(fine_id=fine.id).delete()
    fine.voting_active = False
    fine.voting_start = None
    fine.voting_end = None
    fine.excluded_voters = '[]'
    fine.pending_approval = True
    db.session.commit()

    notifier(
        'denuncia_votazione_annullata',
        f"🚫 Votazione annullata per la multa a {get_nome_giocatore(db.session.get(User, fine.user_id))}. La denuncia torna in attesa.",
        icon='🚫',
    )


def _parse_excluded_ids(raw_value):
    try:
        excluded = json.loads(raw_value or '[]')
    except (TypeError, json.JSONDecodeError):
        excluded = []
    return {int(user_id) for user_id in excluded if str(user_id).isdigit()}


def _notify_donator_rankings(fine, notifier=crea_notifica):
    giocatore = db.session.get(User, fine.user_id)
    giocatore_nome = get_nome_giocatore(giocatore)

    # Le notifiche top-3 sono deduplicate per evitare spam ogni volta che una multa già pagata
    # modifica una classifica in cui il giocatore è già stato celebrato.
    classifica_generale = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        Fine.paid == True,
    ).group_by(User.id).order_by(desc('total')).all()

    for index, (user, total) in enumerate(classifica_generale[:3]):
        if user.id != fine.user_id:
            continue

        posizione_str = {0: '🥇 PRIMO', 1: '🥈 SECONDO', 2: '🥉 TERZO'}[index]
        existing = Notification.query.filter(
            Notification.tipo == 'donatore_top3',
            Notification.messaggio.contains(giocatore_nome),
            Notification.messaggio.contains('classifica generale'),
        ).first()
        if not existing:
            notifier(
                'donatore_top3',
                f"💰 {giocatore_nome} è {posizione_str} nella classifica generale donatori con €{total:.2f}!",
                icon='💰',
            )
        break

    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)
    if now.month == 12:
        month_end = datetime(now.year + 1, 1, 1)
    else:
        month_end = datetime(now.year, now.month + 1, 1)

    classifica_mensile = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        Fine.paid == True,
        Fine.date >= month_start,
        Fine.date < month_end,
    ).group_by(User.id).order_by(desc('total')).all()

    for index, (user, total) in enumerate(classifica_mensile[:3]):
        if user.id != fine.user_id:
            continue

        posizione_str = {0: '🥇 PRIMO', 1: '🥈 SECONDO', 2: '🥉 TERZO'}[index]
        mese_nome = now.strftime('%B %Y')
        existing = Notification.query.filter(
            Notification.tipo == 'donatore_top3',
            Notification.messaggio.contains(giocatore_nome),
            Notification.messaggio.contains(mese_nome),
        ).first()
        if not existing:
            notifier(
                'donatore_top3',
                f"💰 {giocatore_nome} è {posizione_str} nella classifica donatori di {mese_nome} con €{total:.2f}!",
                icon='💰',
            )
        break
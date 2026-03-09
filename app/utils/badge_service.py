import json
from datetime import datetime, timedelta

from sqlalchemy import extract, func

from app.models import Achievement, Event, Fine, FlappyGameProfile, FlappyMonthlyScore, User, UserAchievement, Vote, db
from app.utils.notifications import crea_notifica


def assign_badge(user_id, badge_code, year, month, icon='🏅', color='bg-warning'):
    badge = Achievement.query.filter_by(code=badge_code).first()

    if not badge:
        badge = Achievement(
            code=badge_code,
            name=badge_code.replace('_', ' ').title(),
            description=f'Badge {badge_code}',
            icon=icon,
            color=color,
            is_monthly=True,
        )
        db.session.add(badge)
        db.session.commit()

    existing = UserAchievement.query.filter_by(
        user_id=user_id,
        achievement_id=badge.id,
        month=month,
        year=year,
    ).first()

    if existing:
        return False

    db.session.add(UserAchievement(user_id=user_id, achievement_id=badge.id, month=month, year=year))
    db.session.commit()
    return True


def _get_or_create_profile(user_id):
    profile = FlappyGameProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile

    profile = FlappyGameProfile(user_id=user_id, unlocked_skins='["default"]', selected_skin='default', bug_report_notes='[]')
    db.session.add(profile)
    db.session.flush()
    return profile


def _unlock_monthly_skin(user_id, skin_code, winner_name, message, icon):
    profile = _get_or_create_profile(user_id)
    unlocked = json.loads(profile.unlocked_skins or '["default"]')
    if skin_code in unlocked:
        return False

    unlocked.append(skin_code)
    profile.unlocked_skins = json.dumps(unlocked)
    crea_notifica('skin_unlock', message.format(nome=winner_name), icon=icon, send_push=True)
    db.session.commit()
    return True


def _get_previous_month_period(reference_date=None):
    today = reference_date or datetime.now()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    return last_day_previous_month.year, last_day_previous_month.month


def process_previous_month_badges(reference_date=None):
    year, month = _get_previous_month_period(reference_date)
    results = []

    fines = db.session.query(
        Fine.user_id,
        func.sum(Fine.amount).label('total'),
        User.nome_completo,
    ).join(User, Fine.user_id == User.id).filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None),
        extract('year', Fine.date) == year,
        extract('month', Fine.date) == month,
    ).group_by(Fine.user_id, User.nome_completo).all()

    if fines:
        max_amount = max(fines, key=lambda item: item.total).total
        candidates = [item for item in fines if item.total == max_amount]
        winners = []
        if len(candidates) == 1:
            winners = [{'user_id': candidates[0].user_id, 'nome': candidates[0].nome_completo, 'lifetime_total': 0}]
        else:
            candidates_data = []
            for candidate in candidates:
                lifetime_total = db.session.query(func.sum(Fine.amount)).filter(
                    Fine.user_id == candidate.user_id,
                    (Fine.pending_approval == False) | (Fine.pending_approval == None),
                ).scalar() or 0
                candidates_data.append({'user_id': candidate.user_id, 'nome': candidate.nome_completo, 'lifetime_total': lifetime_total})

            max_lifetime = max(candidates_data, key=lambda item: item['lifetime_total'])['lifetime_total']
            winners = [item for item in candidates_data if item['lifetime_total'] == max_lifetime]

        winner_names = []
        any_assigned = False
        for winner in winners:
            any_assigned = assign_badge(winner['user_id'], 'top_donatore_mese', year, month, '❌', 'bg-danger') or any_assigned
            winner_names.append(winner['nome'])
            _unlock_monthly_skin(
                winner['user_id'],
                'mosquito',
                winner['nome'],
                '🦅 {nome} ha sbloccato la skin ZANZARA! 🦟 Top Donatore del Mese!',
                '🦟',
            )

        value = f'€{max_amount:.2f}'
        if len(candidates) > 1:
            value += f" (Totale: €{winners[0]['lifetime_total']:.2f})"
        results.append({'tipo': '💰 Top Donatore', 'utente': ', '.join(winner_names), 'valore': value, 'assegnato': any_assigned})
    else:
        results.append({'tipo': '💰 Top Donatore', 'utente': 'Nessuno', 'valore': 'Nessuna multa', 'assegnato': False})

    reports = db.session.query(
        Fine.denunciante_id,
        func.count(Fine.id).label('total'),
        User.nome_completo,
    ).join(User, Fine.denunciante_id == User.id).filter(
        Fine.denunciante_id != None,
        extract('year', Fine.date) == year,
        extract('month', Fine.date) == month,
    ).group_by(Fine.denunciante_id, User.nome_completo).all()

    if reports:
        max_total = max(reports, key=lambda item: item.total).total
        winners = [item for item in reports if item.total == max_total]
        winner_names = []
        any_assigned = False
        for winner in winners:
            any_assigned = assign_badge(winner.denunciante_id, 'top_denunciatore_mese', year, month, '🚨', 'bg-purple') or any_assigned
            winner_names.append(winner.nome_completo)
            _unlock_monthly_skin(
                winner.denunciante_id,
                'raven',
                winner.nome_completo,
                '🦅 {nome} ha sbloccato la skin CORVO! 🚨 Top Denunciatore del Mese!',
                '🐦‍⬛',
            )
        results.append({'tipo': '🚨 Top Denunciatore', 'utente': ', '.join(winner_names), 'valore': f'{max_total} denunce', 'assegnato': any_assigned})
    else:
        results.append({'tipo': '🚨 Top Denunciatore', 'utente': 'Nessuno', 'valore': 'Nessuna denuncia', 'assegnato': False})

    mvp_counts = db.session.query(
        Event.mvp_id,
        func.count(Event.id).label('total'),
        User.nome_completo,
    ).join(User, Event.mvp_id == User.id).filter(
        Event.mvp_id != None,
        extract('year', Event.date_start) == year,
        extract('month', Event.date_start) == month,
    ).group_by(Event.mvp_id, User.nome_completo).all()

    if mvp_counts:
        max_wins = max(mvp_counts, key=lambda item: item.total).total
        candidates = [item for item in mvp_counts if item.total == max_wins]
        winners = []
        if len(candidates) == 1:
            winners = [{'user_id': candidates[0].mvp_id, 'nome': candidates[0].nome_completo, 'votes': 0}]
        else:
            candidates_data = []
            for candidate in candidates:
                vote_count = db.session.query(func.count(Vote.id)).join(Event, Vote.event_id == Event.id).filter(
                    Vote.voted_user_id == candidate.mvp_id,
                    extract('year', Event.date_start) == year,
                    extract('month', Event.date_start) == month,
                ).scalar() or 0
                candidates_data.append({'user_id': candidate.mvp_id, 'nome': candidate.nome_completo, 'votes': vote_count})

            max_votes = max(candidates_data, key=lambda item: item['votes'])['votes']
            winners = [item for item in candidates_data if item['votes'] == max_votes]

        winner_names = []
        any_assigned = False
        for winner in winners:
            any_assigned = assign_badge(winner['user_id'], 'top_mvp_mese', year, month, '⭐', 'bg-warning') or any_assigned
            winner_names.append(winner['nome'])
            _unlock_monthly_skin(
                winner['user_id'],
                'dove',
                winner['nome'],
                '🦅 {nome} ha sbloccato la skin COLOMBA! ⭐ MVP del Mese!',
                '⭐',
            )

        value = f'{max_wins} MVP'
        if len(candidates) > 1:
            value += f" ({winners[0]['votes']} voti)"
        results.append({'tipo': '⭐ Top MVP', 'utente': ', '.join(winner_names), 'valore': value, 'assegnato': any_assigned})
    else:
        results.append({'tipo': '⭐ Top MVP', 'utente': 'Nessuno', 'valore': 'Nessun MVP', 'assegnato': False})

    flappy_scores = db.session.query(
        FlappyMonthlyScore.user_id,
        FlappyMonthlyScore.score,
        User.nome_completo,
    ).join(User, FlappyMonthlyScore.user_id == User.id).filter(
        FlappyMonthlyScore.month == month,
        FlappyMonthlyScore.year == year,
    ).order_by(FlappyMonthlyScore.score.desc()).all()

    if flappy_scores:
        top_flappy = flappy_scores[0]
        badge_assigned = assign_badge(top_flappy.user_id, 'top_floppy_mese', year, month, '🎮', 'bg-primary')
        _unlock_monthly_skin(
            top_flappy.user_id,
            'goat',
            top_flappy.nome_completo,
            '🦅 {nome} ha sbloccato la skin CAPRA! 🏅 Floppy Eagle del Mese!',
            '🐐',
        )
        results.append({'tipo': '🎮 Top Flappy Eagle', 'utente': top_flappy.nome_completo, 'valore': f'{top_flappy.score} punti', 'assegnato': badge_assigned})
    else:
        results.append({'tipo': '🎮 Top Flappy Eagle', 'utente': 'Nessuno', 'valore': 'Nessun punteggio', 'assegnato': False})

    return results, month, year
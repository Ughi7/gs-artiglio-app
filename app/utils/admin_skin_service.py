import json
from datetime import datetime

from sqlalchemy import or_

from app.models import Achievement, FlappyGameProfile, User, UserAchievement, db
from app.utils.notifications import crea_notifica, get_nome_giocatore


ASSIGNABLE_SKINS = {
    'ladybug': {
        'name': 'Coccinella',
        'icon': '🐞',
        'event': '3 Segnalazioni Bug/Feedback',
        'type': 'counter',
        'threshold': 3,
        'counter_field': 'bug_report_count',
    },
}

TOP_BADGE_SKIN_MAP = {
    'top_donatore_mese': 'mosquito',
    'top_denunciatore_mese': 'raven',
    'top_mvp_mese': 'dove',
    'top_floppy_mese': 'goat',
}

RETROACTIVE_SKIN_NAMES = {
    'mosquito': 'ZANZARA 🦟',
    'raven': 'CORVO 🐦‍⬛',
    'dove': 'COLOMBA 🕊️',
    'goat': 'CAPRA 🐐',
}


class InvalidSkinError(ValueError):
    pass


def build_flappy_profile(user_id):
    return FlappyGameProfile(
        user_id=user_id,
        unlocked_skins='["default"]',
        selected_skin='default',
        bug_report_notes='[]',
    )


def get_or_create_flappy_profile(user_id):
    profile = FlappyGameProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile

    profile = build_flappy_profile(user_id)
    db.session.add(profile)
    db.session.flush()
    return profile


def assign_skin_to_users(skin_id, user_ids, notifier=crea_notifica):
    skin_info = _get_assignable_skin_info(skin_id)
    results = []

    for user_id in user_ids:
        user = db.session.get(User, int(user_id))
        if not user:
            continue

        profile = get_or_create_flappy_profile(user.id)
        unlocked = json.loads(profile.unlocked_skins or '[]')
        player_name = get_nome_giocatore(user)
        if skin_id not in unlocked:
            unlocked.append(skin_id)
            profile.unlocked_skins = json.dumps(unlocked)
            notifier('skin_unlock', f'🎨 {player_name} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]}', icon=skin_info['icon'])
            status = 'Assegnata!'
        else:
            status = 'Già sbloccata'

        results.append({
            'user': player_name,
            'skin': skin_info['name'],
            'icon': skin_info['icon'],
            'status': status,
        })

    db.session.commit()
    return results


def increment_skin_counter(skin_id, user_id, note='', now=None, notifier=crea_notifica):
    skin_info = _get_counter_skin_info(skin_id)
    user = db.session.get(User, int(user_id))
    if not user:
        return None

    now = now or datetime.now()
    profile = get_or_create_flappy_profile(user.id)
    counter_field = skin_info['counter_field']
    new_value = (getattr(profile, counter_field, 0) or 0) + 1
    setattr(profile, counter_field, new_value)

    notes = json.loads(profile.bug_report_notes or '[]')
    notes.append({'note': note or '(nessuna descrizione)', 'date': now.strftime('%d/%m/%Y %H:%M')})
    profile.bug_report_notes = json.dumps(notes)

    unlocked = json.loads(profile.unlocked_skins or '[]')
    player_name = get_nome_giocatore(user)
    if new_value >= skin_info['threshold'] and skin_id not in unlocked:
        unlocked.append(skin_id)
        profile.unlocked_skins = json.dumps(unlocked)
        notifier(
            'skin_unlock',
            f'🎨 {player_name} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]} {skin_info["event"]}',
            icon=skin_info['icon'],
        )
        status = f'Counter {new_value}/{skin_info["threshold"]} - SKIN SBLOCCATA! 🎉'
    else:
        status = f'Counter aggiornato: {new_value}/{skin_info["threshold"]}'

    db.session.commit()
    return {
        'user': player_name,
        'skin': skin_info['name'],
        'icon': skin_info['icon'],
        'status': status,
    }


def decrement_skin_counter(skin_id, user_id):
    skin_info = _get_counter_skin_info(skin_id)
    user = db.session.get(User, int(user_id))
    if not user:
        return None

    profile = get_or_create_flappy_profile(user.id)
    counter_field = skin_info['counter_field']
    new_value = max(0, (getattr(profile, counter_field, 0) or 0) - 1)
    setattr(profile, counter_field, new_value)
    db.session.commit()

    return {
        'user': get_nome_giocatore(user),
        'skin': skin_info['name'],
        'icon': skin_info['icon'],
        'status': f'Counter aggiornato: {new_value}/{skin_info["threshold"]}',
    }


def delete_skin_note(user_id, note_index):
    try:
        index = int(note_index)
    except (TypeError, ValueError):
        return None

    profile = get_or_create_flappy_profile(int(user_id))
    notes = json.loads(profile.bug_report_notes or '[]')
    if not 0 <= index < len(notes):
        return None

    del notes[index]
    profile.bug_report_notes = json.dumps(notes)
    db.session.commit()
    user = db.session.get(User, int(user_id))
    return {
        'user': get_nome_giocatore(user),
        'skin': 'Segnalazioni',
        'icon': '📝',
        'status': 'Nota eliminata',
    }


def edit_skin_note(user_id, note_index, new_text):
    if not new_text:
        return None

    try:
        index = int(note_index)
    except (TypeError, ValueError):
        return None

    profile = get_or_create_flappy_profile(int(user_id))
    notes = json.loads(profile.bug_report_notes or '[]')
    if not 0 <= index < len(notes):
        return None

    notes[index]['note'] = new_text
    profile.bug_report_notes = json.dumps(notes)
    db.session.commit()
    user = db.session.get(User, int(user_id))
    return {
        'user': get_nome_giocatore(user),
        'skin': 'Segnalazioni',
        'icon': '📝',
        'status': 'Nota modificata',
    }


def build_admin_skin_users_data():
    users = User.query.filter(or_(User.is_admin == False, User.is_admin == None)).order_by(User.nome_completo).all()
    user_ids = [user.id for user in users]
    profiles_by_user_id = {
        profile.user_id: profile
        for profile in FlappyGameProfile.query.filter(FlappyGameProfile.user_id.in_(user_ids)).all()
    } if user_ids else {}

    missing_profiles = []
    for user in users:
        if user.id not in profiles_by_user_id:
            profile = build_flappy_profile(user.id)
            missing_profiles.append(profile)
            profiles_by_user_id[user.id] = profile

    if missing_profiles:
        db.session.add_all(missing_profiles)
        db.session.commit()

    users_data = []
    for user in users:
        profile = profiles_by_user_id.get(user.id)
        unlocked = json.loads(profile.unlocked_skins or '[]') if profile else []
        counters = {}
        for skin_id, skin_info in ASSIGNABLE_SKINS.items():
            if skin_info.get('type') == 'counter' and profile:
                try:
                    counters[skin_id] = getattr(profile, skin_info['counter_field'], 0) or 0
                except Exception:
                    counters[skin_id] = 0
        users_data.append({
            'id': user.id,
            'nome': get_nome_giocatore(user),
            'skins': {skin_id: (skin_id in unlocked) for skin_id in ASSIGNABLE_SKINS},
            'counters': counters,
            'notes': json.loads(profile.bug_report_notes or '[]') if profile else [],
        })

    return users_data


def apply_retroactive_top_skins(notifier=crea_notifica):
    total_assigned = 0
    assigned_details = []

    for badge_code, skin_id in TOP_BADGE_SKIN_MAP.items():
        badge = Achievement.query.filter_by(code=badge_code).first()
        if not badge:
            continue

        winners = UserAchievement.query.filter_by(achievement_id=badge.id).all()
        count_for_badge = 0
        for winner in winners:
            profile = get_or_create_flappy_profile(winner.user_id)
            unlocked = json.loads(profile.unlocked_skins or '[]')
            if skin_id in unlocked:
                continue

            unlocked.append(skin_id)
            profile.unlocked_skins = json.dumps(unlocked)
            user = db.session.get(User, winner.user_id)
            notifier(
                'skin_unlock',
                f'🎨 {get_nome_giocatore(user)} ha sbloccato la skin {RETROACTIVE_SKIN_NAMES.get(skin_id, skin_id.capitalize())} tramite recupero premi passati!',
                icon='✨',
                send_push=True,
            )
            count_for_badge += 1
            total_assigned += 1

        if count_for_badge > 0:
            assigned_details.append(f'{count_for_badge} {skin_id}')

    db.session.commit()
    return total_assigned, assigned_details


def _get_assignable_skin_info(skin_id):
    skin_info = ASSIGNABLE_SKINS.get(skin_id)
    if not skin_info:
        raise InvalidSkinError('Skin non valida')
    return skin_info


def _get_counter_skin_info(skin_id):
    skin_info = _get_assignable_skin_info(skin_id)
    if skin_info.get('type') != 'counter':
        raise InvalidSkinError('Skin non valida per counter')
    return skin_info
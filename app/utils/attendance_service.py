from datetime import date, datetime, timedelta

from app.models import Attendance, Event, Training, User, db
from app.utils.notifications import get_nome_giocatore


WEEKDAY_NAMES = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']


class AttendanceValidationError(ValueError):
    pass


def can_manage_attendance(user):
    return user.is_admin or user.is_capitano or user.is_coach


def get_or_create_training(training_date):
    training = Training.query.filter_by(date=training_date).first()
    if not training:
        training = Training(date=training_date, start_time='19:00', end_time='21:00')
        db.session.add(training)
        db.session.commit()
    return training


def generate_training_dates(weeks_ahead=4):
    today = date.today()
    training_dates = []
    all_matches = Event.query.all()
    match_dates = set(match.date_start.date() for match in all_matches)

    for offset in range(weeks_ahead * 7):
        check_date = today + timedelta(days=offset)
        weekday = check_date.weekday()
        if weekday in [1, 2, 4] and check_date not in match_dates:
            training_dates.append(check_date)

    return training_dates


def _build_future_match_event(match, current_user):
    absences = Attendance.query.filter_by(event_id=match.id, status='absent').count()
    absent_users = [attendance.user for attendance in Attendance.query.filter_by(event_id=match.id, status='absent').all()]
    user_absent = Attendance.query.filter_by(event_id=match.id, user_id=current_user.id, status='absent').first()

    return {
        'type': 'match',
        'id': match.id,
        'date': match.date_start.date(),
        'datetime': match.date_start,
        'title': f"🏐 Partita vs {match.opponent_name}",
        'subtitle': f"{'Casa' if match.is_home else 'Trasferta'} - {match.date_start.strftime('%H:%M')}",
        'absences': absences,
        'absent_users': absent_users,
        'user_is_absent': user_absent is not None,
        'user_reason': user_absent.reason if user_absent else None,
        'location': match.location,
        'is_home': match.is_home,
        'is_friendly': match.is_friendly,
    }


def _build_training_event(training, current_user):
    absences = Attendance.query.filter_by(training_id=training.id, status='absent').count()
    absent_users = [attendance.user for attendance in Attendance.query.filter_by(training_id=training.id, status='absent').all()]
    user_absent = Attendance.query.filter_by(training_id=training.id, user_id=current_user.id, status='absent').first()
    late_count = Attendance.query.filter_by(training_id=training.id, status='late').count()
    late_users = [(attendance.user, attendance.reason) for attendance in Attendance.query.filter_by(training_id=training.id, status='late').all()]
    user_late = Attendance.query.filter_by(training_id=training.id, user_id=current_user.id, status='late').first()
    weekday_name = WEEKDAY_NAMES[training.date.weekday()]

    return {
        'type': 'training',
        'id': training.id,
        'date': training.date,
        'datetime': datetime.combine(training.date, datetime.strptime(training.start_time, '%H:%M').time()),
        'title': f"📋 Allenamento ({weekday_name})",
        'subtitle': f'{training.start_time} - {training.end_time}',
        'absences': absences,
        'absent_users': absent_users,
        'user_is_absent': user_absent is not None,
        'user_reason': user_absent.reason if user_absent else None,
        'late_count': late_count,
        'late_users': late_users,
        'user_is_late': user_late is not None,
        'user_late_reason': user_late.reason if user_late else None,
        'start_time': training.start_time,
        'end_time': training.end_time,
        'coach_notes': training.coach_notes,
        'coach_notes_private': training.coach_notes_private,
    }


def _build_past_match_event(match):
    absences = Attendance.query.filter_by(event_id=match.id, status='absent').count()
    absent_users = [attendance.user for attendance in Attendance.query.filter_by(event_id=match.id, status='absent').all()]
    return {
        'type': 'match',
        'id': match.id,
        'date': match.date_start.date(),
        'datetime': match.date_start,
        'title': f"🏐 Partita vs {match.opponent_name}",
        'subtitle': f"{'Casa' if match.is_home else 'Trasferta'} - {match.date_start.strftime('%H:%M')}",
        'absences': absences,
        'absent_users': absent_users,
        'result': f'{match.sets_us}-{match.sets_them}' if match.sets_us is not None else None,
        'is_friendly': match.is_friendly,
    }


def _build_past_training_event(training):
    absences = Attendance.query.filter_by(training_id=training.id, status='absent').count()
    absent_users = [attendance.user for attendance in Attendance.query.filter_by(training_id=training.id, status='absent').all()]
    late_count = Attendance.query.filter_by(training_id=training.id, status='late').count()
    weekday_name = WEEKDAY_NAMES[training.date.weekday()]
    return {
        'type': 'training',
        'id': training.id,
        'date': training.date,
        'datetime': datetime.combine(training.date, datetime.strptime(training.start_time, '%H:%M').time()),
        'title': f"📋 Allenamento ({weekday_name})",
        'subtitle': f'{training.start_time} - {training.end_time}',
        'absences': absences,
        'absent_users': absent_users,
        'late_count': late_count,
        'coach_notes': training.coach_notes,
        'coach_notes_private': training.coach_notes_private,
        'is_cancelled': training.is_cancelled,
    }


def build_attendance_context(current_user, filter_type='all', now=None):
    now = now or datetime.now()
    today = now.date()

    future_matches = Event.query.filter(Event.date_start >= now).order_by(Event.date_start).all()
    training_dates = generate_training_dates(4)

    trainings = []
    for training_date in training_dates:
        training = get_or_create_training(training_date)
        if not training.is_cancelled:
            trainings.append(training)

    events = [_build_future_match_event(match, current_user) for match in future_matches]
    events.extend(_build_training_event(training, current_user) for training in trainings)
    events.sort(key=lambda event: event['datetime'])

    history_start_date = now - timedelta(days=14)
    past_matches = Event.query.filter(Event.date_start < now, Event.date_start >= history_start_date).order_by(Event.date_start.desc()).all()
    past_trainings = Training.query.filter(Training.date < today, Training.date >= history_start_date.date()).order_by(Training.date.desc()).all()

    history_events = [_build_past_match_event(match) for match in past_matches]
    history_events.extend(_build_past_training_event(training) for training in past_trainings)
    history_events.sort(key=lambda event: event['datetime'], reverse=True)

    if filter_type == 'training':
        events = [event for event in events if event['type'] == 'training']
        history_events = [event for event in history_events if event['type'] == 'training']
    elif filter_type == 'match':
        events = [event for event in events if event['type'] == 'match']
        history_events = [event for event in history_events if event['type'] == 'match']

    players = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()
    can_manage = current_user.is_admin or current_user.is_capitano or current_user.is_coach

    return {
        'events': events,
        'history_events': history_events,
        'players': players,
        'can_manage': can_manage,
        'current_filter': filter_type,
        'now': now,
    }


def toggle_user_absence(event_type, event_id, user_id, reason=''):
    normalized_reason = reason.strip() or None
    if event_type == 'match':
        existing = Attendance.query.filter_by(event_id=event_id, user_id=user_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return 'Assenza annullata!', 'success'

        db.session.add(Attendance(event_id=event_id, user_id=user_id, status='absent', reason=normalized_reason))
        db.session.commit()
        return 'Assenza segnata!', 'warning'

    if event_type == 'training':
        existing = Attendance.query.filter_by(training_id=event_id, user_id=user_id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return 'Assenza annullata!', 'success'

        db.session.add(Attendance(training_id=event_id, user_id=user_id, status='absent', reason=normalized_reason))
        db.session.commit()
        return 'Assenza segnata!', 'warning'

    raise AttendanceValidationError('Tipo evento non valido.')


def toggle_member_absence(event_type, event_id, user, reason=''):
    normalized_reason = reason.strip() or None
    player_name = get_nome_giocatore(user)

    if event_type == 'match':
        existing = Attendance.query.filter_by(event_id=event_id, user_id=user.id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return f'Assenza di {player_name} annullata!', 'success'

        db.session.add(Attendance(event_id=event_id, user_id=user.id, status='absent', reason=normalized_reason))
        db.session.commit()
        return f'Assenza di {player_name} segnata!', 'warning'

    if event_type == 'training':
        existing = Attendance.query.filter_by(training_id=event_id, user_id=user.id).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return f'Assenza di {player_name} annullata!', 'success'

        db.session.add(Attendance(training_id=event_id, user_id=user.id, status='absent', reason=normalized_reason))
        db.session.commit()
        return f'Assenza di {player_name} segnata!', 'warning'

    raise AttendanceValidationError('Tipo evento non valido.')


def toggle_training_late(training_id, user_id, reason=''):
    normalized_reason = reason.strip() or None
    existing = Attendance.query.filter_by(training_id=training_id, user_id=user_id).first()
    if existing:
        if existing.status == 'late':
            db.session.delete(existing)
            db.session.commit()
            return 'Ritardo annullato!', 'success'

        existing.status = 'late'
        existing.reason = normalized_reason
        db.session.commit()
        return 'Stato aggiornato a ritardo!', 'info'

    db.session.add(Attendance(training_id=training_id, user_id=user_id, status='late', reason=normalized_reason))
    db.session.commit()
    return 'Ritardo segnato!', 'info'


def update_training(training, start_time=None, end_time=None, is_cancelled=False, coach_notes='', coach_notes_private=''):
    if start_time:
        training.start_time = start_time
    if end_time:
        training.end_time = end_time

    training.is_cancelled = is_cancelled
    training.coach_notes = coach_notes.strip() or None
    training.coach_notes_private = coach_notes_private.strip() or None
    db.session.commit()
    return training
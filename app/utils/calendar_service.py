import calendar as calendar_module
from datetime import date, datetime

from app.models import Event, Turno, User


def build_calendar_context(year, month, now=None):
    now = now or datetime.now()
    month_matrix = calendar_module.monthcalendar(year, month)
    month_name = calendar_module.month_name[month]
    _, last_day = calendar_module.monthrange(year, month)

    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    events = Event.query.filter(
        Event.date_start >= datetime(year, month, 1),
        Event.date_start <= datetime(year, month, last_day, 23, 59, 59),
    ).all()
    turni = Turno.query.filter(Turno.date >= start_date, Turno.date <= end_date).all()

    days_data = _build_days_data(turni, events)
    players = User.query.order_by(User.nome_completo).all()
    turni_counts = _build_turni_counts(players)
    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

    return {
        'calendar': month_matrix,
        'year': year,
        'month': month,
        'month_name': month_name,
        'days_data': days_data,
        'players': players,
        'turni_counts': turni_counts,
        'prev_ym': {'y': prev_year, 'm': prev_month},
        'next_ym': {'y': next_year, 'm': next_month},
        'now': now,
    }


def _build_days_data(turni, events):
    days_data = {}
    canonical_by_key = {}
    for turno in turni:
        date_str = turno.date.strftime('%Y-%m-%d')
        key = (date_str, turno.tipo)
        existing = canonical_by_key.get(key)
        if not existing:
            canonical_by_key[key] = turno
            continue

        keep = turno if (turno.id or 0) > (existing.id or 0) else existing
        drop = existing if keep is turno else turno

        try:
            keep_ids = {user.id for user in keep.incaricati}
            for user in drop.incaricati:
                if user.id not in keep_ids:
                    keep.incaricati.append(user)
                    keep_ids.add(user.id)
        except Exception:
            pass

        if getattr(existing, 'is_cancelled', False) and not getattr(turno, 'is_cancelled', False):
            keep = turno
        elif getattr(turno, 'is_cancelled', False) and not getattr(existing, 'is_cancelled', False):
            keep = existing

        canonical_by_key[key] = keep

    for turno in canonical_by_key.values():
        date_str = turno.date.strftime('%Y-%m-%d')
        if date_str not in days_data:
            days_data[date_str] = {}
        days_data[date_str].setdefault('turni', []).append(turno)
        days_data[date_str].setdefault('turno', turno)

    for event in events:
        date_str = event.date_start.strftime('%Y-%m-%d')
        days_data.setdefault(date_str, {})['match'] = event

    return days_data


def _build_turni_counts(players):
    counts = {}
    all_turni_raw = Turno.query.filter(Turno.is_cancelled == False).all()
    all_turni_map = {}
    for turno in all_turni_raw:
        key = (turno.date, turno.tipo)
        existing = all_turni_map.get(key)
        if not existing or (turno.id or 0) > (existing.id or 0):
            all_turni_map[key] = turno

    for player in players:
        pizza_count = 0
        birra_count = 0
        for turno in all_turni_map.values():
            if player in turno.incaricati:
                if turno.tipo == 'pizza':
                    pizza_count += 1
                elif turno.tipo == 'birra':
                    birra_count += 1
        counts[player.id] = {'pizza': pizza_count, 'birra': birra_count}

    return counts
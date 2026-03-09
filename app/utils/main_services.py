from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import func

from app.models import Event, Fine, MatchStats, User, db


VALID_PAYMENT_METHODS = {'contanti', 'paypal'}


class ValidationError(ValueError):
    pass


def _clean_text(value):
    return (value or '').strip()


def _parse_positive_int(value, field_label):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f'{field_label} non valido.')

    if parsed <= 0:
        raise ValidationError(f'{field_label} non valido.')

    return parsed


def _parse_reason(value):
    reason = _clean_text(value)
    if not reason:
        raise ValidationError('Il motivo della multa e obbligatorio.')
    if len(reason) > 100:
        raise ValidationError('Il motivo della multa deve restare entro 100 caratteri.')
    return reason


def _parse_amount(value):
    cleaned = _clean_text(value).replace(',', '.')
    if not cleaned:
        raise ValidationError('L\'importo e obbligatorio.')

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError('Importo non valido.')

    if amount <= 0:
        raise ValidationError('L\'importo deve essere maggiore di zero.')

    return float(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _parse_fine_date(value):
    cleaned = _clean_text(value)
    if not cleaned:
        return datetime.now()

    try:
        return datetime.strptime(cleaned, '%Y-%m-%d')
    except ValueError:
        raise ValidationError('Data multa non valida.')


def _get_user_or_raise(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise ValidationError('Giocatore non trovato.')
    return user


def normalize_payment_method(value, required=False):
    cleaned = _clean_text(value).lower()
    if not cleaned:
        if required:
            raise ValidationError('Seleziona un metodo di pagamento valido.')
        return None

    if cleaned not in VALID_PAYMENT_METHODS:
        raise ValidationError('Metodo di pagamento non valido.')

    return cleaned


def parse_new_fine_form(form):
    user_id = _parse_positive_int(form.get('user_id'), 'Giocatore')
    fine_date = _parse_fine_date(form.get('fine_date'))
    user = _get_user_or_raise(user_id)

    return {
        'user': user,
        'amount': _parse_amount(form.get('amount')),
        'reason': _parse_reason(form.get('reason')),
        'date': fine_date,
        'deadline': fine_date + timedelta(weeks=3)
    }


def parse_fine_update_form(form):
    fine_id = _parse_positive_int(form.get('fine_id'), 'Multa')
    is_paid = form.get('paid') == 'on'

    return {
        'fine_id': fine_id,
        'amount': _parse_amount(form.get('amount')),
        'reason': _parse_reason(form.get('reason')),
        'paid': is_paid,
        'payment_method': normalize_payment_method(form.get('payment_method'), required=is_paid)
    }


def get_user_profile_summary(user):
    totals = db.session.query(
        func.coalesce(func.sum(MatchStats.points), 0),
        func.coalesce(func.sum(MatchStats.aces), 0),
        func.coalesce(func.sum(MatchStats.blocks), 0)
    ).join(Event).filter(
        MatchStats.user_id == user.id,
        Event.is_friendly == False
    ).one()

    achievements_list = [
        {
            'icon': ua.achievement.icon,
            'name': ua.achievement.name,
            'desc': ua.achievement.description,
            'color': ua.achievement.color if ua.achievement.color else 'bg-warning',
            'is_monthly': ua.achievement.is_monthly,
            'month': ua.month,
            'year': ua.year
        }
        for ua in user.achievements
    ]

    return {
        'mvp_count': Event.query.filter(
            Event.mvp_id == user.id,
            Event.is_friendly == False
        ).count(),
        'total_points': totals[0],
        'total_aces': totals[1],
        'total_blocks': totals[2],
        'total_multe_count': Fine.query.filter_by(user_id=user.id).count(),
        'denunce_fatte': Fine.query.filter_by(denunciante_id=user.id).count(),
        'denunce_prese': Fine.query.filter(Fine.user_id == user.id, Fine.denunciante_id != None).count(),
        'achievements_list': achievements_list,
    }
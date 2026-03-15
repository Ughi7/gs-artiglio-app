import json
from datetime import datetime

from app.models import AdminFineReportEvent, UserSeenAdminFineReportEvent, db
from app.utils.notifications import get_nome_giocatore


ACTION_META = {
    'add_fine': {
        'icon': '💸',
        'label': 'Multa aggiunta',
        'badge_class': 'bg-danger-subtle text-danger-emphasis border border-danger-subtle',
    },
    'modify_fine': {
        'icon': '✏️',
        'label': 'Multa modificata',
        'badge_class': 'bg-warning-subtle text-warning-emphasis border border-warning-subtle',
    },
    'delete_fine': {
        'icon': '🗑️',
        'label': 'Multa eliminata',
        'badge_class': 'bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle',
    },
    'approve_denuncia': {
        'icon': '✅',
        'label': 'Denuncia approvata',
        'badge_class': 'bg-success-subtle text-success-emphasis border border-success-subtle',
    },
    'reject_denuncia': {
        'icon': '❌',
        'label': 'Denuncia respinta',
        'badge_class': 'bg-danger-subtle text-danger-emphasis border border-danger-subtle',
    },
    'start_denuncia_vote': {
        'icon': '🗳️',
        'label': 'Denuncia messa ai voti',
        'badge_class': 'bg-info-subtle text-info-emphasis border border-info-subtle',
    },
    'mark_fine_paid': {
        'icon': '💰',
        'label': 'Multa pagata',
        'badge_class': 'bg-success-subtle text-success-emphasis border border-success-subtle',
    },
}


FIELD_LABELS = {
    'amount': 'Importo',
    'reason': 'Motivazione',
    'paid': 'Pagata',
    'payment_method': 'Metodo pagamento',
    'deadline': 'Scadenza',
    'date': 'Data',
    'pending_approval': 'In attesa',
    'voting_active': 'Votazione attiva',
}


def format_fine_reference(fine=None, fine_id=None, details=None):
    details = details or {}

    if fine is not None and getattr(fine, 'date', None):
        return f"del {fine.date.strftime('%d/%m/%Y')}"

    snapshot = details.get('after') or details.get('before') or {}
    snapshot_date = snapshot.get('date')
    if snapshot_date:
        try:
            parsed_date = datetime.strptime(snapshot_date, '%d/%m/%Y %H:%M')
            return f"del {parsed_date.strftime('%d/%m/%Y')}"
        except ValueError:
            return f"del {snapshot_date}"

    if fine_id:
        return f"#{fine_id}"

    return 'senza riferimento'


def get_admin_fine_report_action_meta(action):
    return ACTION_META.get(action, {
        'icon': '🧾',
        'label': action.replace('_', ' ').title(),
        'badge_class': 'bg-dark text-white border border-secondary',
    })


def _format_value(field, value):
    if value is None or value == '':
        return '-'
    if field == 'amount':
        return f'€ {float(value):.2f}'
    if field in {'paid', 'pending_approval', 'voting_active'}:
        return 'Si' if value else 'No'
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y %H:%M')
    return str(value)


def build_fine_snapshot(fine):
    return {
        'amount': fine.amount,
        'reason': fine.reason,
        'paid': fine.paid,
        'payment_method': fine.payment_method,
        'deadline': fine.deadline.strftime('%d/%m/%Y %H:%M') if fine.deadline else None,
        'date': fine.date.strftime('%d/%m/%Y %H:%M') if fine.date else None,
        'pending_approval': fine.pending_approval,
        'voting_active': fine.voting_active,
    }


def build_fine_change_details(before_snapshot, after_snapshot):
    changes = []
    for field, label in FIELD_LABELS.items():
        before_value = before_snapshot.get(field)
        after_value = after_snapshot.get(field)

        if field == 'payment_method' and not (before_snapshot.get('paid') or after_snapshot.get('paid')):
            continue

        if before_value != after_value:
            changes.append(
                f"{label}: {_format_value(field, before_value)} -> {_format_value(field, after_value)}"
            )
    return changes


def _default_summary(action, actor, fine_id=None, fine=None, target_user=None, details=None):
    actor_name = get_nome_giocatore(actor) if actor else 'Sistema'
    target_name = get_nome_giocatore(target_user) if target_user else 'utente sconosciuto'
    fine_reference = format_fine_reference(fine=fine, fine_id=fine_id or (fine.id if fine else None), details=details)

    if action == 'add_fine' and fine is not None:
        return f"{actor_name} ha aggiunto una multa a {target_name}: € {fine.amount:.2f} - {fine.reason}"
    if action == 'modify_fine':
        return f"{actor_name} ha modificato la multa {fine_reference} di {target_name}"
    if action == 'delete_fine':
        return f"{actor_name} ha eliminato la multa {fine_reference} di {target_name}"
    if action == 'approve_denuncia' and fine is not None:
        return f"{actor_name} ha approvato la denuncia contro {target_name}: {fine.reason}"
    if action == 'reject_denuncia' and fine is not None:
        return f"{actor_name} ha respinto la denuncia contro {target_name}: {fine.reason}"
    if action == 'start_denuncia_vote' and fine is not None:
        return f"{actor_name} ha messo ai voti la denuncia contro {target_name}: {fine.reason}"
    if action == 'mark_fine_paid':
        method = fine.payment_method if fine is not None and fine.payment_method else 'metodo non specificato'
        return f"{actor_name} ha segnato come pagata la multa {fine_reference} di {target_name} ({method})"

    return f"{actor_name} ha eseguito l'azione {action}"


def log_fine_report_event(action, actor, fine=None, target_user=None, summary=None, details=None, fine_id=None):
    event = AdminFineReportEvent(
        actor_id=actor.id,
        action=action,
        fine_id=fine_id or (fine.id if fine else None),
        target_user_id=target_user.id if target_user else (fine.user_id if fine else None),
        summary=summary or _default_summary(action, actor, fine_id=fine_id, fine=fine, target_user=target_user, details=details),
        details_json=json.dumps(details or {}, ensure_ascii=False),
    )
    db.session.add(event)
    return event


def get_unread_admin_fine_report_events(user, limit=None):
    seen_subquery = db.session.query(UserSeenAdminFineReportEvent.event_id).filter_by(user_id=user.id)
    query = AdminFineReportEvent.query.filter(~AdminFineReportEvent.id.in_(seen_subquery)).order_by(
        AdminFineReportEvent.created_at.desc(),
        AdminFineReportEvent.id.desc(),
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def mark_admin_fine_report_events_seen(user, events=None):
    events = events if events is not None else get_unread_admin_fine_report_events(user)
    created = 0
    for event in events:
        existing = UserSeenAdminFineReportEvent.query.filter_by(user_id=user.id, event_id=event.id).first()
        if existing:
            continue
        db.session.add(UserSeenAdminFineReportEvent(user_id=user.id, event_id=event.id))
        created += 1
    if created:
        db.session.commit()
    return created


def serialize_admin_fine_report_event(event):
    try:
        details = json.loads(event.details_json or '{}')
    except Exception:
        details = {}

    meta = get_admin_fine_report_action_meta(event.action)
    return {
        'id': event.id,
        'icon': meta['icon'],
        'label': meta['label'],
        'badge_class': meta['badge_class'],
        'summary': event.summary,
        'created_at': event.created_at,
        'changes': details.get('changes', []),
        'details': details,
    }
from collections import Counter
from datetime import date, datetime, timedelta

from app.models import (
    AppRelease,
    ClassificaCampionato,
    ClassificaInfo,
    Event,
    Fine,
    GlobalSettings,
    HiddenNotification,
    Notification,
    NotificationPreference,
    User,
    UserSeenRelease,
    Vote,
)
from app.utils.cron_helpers import (
    check_matchday_notification,
    check_medical_certificate_expiry,
    get_mvp_deadline,
    maybe_update_all_streaks,
)
from app.utils.fine_report_service import (
    get_unread_admin_fine_report_events,
    serialize_admin_fine_report_event,
)
from app.utils.notifications import crea_notifica, get_nome_giocatore


def _get_match_data(current_user, now):
    next_match = Event.query.filter(Event.date_start > now).order_by(Event.date_start.asc()).first()
    last_match = Event.query.filter(
        Event.date_start < now,
        Event.sets_us + Event.sets_them > 0,
    ).order_by(Event.date_start.desc()).first()

    mvp_voting_open = False
    mvp_revealed = False
    user_voted = False
    mvp_winners = []

    if last_match and not last_match.is_friendly:
        deadline = get_mvp_deadline(last_match.date_start)

        if now >= deadline:
            mvp_revealed = True
            votes = Vote.query.filter_by(event_id=last_match.id).all()
            if votes:
                vote_counts = Counter(v.voted_user_id for v in votes)
                max_votes = max(vote_counts.values())
                winner_ids = [user_id for user_id, count in vote_counts.items() if count == max_votes]
                mvp_winners = User.query.filter(User.id.in_(winner_ids)).all()

                existing_mvp_notification = Notification.query.filter(
                    Notification.tipo == 'mvp',
                    Notification.messaggio.contains(f"vs {last_match.opponent_name}"),
                ).first()

                if not existing_mvp_notification and mvp_winners:
                    winners_text = ', '.join(get_nome_giocatore(winner) for winner in mvp_winners)
                    crea_notifica(
                        'mvp',
                        f"👑 MVP della partita vs {last_match.opponent_name}: {winners_text}!",
                        icon='👑',
                    )
        else:
            mvp_voting_open = True
            user_voted = Vote.query.filter_by(user_id=current_user.id, event_id=last_match.id).first() is not None

    return {
        'next_match': next_match,
        'last_match': last_match,
        'mvp_voting_open': mvp_voting_open,
        'mvp_revealed': mvp_revealed,
        'user_voted': user_voted,
        'mvp_winners': mvp_winners,
    }


def _get_global_standings_context():
    rank_obj = GlobalSettings.query.filter_by(key='rank').first()
    points_obj = GlobalSettings.query.filter_by(key='points').first()

    return {
        'rank': rank_obj.value if rank_obj else '-',
        'points': points_obj.value if points_obj else '-',
        'classifica': ClassificaCampionato.query.order_by(ClassificaCampionato.posizione.asc()).all(),
        'classifica_info': ClassificaInfo.query.first(),
    }


def _get_unpaid_fines(current_user):
    return Fine.query.filter(
        Fine.user_id == current_user.id,
        Fine.paid == False,
        (Fine.pending_approval == False) | (Fine.pending_approval == None),
    ).order_by(Fine.deadline.asc()).all()


def _get_upcoming_shifts(current_user):
    today = date.today()
    limit_date = today + timedelta(days=7)
    upcoming_shifts = [
        turno
        for turno in current_user.turni
        if not turno.is_cancelled and today <= turno.date <= limit_date
    ]
    upcoming_shifts.sort(key=lambda turno: turno.date)
    return upcoming_shifts


def _filter_notifications(notifiche_raw, notif_prefs):
    if not notif_prefs:
        return notifiche_raw

    notifiche = []
    for notification in notifiche_raw:
        tipo = notification.tipo.lower() if notification.tipo else ''
        if tipo == 'mvp' and not notif_prefs.show_mvp:
            continue
        if 'streak' in tipo and not notif_prefs.show_streak:
            continue
        if 'turno' in tipo and not notif_prefs.show_turno:
            continue
        if 'denuncia' in tipo and not notif_prefs.show_denuncia:
            continue
        if ('flappy' in tipo or 'floppy' in tipo) and not notif_prefs.show_flappy:
            continue
        if 'donator' in tipo and not notif_prefs.show_donatore:
            continue
        if ('certificato' in tipo or 'medical' in tipo) and not notif_prefs.show_certificato:
            continue
        if 'aggiornamento' in tipo and not notif_prefs.show_aggiornamento:
            continue
        notifiche.append(notification)
    return notifiche


def _get_notifications_context(current_user, now):
    una_settimana_fa = now - timedelta(days=7)
    hidden_ids = [hidden.notification_id for hidden in HiddenNotification.query.filter_by(user_id=current_user.id).all()]
    notif_prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()

    notifiche_raw = Notification.query.filter(
        Notification.data_creazione >= una_settimana_fa,
        ~Notification.id.in_(hidden_ids) if hidden_ids else True,
    ).order_by(Notification.data_creazione.desc()).limit(10).all()

    return {
        'notifiche': _filter_notifications(notifiche_raw, notif_prefs),
        'notif_prefs': notif_prefs,
    }


def _get_unseen_release(current_user):
    latest_release = AppRelease.query.order_by(AppRelease.release_date.desc()).first()
    if not latest_release:
        return None

    already_seen = UserSeenRelease.query.filter_by(user_id=current_user.id, release_id=latest_release.id).first()
    return None if already_seen else latest_release


def _get_admin_fine_report_context(current_user):
    if not (current_user.is_admin or current_user.is_notaio):
        return {
            'unread_admin_fine_report_events': [],
            'unread_admin_fine_report_count': 0,
        }

    unread_events = [
        serialize_admin_fine_report_event(event)
        for event in get_unread_admin_fine_report_events(current_user, limit=15)
    ]
    return {
        'unread_admin_fine_report_events': unread_events,
        'unread_admin_fine_report_count': len(unread_events),
    }


def build_home_context(current_user, now=None):
    now = now or datetime.now()

    maybe_update_all_streaks(now=now)
    check_medical_certificate_expiry(current_user)
    check_matchday_notification()

    context = {}
    context.update(_get_match_data(current_user, now))
    context.update(_get_global_standings_context())
    context.update(_get_notifications_context(current_user, now))
    context.update(_get_admin_fine_report_context(current_user))

    context['unpaid_fines'] = _get_unpaid_fines(current_user)
    context['turni_imminenti'] = _get_upcoming_shifts(current_user)
    context['players'] = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()
    context['unseen_release'] = _get_unseen_release(current_user)
    context['unseen_vote_histories'] = _get_unseen_vote_histories(current_user)

    return context

def _get_unseen_vote_histories(current_user):
    from app.models import VoteHistory, UserSeenVoteHistory, db
    import json
    seen_ids_subquery = db.session.query(UserSeenVoteHistory.vote_history_id).filter_by(user_id=current_user.id)
    unseen = VoteHistory.query.filter(
        VoteHistory.id.notin_(seen_ids_subquery)
    ).order_by(VoteHistory.closed_at.asc()).all()
    
    for u in unseen:
        u.non_voters_list = json.loads(u.non_voters) if u.non_voters else []
    return unseen
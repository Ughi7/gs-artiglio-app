from datetime import datetime

from sqlalchemy import desc, func

from app.models import Event, User, Vote, db
from app.utils.cron_helpers import get_mvp_deadline


def build_matches_page_context(now=None):
    now = now or datetime.now()
    all_events = Event.query.order_by(Event.date_start.asc()).all()
    future = []
    past = []

    for event in all_events:
        deadline = get_mvp_deadline(event.date_start)
        if event.date_start < now and event.mvp_id is None and now > deadline and not event.is_friendly:
            top_vote = db.session.query(
                Vote.voted_user_id,
                func.count(Vote.voted_user_id).label('c'),
            ).filter_by(event_id=event.id).group_by(Vote.voted_user_id).order_by(desc('c')).first()
            if top_vote:
                event.mvp_id = top_vote.voted_user_id
                db.session.commit()

        event.voting_closed = now > deadline
        if event.date_start > now:
            future.append(event)
        else:
            past.append(event)

    past.reverse()
    players = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()
    return {
        'future': future,
        'past': past,
        'players': players,
        'now': now,
    }
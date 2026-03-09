import json
from datetime import datetime, timedelta

from app.models import Fine, FineVote, User, db
from app.utils.notifications import crea_notifica, get_nome_giocatore


def get_eligible_voters_count():
    return User.query.filter(
        User.is_coach.isnot(True),
        User.is_presidente.isnot(True)
    ).count()


def calculate_vote_quorum(fine):
    try:
        excluded = json.loads(fine.excluded_voters or '[]')
    except Exception:
        excluded = []

    eligible_voters_total = get_eligible_voters_count()
    effective_voters = max(0, eligible_voters_total - len(excluded) - 1)
    return max(1, (effective_voters // 2) + 1), excluded


def check_and_apply_late_fees(now=None):
    current_time = now or datetime.now()
    overdue_fines = Fine.query.filter(
        Fine.deadline < current_time,
        Fine.paid == False,
        Fine.has_generated_mora == False,
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).all()

    for fine in overdue_fines:
        fine_date_str = fine.date.strftime('%d/%m/%Y')
        mora = Fine(
            amount=2.0,
            reason=f'Mora ritardo pagamento (Rif. Multa #{fine.id} del {fine_date_str})',
            user_id=fine.user_id,
            deadline=current_time + timedelta(weeks=3),
            date=current_time,
        )
        db.session.add(mora)
        fine.has_generated_mora = True

    if overdue_fines:
        db.session.commit()


def cleanup_old_rejected_votes(now=None):
    current_time = now or datetime.now()
    cutoff = current_time - timedelta(hours=24)
    old_rejected = Fine.query.filter(
        Fine.voting_active == False,
        Fine.pending_approval == True,
        Fine.voting_end != None,
        Fine.voting_end < cutoff
    ).all()

    for fine in old_rejected:
        approve_count = FineVote.query.filter_by(fine_id=fine.id, vote=True).count()
        quorum, _ = calculate_vote_quorum(fine)
        if approve_count < quorum:
            FineVote.query.filter_by(fine_id=fine.id).delete()
            db.session.delete(fine)

    if old_rejected:
        db.session.commit()


def check_and_close_expired_votes(now=None):
    current_time = now or datetime.now()
    expired_votes = Fine.query.filter(
        Fine.voting_active == True,
        Fine.voting_end < current_time
    ).all()

    for fine in expired_votes:
        approve_count = FineVote.query.filter_by(fine_id=fine.id, vote=True).count()
        reject_count = FineVote.query.filter_by(fine_id=fine.id, vote=False).count()
        total_votes = approve_count + reject_count
        quorum, _ = calculate_vote_quorum(fine)

        multato = db.session.get(User, fine.user_id)
        multato_nome = get_nome_giocatore(multato)
        fine.voting_active = False

        if approve_count >= quorum:
            fine.pending_approval = False
            if multato:
                multato.current_streak = 0
            crea_notifica(
                'denuncia_votazione_chiusa',
                f'📊 Votazione conclusa: multa a {multato_nome} APPROVATA! ({approve_count} favorevoli, {reject_count} contrari su {total_votes} votanti)',
                icon='✅'
            )
        else:
            fine.pending_approval = True
            crea_notifica(
                'denuncia_votazione_chiusa',
                f'📊 Votazione conclusa: multa a {multato_nome} RESPINTA. ({approve_count} favorevoli, {reject_count} contrari - servivano {quorum} voti)',
                icon='❌'
            )

    if expired_votes:
        db.session.commit()

    cleanup_old_rejected_votes(current_time)
    return len(expired_votes)
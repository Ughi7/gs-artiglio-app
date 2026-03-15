import json
from datetime import datetime, timedelta

from app.models import Fine, FineVote, User, db, VoteHistory
from app.utils.notifications import crea_notifica, get_nome_giocatore


def get_eligible_voters_count():
    return len(get_eligible_voter_ids())


def get_eligible_voter_ids():
    voter_rows = db.session.query(User.id).filter(
        User.is_coach.isnot(True),
        User.is_presidente.isnot(True)
    ).all()
    return {user_id for user_id, in voter_rows}


def get_vote_exclusions(fine, eligible_voter_ids=None):
    eligible_voter_ids = eligible_voter_ids or get_eligible_voter_ids()

    try:
        excluded = json.loads(fine.excluded_voters or '[]')
    except Exception:
        excluded = []

    excluded_ids = set()
    for user_id in excluded:
        try:
            normalized_id = int(user_id)
        except (TypeError, ValueError):
            continue
        if normalized_id in eligible_voter_ids:
            excluded_ids.add(normalized_id)

    if fine.user_id in eligible_voter_ids:
        excluded_ids.add(fine.user_id)

    return excluded_ids


def calculate_vote_quorum(fine, eligible_voter_ids=None):
    eligible_voter_ids = eligible_voter_ids or get_eligible_voter_ids()
    excluded_ids = get_vote_exclusions(fine, eligible_voter_ids)
    effective_voters = max(0, len(eligible_voter_ids - excluded_ids))
    return max(1, (effective_voters // 2) + 1), sorted(excluded_ids)


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
        quorum_reached = total_votes >= quorum

        # --- UPDATE STORICO VOTAZIONI ---
        eligible_voters = get_eligible_voter_ids()
        excluded = get_vote_exclusions(fine, eligible_voters)
        actual_eligible = eligible_voters - excluded
        voted_ids = {v[0] for v in db.session.query(FineVote.user_id).filter_by(fine_id=fine.id).all()}
        non_voter_ids = actual_eligible - voted_ids
        
        non_voters_names = []
        for n_id in non_voter_ids:
            u = db.session.get(User, n_id)
            if u:
                non_voters_names.append(get_nome_giocatore(u))
                
        outcome_str = 'approved' if (quorum_reached and approve_count > reject_count) else ('rejected_quorum' if not quorum_reached else 'rejected_votes')
        denunciante_nome = 'Sconosciuto'
        if fine.denunciante_id:
            d_user = db.session.get(User, fine.denunciante_id)
            if d_user:
                denunciante_nome = get_nome_giocatore(d_user)

        history = VoteHistory(
            fine_reason=fine.reason,
            multato_name=multato_nome,
            denunciante_name=denunciante_nome,
            outcome=outcome_str,
            approve_count=approve_count,
            reject_count=reject_count,
            total_voters=total_votes,
            quorum=quorum,
            non_voters=json.dumps(non_voters_names),
            closed_at=current_time
        )
        db.session.add(history)
        # --------------------------------

        if quorum_reached and approve_count > reject_count:
            fine.voting_active = False
            fine.pending_approval = False
            if multato:
                multato.current_streak = 0
            crea_notifica(
                'denuncia_votazione_chiusa',
                f'📊 Votazione conclusa: multa a {multato_nome} APPROVATA! ({approve_count} favorevoli, {reject_count} contrari su {total_votes} votanti)',
                icon='✅'
            )
        else:
            if not quorum_reached:
                message = (
                    f'📊 Votazione conclusa: multa a {multato_nome} RESPINTA. '
                    f'Quorum non raggiunto ({total_votes}/{quorum} voti).'
                )
            else:
                message = (
                    f'📊 Votazione conclusa: multa a {multato_nome} RESPINTA. '
                    f'({approve_count} favorevoli, {reject_count} contrari su {total_votes} votanti)'
                )

            crea_notifica(
                'denuncia_votazione_chiusa',
                message,
                icon='❌'
            )

            FineVote.query.filter_by(fine_id=fine.id).delete()
            db.session.delete(fine)

    if expired_votes:
        db.session.commit()

    return len(expired_votes)
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Attendance, Event, MatchStats, Notification, Training, User, Vote, db
from app.utils.cron_helpers import get_mvp_deadline
from app.utils.match_service import build_matches_page_context
from app.utils.notifications import crea_notifica
from app.utils.stats_service import build_match_stats_context


matches_bp = Blueprint('matches', __name__)


def _redirect_to_matches():
    return redirect(url_for('matches.partite'))


def _form_int(name: str, default: int = 0) -> int:
    """Parse an int from a form field.

    Empty/missing/invalid values become default.
    """
    raw = request.form.get(name, None)
    if raw is None:
        return default
    raw = raw.strip() if isinstance(raw, str) else raw
    if raw == '':
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        # Be resilient to unexpected browser/input edge cases.
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return default


@matches_bp.route('/stats_partite')
@login_required
def stats_partite():
    return render_template('stats_partite.html', **build_match_stats_context())


@matches_bp.route('/partite')
@login_required
def partite():
    return render_template('partite.html', **build_matches_page_context(now=datetime.now()))


@matches_bp.route('/crea_partita', methods=['POST'])
@login_required
def crea_partita():
    if not current_user.is_admin:
        return _redirect_to_matches()

    date_time = datetime.strptime(f"{request.form.get('data')} {request.form.get('ora')}", '%Y-%m-%d %H:%M')
    is_home = request.form.get('casa_trasferta') == 'casa'
    location = 'PalaArtiglio' if is_home else request.form.get('location')
    is_friendly = request.form.get('is_friendly') == 'on'

    event = Event(
        opponent_name=request.form.get('opponent_name'),
        date_start=date_time,
        is_home=is_home,
        location=location,
        is_friendly=is_friendly,
    )
    db.session.add(event)

    existing_training = Training.query.filter_by(date=date_time.date()).first()
    if existing_training:
        db.session.delete(existing_training)
        flash('Partita aggiunta e allenamento dello stesso giorno rimosso', 'success')
    else:
        flash('Partita aggiunta', 'success')

    db.session.commit()
    return _redirect_to_matches()


@matches_bp.route('/modifica_partita', methods=['POST'])
@login_required
def modifica_partita():
    if not current_user.is_admin:
        return _redirect_to_matches()

    event = db.session.get(Event, int(request.form.get('event_id')))
    if event:
        old_date = event.date_start.date()
        event.opponent_name = request.form.get('opponent_name')
        event.location = request.form.get('location')
        event.is_home = request.form.get('casa_trasferta') == 'casa'
        event.is_friendly = request.form.get('is_friendly') == 'on'

        form_date = request.form.get('data')
        form_time = request.form.get('ora')
        if form_date and form_time:
            new_date_time = datetime.strptime(f'{form_date} {form_time}', '%Y-%m-%d %H:%M')
            event.date_start = new_date_time
            if old_date != new_date_time.date():
                existing_training = Training.query.filter_by(date=new_date_time.date()).first()
                if existing_training:
                    db.session.delete(existing_training)

        db.session.commit()

    return _redirect_to_matches()


@matches_bp.route('/elimina_partita/<int:event_id>')
@login_required
def elimina_partita(event_id):
    if not current_user.is_admin:
        return _redirect_to_matches()

    event = db.session.get(Event, event_id)
    if event:
        Attendance.query.filter_by(event_id=event_id).delete()
        db.session.delete(event)
        db.session.commit()

    return _redirect_to_matches()


@matches_bp.route('/segnala_assenza/<int:event_id>', methods=['GET', 'POST'])
@login_required
def segnala_assenza(event_id):
    try:
        presence = Attendance.query.filter_by(user_id=current_user.id, event_id=event_id).first()
        if presence:
            db.session.delete(presence)
            flash('Assenza annullata!', 'success')
        else:
            db.session.add(Attendance(user_id=current_user.id, event_id=event_id, status='absent'))
            flash('Assenza segnata!', 'warning')
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        flash('Errore nel salvare l\'assenza. Riprova.', 'danger')
        current_app.logger.exception('Errore in segnala_assenza: %s', exc)

    return _redirect_to_matches()


@matches_bp.route('/salva_risultato', methods=['POST'])
@login_required
def salva_risultato():
    if not current_user.is_admin:
        return _redirect_to_matches()

    event = db.session.get(Event, int(request.form.get('event_id')))
    if event:
        event.sets_us = int(request.form.get('sets_us'))
        event.sets_them = int(request.form.get('sets_them'))
        db.session.commit()

        if not event.is_friendly:
            deadline = get_mvp_deadline(event.date_start)
            deadline_str = deadline.strftime('%A %d/%m alle %H:%M').capitalize()
            result = f'{event.sets_us}-{event.sets_them}'
            existing = Notification.query.filter(
                Notification.tipo == 'mvp',
                Notification.messaggio.contains(f'vs {event.opponent_name}'),
            ).filter(
                Notification.messaggio.contains(result),
            ).first()
            if not existing:
                crea_notifica(
                    'mvp',
                    f"🗳️ Votazione MVP aperta! Partita vs {event.opponent_name} ({result}). Vota il migliore in campo entro {deadline_str}!",
                    icon='🗳️',
                )

    return _redirect_to_matches()


@matches_bp.route('/vote_mvp/<int:event_id>', methods=['POST'])
@login_required
def vote_mvp(event_id):
    event = db.get_or_404(Event, event_id)
    voted_user_id = request.form.get('voted_user_id')

    if event.is_friendly:
        flash('Le partite amichevoli non hanno votazione MVP!', 'warning')
        return redirect(url_for('dashboard.home'))

    if not voted_user_id:
        flash('Devi selezionare un giocatore!', 'danger')
        return redirect(url_for('dashboard.home'))

    if Vote.query.filter_by(user_id=current_user.id, event_id=event.id).first():
        flash('Hai già votato per questa partita!', 'warning')
        return redirect(url_for('dashboard.home'))

    if datetime.now() > get_mvp_deadline(event.date_start):
        flash('Le votazioni sono chiuse!', 'danger')
        return redirect(url_for('dashboard.home'))

    db.session.add(Vote(user_id=current_user.id, event_id=event.id, voted_user_id=voted_user_id))
    db.session.commit()

    flash('Voto registrato!', 'success')
    return redirect(url_for('dashboard.home'))


@matches_bp.route('/salva_statistiche', methods=['POST'])
@login_required
def salva_statistiche():
    if not (current_user.is_admin or current_user.is_scout):
        return _redirect_to_matches()

    try:
        event_id = _form_int('event_id', default=0)
        if not event_id:
            flash('Richiesta non valida (partita mancante).', 'danger')
            return _redirect_to_matches()

        event = db.session.get(Event, event_id)
        if not event:
            flash('Partita non trovata', 'danger')
            return _redirect_to_matches()

        event.total_missed_serves = _form_int('total_missed_serves', default=0)
        all_players = User.query.filter(User.is_coach.isnot(True)).all()

        for player in all_players:
            points = _form_int(f'points_{player.id}', default=0)
            aces = _form_int(f'aces_{player.id}', default=0)
            blocks = _form_int(f'blocks_{player.id}', default=0)
            stat = MatchStats.query.filter_by(user_id=player.id, event_id=event_id).first()

            if stat:
                stat.points = points
                stat.aces = aces
                stat.blocks = blocks
            elif points > 0 or aces > 0 or blocks > 0:
                db.session.add(MatchStats(
                    user_id=player.id,
                    event_id=event_id,
                    points=points,
                    aces=aces,
                    blocks=blocks,
                ))

        db.session.commit()
        flash('Statistiche salvate con successo!', 'success')
        return _redirect_to_matches()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception('Errore in salva_statistiche: %s', exc)
        flash('Errore nel salvataggio delle statistiche. Riprova.', 'danger')
        return _redirect_to_matches()

import urllib.parse
from datetime import datetime, timedelta

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Event, Turno, User, db
from app.utils.calendar_service import build_calendar_context
from app.utils.notifications import crea_notifica, get_nome_giocatore


calendar_bp = Blueprint('calendar_pages', __name__)


def _redirect_to_calendar(year=None, month=None):
    if year is not None and month is not None:
        return redirect(url_for('calendar_pages.calendario', year=year, month=month))
    return redirect(url_for('calendar_pages.calendario'))


@calendar_bp.route('/calendario')
@login_required
def calendario():
    now = datetime.now()
    year = request.args.get('year', type=int, default=now.year)
    month = request.args.get('month', type=int, default=now.month)
    return render_template('calendario.html', **build_calendar_context(year, month, now=now))


@calendar_bp.route('/gestisci_turno', methods=['POST'])
@login_required
def gestisci_turno():
    payload = request.get_json(silent=True) or {}
    data_str = request.form.get('date') or payload.get('date')
    tipo = request.form.get('tipo') or payload.get('tipo')
    action = request.form.get('action') or payload.get('action')

    user_ids = request.form.getlist('user_ids')
    if not user_ids and isinstance(payload.get('user_ids'), list):
        user_ids = [str(user_id) for user_id in payload.get('user_ids') if user_id is not None]

    current_app.logger.debug(
        'Gestione turno richiesta da %s: data=%s tipo=%s action=%s',
        current_user.username,
        data_str,
        tipo,
        action,
    )

    if not action and user_ids:
        action = 'assign'

    if not data_str or not tipo or not action:
        missing = []
        if not data_str:
            missing.append('date')
        if not tipo:
            missing.append('tipo')
        if not action:
            missing.append('action')
        flash('Dati mancanti! (' + ', '.join(missing) + ')', 'danger')
        current_app.logger.debug(
            'Gestione turno con dati mancanti: missing=%s form_keys=%s json_keys=%s',
            missing,
            list(request.form.keys()),
            list(payload.keys()),
        )
        return _redirect_to_calendar()

    permesso_birra = tipo == 'birra' and (current_user.is_admin or current_user.is_birra)
    permesso_pizza = tipo == 'pizza' and (current_user.is_admin or current_user.is_pizza)
    current_app.logger.debug('Permessi turno: birra=%s pizza=%s', permesso_birra, permesso_pizza)

    if not (permesso_birra or permesso_pizza):
        flash(f'Non hai i permessi per gestire {tipo}!', 'danger')
        return _redirect_to_calendar()

    turno_date = datetime.strptime(data_str, '%Y-%m-%d').date()
    turni_same_key = Turno.query.filter_by(date=turno_date, tipo=tipo).order_by(Turno.id.desc()).all()
    turno = turni_same_key[0] if turni_same_key else None

    if len(turni_same_key) > 1 and turno:
        try:
            keep_ids = {user.id for user in turno.incaricati}
            for extra in turni_same_key[1:]:
                for user in extra.incaricati:
                    if user.id not in keep_ids:
                        turno.incaricati.append(user)
                        keep_ids.add(user.id)
                db.session.delete(extra)
            db.session.commit()
            current_app.logger.info(
                'Consolidati turni duplicati per %s tipo=%s; tenuto id=%s, rimossi=%s',
                turno_date,
                tipo,
                turno.id,
                len(turni_same_key) - 1,
            )
        except Exception as exc:
            current_app.logger.exception('Errore consolidamento duplicati turno: %s', exc)

    if action == 'cancel':
        if not turno:
            turno = Turno(date=turno_date, tipo=tipo)
            db.session.add(turno)
        turno.is_cancelled = True
        turno.incaricati = []
        db.session.commit()
    elif action == 'assign':
        current_app.logger.debug('Assegnazione turno %s/%s con user_ids=%s', turno_date, tipo, user_ids)
        if not turno:
            turno = Turno(date=turno_date, tipo=tipo)
            db.session.add(turno)
            current_app.logger.debug('Creato nuovo turno per %s tipo=%s', turno_date, tipo)

        turno.is_cancelled = False
        turno.incaricati = []
        for user_id in user_ids:
            try:
                user = db.session.get(User, int(user_id))
                if user:
                    turno.incaricati.append(user)
                    current_app.logger.debug('Aggiunto incaricato al turno: %s', get_nome_giocatore(user))
                else:
                    current_app.logger.warning('User non trovato per assegnazione turno: id=%s', user_id)
            except Exception as exc:
                current_app.logger.exception('Errore aggiungendo user %s al turno: %s', user_id, exc)

        db.session.commit()
        current_app.logger.debug('Turno salvato con %s incaricati', len(turno.incaricati))

        if user_ids:
            responsabile = 'Mastro Birraio' if tipo == 'birra' else 'Resp. Pizza'
            assigner_name = get_nome_giocatore(current_user)
            for user_id in user_ids:
                user = db.session.get(User, int(user_id))
                if user:
                    player_name = get_nome_giocatore(user)
                    emoji = '🍺' if tipo == 'birra' else '🍕'
                    crea_notifica(
                        'turno_assegnato',
                        f'{emoji} {player_name} è stato incaricato da {assigner_name} ({responsabile}) per portare la {tipo} il {turno_date.strftime("%d/%m/%Y")}',
                        icon=emoji,
                    )
    elif action == 'delete' and turno:
        db.session.delete(turno)
        db.session.commit()

    return _redirect_to_calendar(year=turno_date.year, month=turno_date.month)


@calendar_bp.route('/export_calendar_ics')
@login_required
def export_calendar_ics():
    now = datetime.now()
    events = Event.query.filter(Event.date_start >= now).order_by(Event.date_start.asc()).all()

    if not events:
        flash('Nessuna partita futura da esportare.', 'warning')
        return _redirect_to_calendar(year=now.year, month=now.month)

    ics_content = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//GS Artiglio//NONSGML Calendar//EN',
        'X-WR-CALNAME:GS Artiglio Partite',
        'CALSCALE:GREGORIAN',
    ]

    for event in events:
        start_time = event.date_start
        end_time = start_time + timedelta(hours=2)
        dtstart = start_time.strftime('%Y%m%dT%H%M%S')
        dtend = end_time.strftime('%Y%m%dT%H%M%S')
        dtstamp = now.strftime('%Y%m%dT%H%M%S')
        summary = f'Partita vs {event.opponent_name}'
        location = event.location or 'Campo Sportivo'
        maps_link = f'https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}'
        description = f'Partita contro {event.opponent_name}.\\nLink Maps: {maps_link}'

        ics_content.append('BEGIN:VEVENT')
        ics_content.append(f'UID:event_{event.id}@gsartiglio.app')
        ics_content.append(f'DTSTAMP:{dtstamp}')
        ics_content.append(f'DTSTART:{dtstart}')
        ics_content.append(f'DTEND:{dtend}')
        ics_content.append(f'SUMMARY:{summary}')
        ics_content.append(f'LOCATION:{location}')
        ics_content.append(f'DESCRIPTION:{description}')
        ics_content.append('END:VEVENT')

    ics_content.append('END:VCALENDAR')
    response = Response('\r\n'.join(ics_content), mimetype='text/calendar')
    response.headers['Content-Disposition'] = 'attachment; filename=partite_gs_artiglio.ics'
    return response
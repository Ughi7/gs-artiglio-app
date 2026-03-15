from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Training, User, db
from app.utils.attendance_service import (
    AttendanceValidationError,
    build_attendance_context,
    can_manage_attendance,
    toggle_member_absence,
    toggle_training_late,
    toggle_user_absence,
    update_training,
)


attendance_bp = Blueprint('attendance_pages', __name__)


def _redirect_to_attendance():
    return redirect(url_for('attendance_pages.presenze'))
@attendance_bp.route('/presenze')
@login_required
def presenze():
    filter_type = request.args.get('filter', 'all')
    return render_template('presenze.html', **build_attendance_context(current_user, filter_type=filter_type, now=datetime.now()))


@attendance_bp.route('/segna_assenza/<event_type>/<int:event_id>', methods=['POST'])
@login_required
def segna_assenza(event_type, event_id):
    try:
        message, category = toggle_user_absence(event_type, event_id, current_user.id, request.form.get('reason', ''))
        flash(message, category)
    except AttendanceValidationError as exc:
        flash(str(exc), 'danger')
    except Exception as exc:
        db.session.rollback()
        flash('Errore nel salvare l\'assenza. Riprova.', 'danger')
        current_app.logger.exception('Errore in segna_assenza: %s', exc)
    return _redirect_to_attendance()


@attendance_bp.route('/segna_ritardo/<int:training_id>', methods=['POST'])
@login_required
def segna_ritardo(training_id):
    message, category = toggle_training_late(training_id, current_user.id, request.form.get('reason', ''))
    flash(message, category)
    return _redirect_to_attendance()


@attendance_bp.route('/modifica_training/<int:training_id>', methods=['POST'])
@login_required
def modifica_training(training_id):
    if not can_manage_attendance(current_user):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_attendance()

    training = db.get_or_404(Training, training_id)
    update_training(
        training,
        start_time=request.form.get('start_time'),
        end_time=request.form.get('end_time'),
        is_cancelled=request.form.get('is_cancelled') == 'on',
        coach_notes=request.form.get('coach_notes', ''),
        coach_notes_private=request.form.get('coach_notes_private', ''),
    )
    flash('Allenamento modificato!', 'success')
    return _redirect_to_attendance()


@attendance_bp.route('/segna_assenza_membro/<event_type>/<int:event_id>/<int:user_id>', methods=['POST'])
@login_required
def segna_assenza_membro(event_type, event_id, user_id):
    if not can_manage_attendance(current_user):
        flash('Non hai i permessi!', 'danger')
        return _redirect_to_attendance()

    try:
        user = db.get_or_404(User, user_id)
        message, category = toggle_member_absence(event_type, event_id, user, request.form.get('reason', ''))
        flash(message, category)
    except AttendanceValidationError as exc:
        flash(str(exc), 'danger')
    except Exception as exc:
        db.session.rollback()
        flash('Errore nel salvare l\'assenza. Riprova.', 'danger')
        current_app.logger.exception('Errore in segna_assenza_membro: %s', exc)

    return _redirect_to_attendance()
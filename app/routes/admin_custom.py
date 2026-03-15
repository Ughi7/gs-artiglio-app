import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, User, UserFeedback, AppRelease, UserSeenRelease
from app.utils.json_services import JsonValidationError, parse_bool, parse_optional_text, parse_positive_int, require_json_object
from app.utils.notifications import crea_notifica, get_nome_giocatore, send_push_notification
from app.utils.admin_skin_service import (
    ASSIGNABLE_SKINS,
    InvalidSkinError,
    apply_retroactive_top_skins,
    assign_skin_to_users,
    build_admin_skin_users_data,
    decrement_skin_counter,
    delete_skin_note,
    edit_skin_note,
    increment_skin_counter,
)

admin_custom_bp = Blueprint('admin_custom', __name__)

ALLOWED_FEEDBACK_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic', 'heif', 'mp4', 'mov', 'm4v'}
VALID_FEEDBACK_STATUS = {'pending', 'in_progress', 'resolved', 'rejected'}
@admin_custom_bp.route('/aggiornamenti')
@login_required
def aggiornamenti():
    releases = AppRelease.query.order_by(AppRelease.release_date.desc()).all()
    my_feedbacks = UserFeedback.query.filter_by(user_id=current_user.id).order_by(UserFeedback.created_at.desc()).all()
    return render_template('aggiornamenti.html', releases=releases, my_feedbacks=my_feedbacks)

@admin_custom_bp.route('/invia-feedback', methods=['POST'])
@login_required
def invia_feedback():
    feedback_type = request.form.get('feedback_type', 'bug')
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    
    if not title or not description:
        flash('Titolo e descrizione sono obbligatori.', 'danger')
        return redirect(url_for('admin_custom.aggiornamenti'))
    
    media_path = None
    if 'media' in request.files:
        file = request.files['media']
        if file and file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if ext in ALLOWED_FEEDBACK_EXTENSIONS:
                filename = f"{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
                filepath = os.path.join(current_app.config['FEEDBACK_UPLOAD_FOLDER'], filename)
                os.makedirs(current_app.config['FEEDBACK_UPLOAD_FOLDER'], exist_ok=True)
                file.save(filepath)
                media_path = f"feedback/{filename}"
            else:
                flash(f'Formato file non supportato. Usa: {", ".join(ALLOWED_FEEDBACK_EXTENSIONS)}', 'danger')
                return redirect(url_for('admin_custom.aggiornamenti'))
    
    feedback = UserFeedback(
        user_id=current_user.id,
        feedback_type=feedback_type,
        title=title,
        description=description,
        media_path=media_path
    )
    db.session.add(feedback)
    db.session.commit()
    
    tipo_label = "Segnalazione bug" if feedback_type == 'bug' else "Proposta"
    flash(f'{tipo_label} inviata con successo! Grazie per il tuo feedback.', 'success')
    
    try:
        admin_user = User.query.filter_by(is_admin=True).first()
        if admin_user:
            emoji = "🐛" if feedback_type == 'bug' else "💡"
            send_push_notification(
                admin_user.id,
                f"{emoji} Nuovo Feedback",
                f"{get_nome_giocatore(current_user)}: {title[:50]}{'...' if len(title) > 50 else ''}",
                '/admin/feedback'
            )
    except Exception as e:
        print(f"[FEEDBACK] Errore invio notifica admin: {e}")
    
    return redirect(url_for('admin_custom.aggiornamenti'))

@admin_custom_bp.route('/api/dismiss-release', methods=['POST'])
@login_required
def dismiss_release():
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload release non valido.')
        release_id = parse_positive_int(data.get('release_id'), 'release_id')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    existing = UserSeenRelease.query.filter_by(user_id=current_user.id, release_id=release_id).first()
    if not existing:
        seen = UserSeenRelease(user_id=current_user.id, release_id=release_id)
        db.session.add(seen)
        db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/feedback')
@login_required
def admin_feedback():
    if not current_user.is_admin:
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard.home'))
    
    feedbacks = UserFeedback.query.order_by(UserFeedback.created_at.desc()).all()
    return render_template('admin_feedback.html', feedbacks=feedbacks)

@admin_custom_bp.route('/admin/feedback/<int:feedback_id>/update', methods=['POST'])
@login_required
def update_feedback_status(feedback_id):
    if not current_user.is_admin: return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    feedback = db.get_or_404(UserFeedback, feedback_id)
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload feedback non valido.')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    
    if 'status' in data:
        status = parse_optional_text(data.get('status'), 'Status', max_length=20)
        if status not in VALID_FEEDBACK_STATUS:
            return jsonify({'success': False, 'error': 'Status non valido'}), 400
        feedback.status = status

    if 'admin_response' in data:
        feedback.admin_response = parse_optional_text(data.get('admin_response'), 'Risposta admin', max_length=2000) or ''

    if 'status' not in data and 'admin_response' not in data:
        return jsonify({'success': False, 'error': 'Nessun campo aggiornabile fornito'}), 400

    db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    if not current_user.is_admin: return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    feedback = db.get_or_404(UserFeedback, feedback_id)
    
    if feedback.media_path:
        try:
            full_path = os.path.join(current_app.config['FEEDBACK_UPLOAD_FOLDER'], os.path.basename(feedback.media_path))
            if os.path.exists(full_path): os.remove(full_path)
        except Exception as e:
            print(f"Errore eliminazione media feedback: {e}")

    db.session.delete(feedback)
    db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/aggiornamenti/nuovo', methods=['POST'])
@login_required
def nuovo_aggiornamento():
    if not current_user.is_admin:
        flash('Accesso non autorizzato.', 'danger')
        return redirect(url_for('dashboard.home'))
    
    version = request.form.get('version', '').strip()
    title = request.form.get('title', '').strip()
    notes = request.form.get('notes', '').strip()
    is_major = request.form.get('is_major') == 'on'
    
    if not version or not title or not notes:
        flash('Tutti i campi sono obbligatori.', 'danger')
        return redirect(url_for('admin_custom.aggiornamenti'))
    
    existing = AppRelease.query.filter_by(version=version).first()
    if existing:
        flash(f'La versione {version} esiste già.', 'danger')
        return redirect(url_for('admin_custom.aggiornamenti'))
    
    release = AppRelease(version=version, title=title, notes=notes, is_major=is_major)
    db.session.add(release)
    db.session.commit()
    
    try:
        emoji = "🚀" if is_major else "📱"
        crea_notifica('aggiornamento', f"{emoji} Nuovo aggiornamento v{version}: {title}", icon=emoji)
    except Exception as e:
        print(f"[RELEASE] Errore invio notifica: {e}")
    
    flash(f'Aggiornamento v{version} pubblicato!', 'success')
    return redirect(url_for('admin_custom.aggiornamenti'))

@admin_custom_bp.route('/admin/aggiornamenti/<int:release_id>/update', methods=['POST'])
@login_required
def update_aggiornamento(release_id):
    if not current_user.is_admin: return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    release = db.get_or_404(AppRelease, release_id)
    try:
        data = require_json_object(request.get_json(silent=True), 'Payload aggiornamento non valido.')
    except JsonValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    updated = False
    
    if 'version' in data:
        new_version = parse_optional_text(data.get('version'), 'Versione', max_length=20)
        if not new_version:
            return jsonify({'success': False, 'error': 'Versione obbligatoria'}), 400
        if new_version != release.version:
            existing = AppRelease.query.filter_by(version=new_version).first()
            if existing: return jsonify({'success': False, 'error': f'Versione {new_version} già esistente'}), 400
            release.version = new_version
        updated = True

    if 'title' in data:
        title = parse_optional_text(data.get('title'), 'Titolo', max_length=100)
        if not title:
            return jsonify({'success': False, 'error': 'Titolo obbligatorio'}), 400
        release.title = title
        updated = True

    if 'notes' in data:
        notes = parse_optional_text(data.get('notes'), 'Note', max_length=10000)
        if not notes:
            return jsonify({'success': False, 'error': 'Note obbligatorie'}), 400
        release.notes = notes
        updated = True

    if 'is_major' in data:
        release.is_major = parse_bool(data.get('is_major'), 'Flag is_major')
        updated = True

    if not updated:
        return jsonify({'success': False, 'error': 'Nessun campo aggiornabile fornito'}), 400
    
    db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/aggiornamenti/<int:release_id>/delete', methods=['POST'])
@login_required
def delete_aggiornamento(release_id):
    if not current_user.is_admin: return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    release = db.get_or_404(AppRelease, release_id)
    UserSeenRelease.query.filter_by(release_id=release_id).delete()
    db.session.delete(release)
    db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/assegna-skin', methods=['GET', 'POST'])
@login_required
def admin_assegna_skin():
    if not current_user.is_admin:
        flash('Accesso non autorizzato!', 'danger')
        return redirect(url_for('dashboard.home'))

    risultati = []

    if request.method == 'POST':
        action = request.form.get('action', 'assign')

        try:
            if action == 'assign':
                risultati.extend(assign_skin_to_users(request.form.get('skin_id'), request.form.getlist('user_ids')))
            elif action == 'increment_counter':
                result = increment_skin_counter(
                    request.form.get('skin_id'),
                    request.form.get('user_id'),
                    request.form.get('note', '').strip(),
                    now=datetime.now(),
                )
                if result:
                    risultati.append(result)
            elif action == 'decrement_counter':
                result = decrement_skin_counter(request.form.get('skin_id'), request.form.get('user_id'))
                if result:
                    risultati.append(result)
            elif action == 'delete_note':
                result = delete_skin_note(request.form.get('user_id'), request.form.get('note_index'))
                if result:
                    risultati.append(result)
            elif action == 'edit_note':
                result = edit_skin_note(
                    request.form.get('user_id'),
                    request.form.get('note_index'),
                    request.form.get('new_text', '').strip(),
                )
                if result:
                    risultati.append(result)
        except InvalidSkinError:
            invalid_message = 'Skin non valida per incremento.' if action == 'increment_counter' else 'Skin non valida.'
            if action == 'assign':
                invalid_message = 'Skin non valida!'
            flash(invalid_message, 'danger')
            return redirect(url_for('admin_custom.admin_assegna_skin'))

    return render_template('admin_assegna_skin.html', skins=ASSIGNABLE_SKINS, users=build_admin_skin_users_data(), risultati=risultati)

@admin_custom_bp.route('/admin/fix-top-skins-retroattiva')
@login_required
def admin_fix_top_skins_retroattiva():
    if not current_user.is_admin:
        flash('Accesso non autorizzato!', 'danger')
        return redirect(url_for('dashboard.home'))

    total_assigned, assigned_details = apply_retroactive_top_skins()

    if total_assigned > 0:
        flash(f'Sincronizzazione completata! Assegnate {total_assigned} skin retroattive ({", ".join(assigned_details)}).', 'success')
    else:
        flash('Tutti i vincitori dei Top Badge possiedono già le relative skin. Nessuna nuova assegnazione necessaria.', 'info')

    return redirect(url_for('dashboard.admin_assegna_badge_mensili'))

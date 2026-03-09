import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, User, UserFeedback, AppRelease, UserSeenRelease, FlappyGameProfile, Achievement, UserAchievement
from app.utils.json_services import JsonValidationError, parse_bool, parse_optional_text, parse_positive_int, require_json_object
from app.utils.notifications import crea_notifica, get_nome_giocatore, send_push_notification

admin_custom_bp = Blueprint('admin_custom', __name__)

ALLOWED_FEEDBACK_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
VALID_FEEDBACK_STATUS = {'pending', 'in_progress', 'resolved', 'rejected'}


def _build_flappy_profile(user_id):
    return FlappyGameProfile(
        user_id=user_id,
        unlocked_skins='["default"]',
        selected_skin='default',
        bug_report_notes='[]'
    )


def _get_or_create_flappy_profile(user_id):
    profile = FlappyGameProfile.query.filter_by(user_id=user_id).first()
    if profile:
        return profile

    profile = _build_flappy_profile(user_id)
    db.session.add(profile)
    db.session.flush()
    return profile

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
        return redirect(url_for('main.home'))
    
    feedbacks = UserFeedback.query.order_by(UserFeedback.created_at.desc()).all()
    return render_template('admin_feedback.html', feedbacks=feedbacks)

@admin_custom_bp.route('/admin/feedback/<int:feedback_id>/update', methods=['POST'])
@login_required
def update_feedback_status(feedback_id):
    if not current_user.is_admin: return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    feedback = UserFeedback.query.get_or_404(feedback_id)
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
    feedback = UserFeedback.query.get_or_404(feedback_id)
    
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
        return redirect(url_for('main.home'))
    
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
    release = AppRelease.query.get_or_404(release_id)
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
    release = AppRelease.query.get_or_404(release_id)
    UserSeenRelease.query.filter_by(release_id=release_id).delete()
    db.session.delete(release)
    db.session.commit()
    return jsonify({'success': True})

@admin_custom_bp.route('/admin/assegna-skin', methods=['GET', 'POST'])
@login_required
def admin_assegna_skin():
    if not current_user.is_admin:
        flash('Accesso non autorizzato!', 'danger')
        return redirect(url_for('main.home'))
    
    ASSIGNABLE_SKINS = {
        'ladybug': {'name': 'Coccinella', 'icon': '🐞', 'event': '3 Segnalazioni Bug/Feedback', 'type': 'counter', 'threshold': 3, 'counter_field': 'bug_report_count'},
    }
    
    risultati = []
    
    if request.method == 'POST':
        action = request.form.get('action', 'assign')
        
        if action == 'assign':
            skin_id = request.form.get('skin_id')
            user_ids = request.form.getlist('user_ids')
            if skin_id not in ASSIGNABLE_SKINS:
                flash('Skin non valida!', 'danger')
                return redirect(url_for('admin_custom.admin_assegna_skin'))
            
            skin_info = ASSIGNABLE_SKINS[skin_id]
            for uid in user_ids:
                user = db.session.get(User, int(uid))
                if not user: continue
                profile = _get_or_create_flappy_profile(user.id)
                unlocked = json.loads(profile.unlocked_skins)
                if skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    crea_notifica('skin_unlock', f'🎨 {get_nome_giocatore(user)} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]}', icon=skin_info['icon'])
                    risultati.append({'user': get_nome_giocatore(user), 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': 'Assegnata!'})
                else: risultati.append({'user': get_nome_giocatore(user), 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': 'Già sbloccata'})
            db.session.commit()
        
        elif action == 'increment_counter':
            skin_id = request.form.get('skin_id')
            user_id = request.form.get('user_id')
            note = request.form.get('note', '').strip()
            
            if skin_id not in ASSIGNABLE_SKINS or ASSIGNABLE_SKINS[skin_id].get('type') != 'counter':
                flash('Skin non valida per incremento.', 'danger')
                return redirect(url_for('admin_custom.admin_assegna_skin'))
            
            skin_info = ASSIGNABLE_SKINS[skin_id]
            user = db.session.get(User, int(user_id))
            if user:
                profile = _get_or_create_flappy_profile(user.id)
                counter_field = skin_info['counter_field']
                new_val = (getattr(profile, counter_field, 0) or 0) + 1
                setattr(profile, counter_field, new_val)
                
                notes = json.loads(profile.bug_report_notes or '[]')
                notes.append({'note': note or '(nessuna descrizione)', 'date': datetime.now().strftime('%d/%m/%Y %H:%M')})
                profile.bug_report_notes = json.dumps(notes)
                
                unlocked = json.loads(profile.unlocked_skins)
                if new_val >= skin_info['threshold'] and skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    crea_notifica('skin_unlock', f'🎨 {get_nome_giocatore(user)} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]} {skin_info["event"]}', icon=skin_info['icon'])
                    risultati.append({'user': get_nome_giocatore(user), 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': f'Counter {new_val}/{skin_info["threshold"]} - SKIN SBLOCCATA! 🎉'})
                else: risultati.append({'user': get_nome_giocatore(user), 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': f'Counter aggiornato: {new_val}/{skin_info["threshold"]}'})
                db.session.commit()
                
        elif action == 'decrement_counter':
            skin_id = request.form.get('skin_id')
            user_id = request.form.get('user_id')
            if skin_id not in ASSIGNABLE_SKINS or ASSIGNABLE_SKINS[skin_id].get('type') != 'counter': return redirect(url_for('admin_custom.admin_assegna_skin'))
            
            user = db.session.get(User, int(user_id))
            if user:
                profile = _get_or_create_flappy_profile(user.id)
                if profile:
                    counter_field = ASSIGNABLE_SKINS[skin_id]['counter_field']
                    new_val = max(0, (getattr(profile, counter_field, 0) or 0) - 1)
                    setattr(profile, counter_field, new_val)
                    risultati.append({'user': get_nome_giocatore(user), 'skin': ASSIGNABLE_SKINS[skin_id]['name'], 'icon': ASSIGNABLE_SKINS[skin_id]['icon'], 'status': f'Counter aggiornato: {new_val}/{ASSIGNABLE_SKINS[skin_id]["threshold"]}'})
                    db.session.commit()
                    
        elif action == 'delete_note':
            user_id = request.form.get('user_id')
            note_index = request.form.get('note_index')
            if user_id and note_index is not None:
                profile = _get_or_create_flappy_profile(int(user_id))
                if profile:
                    try:
                        idx = int(note_index)
                        notes = json.loads(profile.bug_report_notes or '[]')
                        if 0 <= idx < len(notes):
                            del notes[idx]
                            profile.bug_report_notes = json.dumps(notes)
                            db.session.commit()
                            risultati.append({'user': get_nome_giocatore(db.session.get(User, int(user_id))), 'skin': 'Segnalazioni', 'icon': '📝', 'status': 'Nota eliminata'})
                    except ValueError: pass
                    
        elif action == 'edit_note':
            user_id = request.form.get('user_id')
            note_index = request.form.get('note_index')
            new_text = request.form.get('new_text', '').strip()
            if user_id and note_index is not None and new_text:
                profile = _get_or_create_flappy_profile(int(user_id))
                if profile:
                    try:
                        idx = int(note_index)
                        notes = json.loads(profile.bug_report_notes or '[]')
                        if 0 <= idx < len(notes):
                            notes[idx]['note'] = new_text
                            profile.bug_report_notes = json.dumps(notes)
                            db.session.commit()
                            risultati.append({'user': get_nome_giocatore(db.session.get(User, int(user_id))), 'skin': 'Segnalazioni', 'icon': '📝', 'status': 'Nota modificata'})
                    except ValueError: pass

    from sqlalchemy import or_
    users = User.query.filter(or_(User.is_admin == False, User.is_admin == None)).order_by(User.nome_completo).all()
    user_ids = [user.id for user in users]
    profiles_by_user_id = {
        profile.user_id: profile
        for profile in FlappyGameProfile.query.filter(FlappyGameProfile.user_id.in_(user_ids)).all()
    } if user_ids else {}

    missing_profiles = []
    for user in users:
        if user.id not in profiles_by_user_id:
            profile = _build_flappy_profile(user.id)
            missing_profiles.append(profile)
            profiles_by_user_id[user.id] = profile

    if missing_profiles:
        db.session.add_all(missing_profiles)
        db.session.commit()

    users_data = []
    for u in users:
        profile = profiles_by_user_id.get(u.id)
        unlocked = json.loads(profile.unlocked_skins) if profile else []
        counters = {}
        for sid, sinfo in ASSIGNABLE_SKINS.items():
            if sinfo.get('type') == 'counter' and profile:
                try: counters[sid] = getattr(profile, sinfo['counter_field'], 0) or 0
                except Exception: counters[sid] = 0
        users_data.append({
            'id': u.id,
            'nome': get_nome_giocatore(u),
            'skins': {sid: (sid in unlocked) for sid in ASSIGNABLE_SKINS},
            'counters': counters,
            'notes': json.loads(profile.bug_report_notes or '[]') if profile else []
        })
    
    return render_template('admin_assegna_skin.html', skins=ASSIGNABLE_SKINS, users=users_data, risultati=risultati)

@admin_custom_bp.route('/admin/fix-top-skins-retroattiva')
@login_required
def admin_fix_top_skins_retroattiva():
    if not current_user.is_admin:
        flash('Accesso non autorizzato!', 'danger')
        return redirect(url_for('main.home'))
    
    top_badge_skin_map = {
        'top_donatore_mese': 'mosquito',
        'top_denunciatore_mese': 'raven',
        'top_mvp_mese': 'dove',
        'top_floppy_mese': 'goat'
    }
    
    total_assigned = 0
    assigned_details = []
    
    for badge_code, skin_id in top_badge_skin_map.items():
        badge = Achievement.query.filter_by(code=badge_code).first()
        if not badge: continue
        
        winners = UserAchievement.query.filter_by(achievement_id=badge.id).all()
        count_for_badge = 0
        
        for ua in winners:
            profile = FlappyGameProfile.query.filter_by(user_id=ua.user_id).first()
            if profile:
                unlocked = json.loads(profile.unlocked_skins)
                if skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    
                    user = db.session.get(User, ua.user_id)
                    skin_name = {"mosquito": "ZANZARA 🦟", "raven": "CORVO 🐦‍⬛", "dove": "COLOMBA 🕊️", "goat": "CAPRA 🐐"}.get(skin_id, skin_id.capitalize())
                    crea_notifica('skin_unlock', f'🎨 {get_nome_giocatore(user)} ha sbloccato la skin {skin_name} tramite recupero premi passati!', icon='✨', send_push=True)
                    
                    count_for_badge += 1
                    total_assigned += 1
        
        if count_for_badge > 0: assigned_details.append(f"{count_for_badge} {skin_id}")
            
    db.session.commit()
    
    if total_assigned > 0:
        flash(f'Sincronizzazione completata! Assegnate {total_assigned} skin retroattive ({", ".join(assigned_details)}).', 'success')
    else:
        flash('Tutti i vincitori dei Top Badge possiedono già le relative skin. Nessuna nuova assegnazione necessaria.', 'info')
        
    return redirect(url_for('main.admin_assegna_badge_mensili'))

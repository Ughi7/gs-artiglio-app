import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import bcrypt
from app.models import User, db
from app.utils.helpers import allowed_file
from app.utils.profile_service import build_profile_context


profile_bp = Blueprint('profile', __name__)


def _redirect_to_profile():
    return redirect(url_for('profile.profilo'))


@profile_bp.route('/profilo')
@login_required
def profilo():
    return render_template('profilo.html', **build_profile_context(current_user, viewing_other=False, now=datetime.now()))


@profile_bp.route('/profilo/<int:user_id>')
@login_required
def profilo_giocatore(user_id):
    user = db.get_or_404(User, user_id)
    return render_template('profilo.html', **build_profile_context(user, viewing_other=True, now=datetime.now()))


@profile_bp.route('/salva_bio', methods=['POST'])
@login_required
def salva_bio():
    bio = request.form.get('bio', '').strip()
    current_user.bio = bio if bio else None
    db.session.commit()
    flash('Bio aggiornata!', 'success')
    return _redirect_to_profile()


@profile_bp.route('/upload_certificato', methods=['POST'])
@login_required
def upload_certificato():
    try:
        if 'certificato_file' not in request.files:
            flash('Nessun file selezionato', 'danger')
            return _redirect_to_profile()

        file = request.files['certificato_file']
        data_scadenza_str = request.form.get('data_scadenza')

        if file.filename == '' and data_scadenza_str:
            try:
                data_scadenza = datetime.strptime(data_scadenza_str, '%Y-%m-%d').date()
                current_user.medical_expiry = data_scadenza
                db.session.commit()
                flash('✅ Data di scadenza aggiornata con successo!', 'success')
                return _redirect_to_profile()
            except ValueError:
                flash('Formato data non valido', 'danger')
                return _redirect_to_profile()

        if file.filename == '':
            flash('Seleziona un file da caricare', 'warning')
            return _redirect_to_profile()

        if not data_scadenza_str:
            flash('Inserisci la data di scadenza', 'warning')
            return _redirect_to_profile()

        if not allowed_file(file.filename):
            flash('❌ Formato file non consentito. Usa: PDF, JPG, JPEG, PNG', 'danger')
            return _redirect_to_profile()

        username_clean = current_user.username.replace(' ', '_').lower()
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f'cert_{current_user.id}_{username_clean}.{file_ext}'

        if current_user.medical_file:
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.medical_file)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as exc:
                    print(f'Errore eliminazione vecchio certificato: {exc}')

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            data_scadenza = datetime.strptime(data_scadenza_str, '%Y-%m-%d').date()
            current_user.medical_file = filename
            current_user.medical_expiry = data_scadenza
            db.session.commit()
            flash('✅ Certificato medico caricato con successo!', 'success')
        except ValueError:
            flash('Formato data non valido', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
    except Exception as exc:
        flash(f'❌ Errore durante il caricamento: {str(exc)}', 'danger')
        print(f'Errore upload certificato: {exc}')

    return _redirect_to_profile()


@profile_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if not current_pw or not new_pw or not confirm_pw:
        flash('Compila tutti i campi', 'danger')
        return _redirect_to_profile()

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        flash('Password attuale non corretta', 'danger')
        return _redirect_to_profile()

    if new_pw != confirm_pw:
        flash('Le nuove password non coincidono', 'danger')
        return _redirect_to_profile()

    if len(new_pw) < 6:
        flash('La password deve avere almeno 6 caratteri', 'danger')
        return _redirect_to_profile()

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    flash('Password aggiornata con successo!', 'success')
    return _redirect_to_profile()
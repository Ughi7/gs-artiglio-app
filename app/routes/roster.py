from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import bcrypt
from app.models import User, db
from app.utils.helpers import generate_temporary_password, get_roles_from_form
from app.utils.roster_service import build_roster_context


roster_bp = Blueprint('roster', __name__)


def _redirect_to_roster():
    return redirect(url_for('roster.rosa'))


@roster_bp.route('/rosa')
@login_required
def rosa():
    return render_template('rosa.html', **build_roster_context())


@roster_bp.route('/aggiungi_giocatore', methods=['POST'])
@login_required
def aggiungi_giocatore():
    if not current_user.is_admin:
        return _redirect_to_roster()

    username = request.form.get('username')
    if User.query.filter_by(username=username).first():
        flash('Username esistente', 'danger')
        return _redirect_to_roster()

    roles = get_roles_from_form(request)
    temporary_password = generate_temporary_password()
    user = User(
        username=username,
        password_hash=bcrypt.generate_password_hash(temporary_password).decode('utf-8'),
        nome_completo=request.form.get('nome_completo'),
        soprannome=request.form.get('soprannome'),
        numero_maglia=int(request.form.get('numero_maglia') or 0),
        ruolo_volley=request.form.get('ruolo_volley'),
        **roles,
    )
    db.session.add(user)
    db.session.commit()

    flash(f'Giocatore aggiunto. Password temporanea per {user.username}: {temporary_password}', 'success')
    return _redirect_to_roster()


@roster_bp.route('/modifica_giocatore', methods=['POST'])
@login_required
def modifica_giocatore():
    if not current_user.is_admin:
        return _redirect_to_roster()

    user = db.session.get(User, int(request.form.get('user_id')))
    if user:
        user.nome_completo = request.form.get('nome_completo')
        user.soprannome = request.form.get('soprannome')
        user.numero_maglia = request.form.get('numero_maglia')
        user.ruolo_volley = request.form.get('ruolo_volley')
        roles = get_roles_from_form(request)
        for key, value in roles.items():
            setattr(user, key, value)
        db.session.commit()
        flash('Aggiornato', 'success')

    return _redirect_to_roster()
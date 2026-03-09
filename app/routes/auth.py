from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app import bcrypt
from app.utils.cron_helpers import maybe_update_all_streaks
from app.utils.helpers import _env_str, _require_setup_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/crea_admin')
def crea_admin():
    _require_setup_token()
    admin_username = _env_str('BOOTSTRAP_ADMIN_USERNAME', 'admin')
    admin_password = _env_str('BOOTSTRAP_ADMIN_PASSWORD')
    admin_full_name = _env_str('BOOTSTRAP_ADMIN_FULL_NAME', 'Admin User')
    admin_nickname = _env_str('BOOTSTRAP_ADMIN_NICKNAME', 'Admin')

    if not admin_password:
        return 'Configura BOOTSTRAP_ADMIN_PASSWORD prima di usare questa route', 400

    if User.query.filter_by(username=admin_username).first(): 
        return "Admin esiste già"
    
    hashed_pw = bcrypt.generate_password_hash(admin_password).decode('utf-8')
    admin = User(
        username=admin_username,
        password_hash=hashed_pw,
        nome_completo=admin_full_name,
        soprannome=admin_nickname,
        is_admin=True,
    )
    db.session.add(admin)
    db.session.commit()
    return "Admin creato"

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and bcrypt.check_password_hash(user.password_hash, request.form.get('password')):
            session.permanent = True  # Rendi la sessione permanente (7 giorni)
            login_user(user)
            # Streak batch: solo dopo le 09:00 e max 1/giorno (evita notifiche notturne)
            maybe_update_all_streaks()
            return redirect(url_for('main.home'))
        else: 
            flash('Login fallito.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

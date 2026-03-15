import os
from datetime import datetime
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect, generate_csrf

# Import the database object from models
from app.models import db, User

# We'll import the admin setup function we just created
from app.admin import init_admin
from config import Config

# Extension initialization
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def create_app():
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app = Flask(__name__, 
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    Config.init_app(app)

    try:
        from flask_compress import Compress
        Compress(app)
    except ImportError:
        pass

    # --------------------
    # INIT EXTENSIONS
    # --------------------
    db.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    init_admin(app)

    # --------------------
    # REGISTER BLUEPRINTS
    # --------------------
    from app.routes.dashboard import dashboard_bp
    from app.routes.auth import auth_bp
    from app.routes.fines import fines_bp
    from app.routes.profile import profile_bp
    from app.routes.roster import roster_bp
    from app.routes.attendance import attendance_bp
    from app.routes.matches import matches_bp
    from app.routes.calendar import calendar_bp
    from app.routes.game import game_bp
    from app.routes.video import video_bp
    from app.routes.api import api_bp
    from app.routes.admin_custom import admin_custom_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(fines_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(roster_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(video_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_custom_bp)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_now():
        return {
            'now': datetime.now,
            'csrf_token': generate_csrf
        }

    return app

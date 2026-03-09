import json
import os
import secrets
from datetime import timedelta

from app.utils.helpers import _env_str


class Config:
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'certificati')
    VIDEO_UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'videos')
    FILES_UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'files')
    FEEDBACK_UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'feedback')

    @classmethod
    def init_app(cls, app):
        app.config['SECRET_KEY'] = _env_str('SECRET_KEY') or secrets.token_hex(32)
        app.config['SQLALCHEMY_DATABASE_URI'] = _env_str('DATABASE_URL', f"sqlite:///{os.path.join(cls.BASEDIR, 'artiglio.db')}")
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=300)
        app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
        app.config['UPLOAD_FOLDER'] = cls.UPLOAD_FOLDER
        app.config['VIDEO_UPLOAD_FOLDER'] = cls.VIDEO_UPLOAD_FOLDER
        app.config['FILES_UPLOAD_FOLDER'] = cls.FILES_UPLOAD_FOLDER
        app.config['FEEDBACK_UPLOAD_FOLDER'] = cls.FEEDBACK_UPLOAD_FOLDER
        app.config['VAPID_PRIVATE_KEY'] = _env_str('VAPID_PRIVATE_KEY')
        app.config['VAPID_PUBLIC_KEY'] = _env_str('VAPID_PUBLIC_KEY')
        app.config['VAPID_CLAIM_EMAIL'] = _env_str('VAPID_CLAIM_EMAIL')
        cls._load_vapid_config(app)
        cls._ensure_upload_folders(app)

    @classmethod
    def _load_vapid_config(cls, app):
        if app.config['VAPID_PRIVATE_KEY'] and app.config['VAPID_PUBLIC_KEY'] and app.config['VAPID_CLAIM_EMAIL']:
            return

        vapid_path = os.path.join(cls.BASEDIR, 'vapid_json_config.json')
        try:
            with open(vapid_path, 'r', encoding='utf-8') as file_handle:
                vapid_config = json.load(file_handle)
        except Exception:
            return

        app.config['VAPID_PRIVATE_KEY'] = app.config['VAPID_PRIVATE_KEY'] or vapid_config.get('VAPID_PRIVATE_KEY')
        app.config['VAPID_PUBLIC_KEY'] = app.config['VAPID_PUBLIC_KEY'] or vapid_config.get('VAPID_PUBLIC_KEY')
        app.config['VAPID_CLAIM_EMAIL'] = app.config['VAPID_CLAIM_EMAIL'] or vapid_config.get('VAPID_CLAIM_EMAIL')

    @classmethod
    def _ensure_upload_folders(cls, app):
        for folder in (
            app.config['UPLOAD_FOLDER'],
            app.config['VIDEO_UPLOAD_FOLDER'],
            app.config['FILES_UPLOAD_FOLDER'],
            app.config['FEEDBACK_UPLOAD_FOLDER'],
        ):
            os.makedirs(folder, exist_ok=True)
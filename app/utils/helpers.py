import os
import secrets
import string
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    """Verifica che il file abbia un'estensione consentita"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_roles_from_form(req):
    return {
        'is_admin': req.form.get('is_admin') == 'on',
        'is_notaio': req.form.get('is_notaio') == 'on',
        'is_capitano': req.form.get('is_capitano') == 'on',
        'is_pizza': req.form.get('is_pizza') == 'on',
        'is_birra': req.form.get('is_birra') == 'on',
        'is_smm': req.form.get('is_smm') == 'on',
        'is_preparatore': req.form.get('is_preparatore') == 'on',
        'is_convenzioni': req.form.get('is_convenzioni') == 'on',
        'is_abbigliamento': req.form.get('is_abbigliamento') == 'on',
        'is_sponsor': req.form.get('is_sponsor') == 'on',
        'is_pensionato': req.form.get('is_pensionato') == 'on',
        'is_gemellaggi': req.form.get('is_gemellaggi') == 'on',
        'is_coach': req.form.get('is_coach') == 'on',
        'is_catering': req.form.get('is_catering') == 'on',
        'is_scout': req.form.get('is_scout') == 'on',
        'is_dirigente': req.form.get('is_dirigente') == 'on',
        'is_presidente': req.form.get('is_presidente') == 'on'
    }

def _env_str(key: str, default: str | None = None) -> str | None:
    val = os.environ.get(key)
    if val is None:
        return default
    val = val.strip()
    return val if val != '' else default

def _env_bool(key: str, default: bool = False) -> bool:
    val = _env_str(key)
    if val is None:
        return default
    return val.lower() in {'1', 'true', 'yes', 'y', 'on'}

def _setup_routes_allowed() -> bool:
    return _env_bool('ALLOW_SETUP_ROUTES', default=False)

def _require_setup_token() -> None:
    from flask import request, abort
    if not _setup_routes_allowed():
        abort(404)
    expected = _env_str('SETUP_TOKEN')
    if not expected:
        abort(403)
    provided = (request.args.get('token') or '').strip()
    if provided != expected:
        abort(403)

def generate_temporary_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

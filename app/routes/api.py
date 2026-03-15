from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import db, PushSubscription, NotificationPreference
from app.utils.helpers import _require_setup_token

api_bp = Blueprint('api', __name__)


def _upsert_push_subscription(user_id, data):
    payload = data or {}
    endpoint = payload.get('endpoint')
    keys = payload.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({"success": False, "error": "Dati di sottoscrizione incompleti"}), 400

    subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not subscription:
        subscription = PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        db.session.add(subscription)
    else:
        subscription.user_id = user_id
        subscription.p256dh = p256dh
        subscription.auth = auth

    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=user_id)
        db.session.add(prefs)
    prefs.push_enabled = True

    db.session.commit()
    return jsonify({"success": True, "message": "Sottoscrizione registrata"})


def _remove_push_subscription(user_id, data):
    payload = data or {}
    endpoint = payload.get('endpoint')

    if endpoint:
        subscription = PushSubscription.query.filter_by(endpoint=endpoint).first()
        if subscription:
            db.session.delete(subscription)

    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    if prefs:
        prefs.push_enabled = False

    db.session.commit()
    return jsonify({"success": True})

@api_bp.route('/setup_db')
def setup_db():
    _require_setup_token()
    db.create_all()
    return "DB OK"

@api_bp.route('/sw.js')
def service_worker():
    from flask import send_file
    import os
    # Percorso standard: static/sw.js. Fallback al root storico per retrocompatibilità.
    static_sw_path = os.path.join(current_app.static_folder, 'sw.js')
    if os.path.exists(static_sw_path):
        sw_path = static_sw_path
    else:
        sw_path = os.path.join(os.path.dirname(current_app.root_path), 'sw.js')
    return send_file(sw_path, mimetype='application/javascript')

@api_bp.route('/get_vapid_public_key')
def get_vapid_public_key():
    return jsonify({"public_key": current_app.config['VAPID_PUBLIC_KEY']})

@api_bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    return _upsert_push_subscription(current_user.id, request.get_json(silent=True))

@api_bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    return _remove_push_subscription(current_user.id, request.get_json(silent=True))

@api_bp.route('/api/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    return _upsert_push_subscription(current_user.id, request.get_json(silent=True))

@api_bp.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    return _remove_push_subscription(current_user.id, request.get_json(silent=True))

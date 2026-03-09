from pywebpush import webpush, WebPushException
import urllib.parse
import json
from datetime import datetime
from flask import current_app
from app.models import db, User, NotificationPreference, PushSubscription, Notification

def send_push_notification(user_id, title, body, url='/', notification_type=None):
    """Invia una notifica push a un utente specifico"""
    user = db.session.get(User, user_id)
    if not user: return
    
    # Verifica preferenze notifiche
    prefs = NotificationPreference.query.filter_by(user_id=user_id).first()
    if prefs and not prefs.push_enabled:
        print(f"[PUSH] Utente {user.username} ha disabilitato le notifiche push")
        return
    
    # Verifica filtri per tipo di notifica
    if prefs and notification_type:
        tipo = notification_type.lower() if notification_type else ''
        should_skip = False
        
        if tipo == 'mvp' and not prefs.show_mvp:
            should_skip = True
        elif 'streak' in tipo and not prefs.show_streak:
            should_skip = True
        elif 'turno' in tipo and not prefs.show_turno:
            should_skip = True
        elif ('denuncia' in tipo or 'multa' in tipo) and not prefs.show_denuncia:
            should_skip = True
        elif ('flappy' in tipo or 'floppy' in tipo or 'skin_unlock' in tipo or 'leaderboard' in tipo) and not prefs.show_flappy:
            should_skip = True
        elif 'donator' in tipo and not prefs.show_donatore:
            should_skip = True
        elif ('certificato' in tipo or 'medical' in tipo) and not prefs.show_certificato:
            should_skip = True
        elif 'aggiornamento' in tipo and not prefs.show_aggiornamento:
            should_skip = True
        
        if should_skip:
            print(f"[PUSH] Utente {user.username} ha filtrato le notifiche di tipo '{tipo}'")
            return

    subscriptions = PushSubscription.query.filter_by(user_id=user_id).all()
    if not subscriptions: return

    for sub in subscriptions:
        try:
            # Estrai l'origine dall'endpoint per il claim "aud"
            parsed_url = urllib.parse.urlparse(sub.endpoint)
            audience = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Crea vapid_claims dinamici con audience corretta
            vapid_claims = {
                "sub": current_app.config['VAPID_CLAIM_EMAIL'],
                "aud": audience
            }
            
            payload = json.dumps({
                "title": title,
                "body": body,
                "icon": "/static/icons3/icon-192x192.png",
                "badge": "/static/icons3/icon-72x72.png",
                "data": {"url": url}
            })
            
            print(f'[PUSH] Invio a user_id={user_id}, endpoint={sub.endpoint[:50]}...')
            
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=payload,
                vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
                vapid_claims=vapid_claims
            )
            print(f'[PUSH] ✓ Notifica inviata con successo a user_id={user_id}')
        except WebPushException as ex:
            print(f'[PUSH] ✗ Errore invio a user_id={user_id}: {ex}')
            # Rimuovi subscription se obsoleta o invalida
            if ex.response and ex.response.status_code in [400, 401, 403, 404, 410]:
                print(f'[PUSH] Rimuovo sottoscrizione non valida (status {ex.response.status_code}) per user_id={user_id}')
                db.session.delete(sub)
                db.session.commit()
        except Exception as e:
            print(f"[PUSH] Errore generico invio a {user.username}: {e}")

def send_push_to_all(title, body, url='/', notification_type=None):
    """Invia notifica push a tutti gli utenti che hanno abilitato le notifiche"""
    users = User.query.all()
    for user in users:
        send_push_notification(user.id, title, body, url, notification_type)


def crea_notifica(tipo, messaggio, icon='📢', send_push=True, target_user_id=None):
    """Crea una nuova notifica nella bacheca e opzionalmente invia push"""
    notifica = Notification(
        tipo=tipo,
        messaggio=messaggio,
        icon=icon,
        data_creazione=datetime.now()
    )
    db.session.add(notifica)
    db.session.commit()
    
    # Invia push notification se richiesto
    if send_push:
        try:
            # Estrai titolo breve dal messaggio
            title = f"{icon} GS Artiglio"
            body = messaggio[:200] if len(messaggio) > 200 else messaggio
            
            print(f'[PUSH] Tentativo invio notifica: {title} - {body[:50]}...')
            
            if target_user_id:
                # Invia solo all'utente specifico
                print(f'[PUSH] Invio a utente specifico: {target_user_id}')
                send_push_notification(target_user_id, title, body, '/', tipo)
            else:
                # Invia a tutti gli utenti sottoscritti
                print(f'[PUSH] Invio a tutti gli utenti')
                send_push_to_all(title, body, '/', tipo)
        except Exception as e:
            print(f'[PUSH] Errore invio notifica: {e}')
            import traceback
            traceback.print_exc()

def get_nome_giocatore(user):
    """Restituisce il soprannome se presente, altrimenti il nome completo"""
    if not user:
        return "Giocatore"
    
    nome = user.soprannome if user.soprannome else user.nome_completo
    
    # Fallback se entrambi sono None o vuoti
    if not nome or nome.strip() == "":
        return f"Giocatore#{user.id}"
    
    return nome

from sqlalchemy import func, extract
from datetime import datetime, timedelta, date
from flask import current_app
from app.models import db, CashTransaction, Fine, Event, Achievement, UserAchievement, GlobalSettings, User, Notification
from app.utils.badge_service import assign_badge
from app.utils.fine_service import check_and_apply_late_fees
from app.utils.notifications import crea_notifica, send_push_notification, get_nome_giocatore

def assegna_badge_mensili(anno, mese):
    # 1. Top Donatore
    donazioni = db.session.query(CashTransaction.user_id, func.sum(CashTransaction.amount).label('totale')) \
        .filter(CashTransaction.transaction_type=='entrata',
                extract('year', CashTransaction.date)==anno,
                extract('month', CashTransaction.date)==mese) \
        .group_by(CashTransaction.user_id).all()
    if donazioni:
        top_donatore = max(donazioni, key=lambda x: x.totale)
        assign_badge(top_donatore.user_id, 'top_donatore_mese', anno, mese)

    # 2. Top Denunciatore
    denunce = db.session.query(Fine.denunciante_id, func.count(Fine.id).label('totale')) \
        .filter(Fine.denunciante_id != None,
                extract('year', Fine.date)==anno,
                extract('month', Fine.date)==mese) \
        .group_by(Fine.denunciante_id).all()
    if denunce:
        top_denunciatore = max(denunce, key=lambda x: x.totale)
        assign_badge(top_denunciatore.denunciante_id, 'top_denunciatore_mese', anno, mese)

    # 3. MVP del mese (escludi amichevoli)
    mvp_counts = db.session.query(Event.mvp_id, func.count(Event.id).label('totale')) \
        .filter(Event.mvp_id != None,
                Event.is_friendly == False,
                extract('year', Event.date_start)==anno,
                extract('month', Event.date_start)==mese) \
        .group_by(Event.mvp_id).all()
    if mvp_counts:
        top_mvp = max(mvp_counts, key=lambda x: x.totale)
        assign_badge(top_mvp.mvp_id, 'top_mvp_mese', anno, mese)

def get_mvp_deadline(event_date):
    # Calcola il Martedì successivo alla partita alle ore 12:00 (Mezzogiorno)
    days_ahead = 1 - event_date.weekday()
    if days_ahead <= 0: # Se il martedì è oggi o passato, vai al prossimo
        days_ahead += 7

    next_tuesday = event_date.date() + timedelta(days=days_ahead)
    deadline = datetime.combine(next_tuesday, datetime.min.time().replace(hour=12)) # 12:00
    return deadline

def check_medical_certificate_expiry(user):
    """Controlla la scadenza del certificato medico e invia notifiche push max una volta al giorno"""
    if not user.medical_expiry:
        return
    
    today = date.today()
    days_until_expiry = (user.medical_expiry - today).days
    
    thresholds = {
        30: "⚠️ Il tuo certificato medico scade tra 30 giorni!",
        21: "⚠️ Il tuo certificato medico scade tra 21 giorni!",
        14: "⚠️ ATTENZIONE: Il tuo certificato medico scade tra 14 giorni!",
        7: "⚠️ ATTENZIONE: Il tuo certificato medico scade tra 7 giorni!",
        1: "🚨 URGENTE: Il tuo certificato medico scade DOMANI!"
    }
    
    today_str = today.isoformat()
    limit_key = f'medical_notif_last_run_{user.id}'
    
    # Il throttle vive in GlobalSettings per evitare invii ripetuti nello stesso giorno
    # anche se il controllo viene eseguito più volte da bootstrap, cron o richieste utente.
    gs = GlobalSettings.query.filter_by(key=limit_key).first()
    if gs and (gs.value or '').strip() == today_str:
        return
        
    for threshold_days, message in thresholds.items():
        if days_until_expiry == threshold_days:
            try:
                send_push_notification(user.id, "🏥 GS Artiglio", message, '/')
            except Exception as e:
                pass
            break
    
    if days_until_expiry < 0 and user.medical_expiry:
        try:
            send_push_notification(user.id, "🏥 GS Artiglio", "🚨 Il tuo certificato medico è SCADUTO! Aggiornalo immediatamente.", '/')
        except Exception as e:
            pass

    try:
        if not gs:
            gs = GlobalSettings(key=limit_key, value=today_str)
            db.session.add(gs)
        else:
            gs.value = today_str
        db.session.commit()
    except Exception as e:
        try:
            db.session.rollback()
        except:
            pass

def check_matchday_notification():
    """Invia una notifica push a tutti se oggi c'è una partita (solo dopo le 10:00 Italia, una volta per partita)"""
    now = datetime.now()
    
    # Non inviare prima delle 10:00
    if now.hour < 10:
        return
    
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Cerca partite di oggi
    today_matches = Event.query.filter(
        Event.date_start >= today_start,
        Event.date_start <= today_end
    ).all()
    
    for match in today_matches:
        # Controlla se abbiamo già inviato la notifica matchday per questa partita
        notifica_key = f"matchday_{match.id}"
        existing = Notification.query.filter(
            Notification.tipo == 'matchday',
            Notification.messaggio.contains(f"vs {match.opponent_name}")
        ).filter(
            func.date(Notification.data_creazione) == now.date()
        ).first()
        
        if existing:
            continue  # Già inviata
        
        ora_partita = match.date_start.strftime('%H:%M')
        luogo = "Casa" if match.is_home else "Trasferta"
        location_text = f" - {match.location}" if match.location else ""
        
        messaggio = f"🏐 MATCHDAY! Oggi alle {ora_partita} vs {match.opponent_name} ({luogo}{location_text})"
        
        crea_notifica(
            'matchday',
            messaggio,
            icon='🏐',
            send_push=True
        )
        current_app.logger.info('Notifica matchday inviata per partita vs %s', match.opponent_name)

def update_all_streaks():
    """Aggiorna lo streak di tutti gli utenti basandosi sulle multe ricevute oggi"""
    from datetime import date
    today = date.today()

    users = User.query.filter(User.ruolo_volley.notin_(['Allenatore', 'Dirigente'])).all()

    for user in users:
        # Controlla se ha ricevuto multe oggi (solo approvate, non in attesa)
        multa_oggi = Fine.query.filter(
            Fine.user_id == user.id,
            db.func.date(Fine.date) == today,
            (Fine.pending_approval == False) | (Fine.pending_approval == None)
        ).first()

        if multa_oggi:
            # Ha ricevuto una multa oggi: reset streak
            user.current_streak = 0
        else:
            # Nessuna multa oggi
            if user.last_streak_update is None:
                # Prima volta: inizia streak
                user.current_streak = 1
            elif user.last_streak_update == today:
                # Già aggiornato oggi, non fare nulla
                continue
            elif user.last_streak_update == today - timedelta(days=1):
                # Giorno consecutivo: incrementa streak
                user.current_streak += 1
            else:
                # Giorni saltati (es. non ha usato l'app): mantieni streak ma non incrementare
                # oppure resetta se vuoi essere più severo
                pass

        # Aggiorna last_streak_update
        user.last_streak_update = today

        # Aggiorna best streak se necessario
        if user.current_streak > user.best_streak:
            user.best_streak = user.current_streak
            # Notifica per nuovo record se significativo (escludi 7 e 14 giorni: troppo spam)
            if user.best_streak in [30, 60, 90, 100]:
                nome = get_nome_giocatore(user)
                crea_notifica(
                    'streak_record',
                    f"🔥 {nome} ha raggiunto {user.best_streak} giorni consecutivi senza multe!",
                    icon='🔥'
                )

    db.session.commit()

def maybe_update_all_streaks(now: datetime | None = None, min_hour: int = 9) -> bool:
    """Esegue update_all_streaks() solo dopo una certa ora e max 1 volta al giorno (throttle globale)."""
    now = now or datetime.now()

    try:
        if now.hour < min_hour:
            return False  # Skip silenziosamente

        today_str = now.date().isoformat()
        key = 'streaks_last_run_date'
        # Il guard giornaliero evita che lo streak venga incrementato più volte se il codice
        # parte sia da scheduler sia da richieste web nello stesso giorno.
        gs = GlobalSettings.query.filter_by(key=key).first()
        if gs and (gs.value or '').strip() == today_str:
            return False  # Skip silenziosamente (già eseguito oggi)

        current_app.logger.info('Esecuzione update_all_streaks per today=%s', today_str)
        update_all_streaks()

        if not gs:
            gs = GlobalSettings(key=key, value=today_str)
            db.session.add(gs)
        else:
            gs.value = today_str
        db.session.commit()
        return True
    except Exception as e:
        current_app.logger.exception('Errore in maybe_update_all_streaks: %s', e)
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


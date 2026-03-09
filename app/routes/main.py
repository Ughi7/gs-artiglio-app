from flask import Blueprint, render_template, redirect, url_for, request, flash, session, Response, jsonify, current_app
from flask_login import login_required, current_user
import os
import json
import urllib.parse
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, extract
import calendar

# Models
from app.models import db, User, Fine, Event, Attendance, Vote, Turno, GlobalSettings, MatchStats, ClassificaCampionato, ClassificaInfo, Notification, HiddenNotification, NotificationPreference, CashTransaction, PushSubscription, FlappyMonthlyScore, FlappyGameProfile, Training, AppRelease, UserSeenRelease, UserFeedback, FineVote, Achievement, UserAchievement

# Setup Blueprint
main_bp = Blueprint('main', __name__)

# Import helper functions
from app.utils.badge_service import process_previous_month_badges
from app.utils.fine_service import calculate_vote_quorum, check_and_apply_late_fees, check_and_close_expired_votes, cleanup_old_rejected_votes, get_eligible_voters_count
from app.utils.helpers import allowed_file, generate_temporary_password, get_roles_from_form
from app.utils.main_services import ValidationError, get_user_profile_summary, normalize_payment_method, parse_fine_update_form, parse_new_fine_form
from app.utils.notifications import crea_notifica, get_nome_giocatore, send_push_notification, send_push_to_all
from app.utils.cron_helpers import check_medical_certificate_expiry, get_mvp_deadline, check_matchday_notification, maybe_update_all_streaks

# Da app.py
from werkzeug.utils import secure_filename
from app import bcrypt

@main_bp.route('/elimina_notifica/<int:notifica_id>', methods=['POST'])
@login_required
def elimina_notifica(notifica_id):
    # Nasconde la notifica solo per l'utente corrente
    notifica = Notification.query.get(notifica_id)
    if notifica:
        # Verifica se già nascosta per questo utente
        existing = HiddenNotification.query.filter_by(
            user_id=current_user.id,
            notification_id=notifica_id
        ).first()
        if not existing:
            hidden = HiddenNotification(user_id=current_user.id, notification_id=notifica_id)
            db.session.add(hidden)
            db.session.commit()

    return redirect(url_for('main.home'))

@main_bp.route('/elimina_tutte_notifiche', methods=['POST'])
@login_required
def elimina_tutte_notifiche():
    # Nasconde tutte le notifiche solo per l'utente corrente
    una_settimana_fa = datetime.now() - timedelta(days=7)
    notifiche = Notification.query.filter(
        Notification.data_creazione >= una_settimana_fa
    ).all()

    for notifica in notifiche:
        existing = HiddenNotification.query.filter_by(
            user_id=current_user.id,
            notification_id=notifica.id
        ).first()
        if not existing:
            hidden = HiddenNotification(user_id=current_user.id, notification_id=notifica.id)
            db.session.add(hidden)

    db.session.commit()
    flash('Bacheca svuotata.', 'success')

    return redirect(url_for('main.home'))

@main_bp.route('/salva_filtro_notifiche', methods=['POST'])
@login_required
def salva_filtro_notifiche():
    # Recupera o crea preferenze
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id, push_enabled=True)  # FIX: Esplicito push_enabled=True
        db.session.add(prefs)
    
    # Aggiorna preferenze dai campi form
    prefs.show_mvp = request.form.get('show_mvp') == 'on'
    prefs.show_streak = request.form.get('show_streak') == 'on'
    prefs.show_turno = request.form.get('show_turno') == 'on'
    prefs.show_denuncia = request.form.get('show_denuncia') == 'on'
    prefs.show_flappy = request.form.get('show_flappy') == 'on'
    prefs.show_donatore = request.form.get('show_donatore') == 'on'
    prefs.show_certificato = request.form.get('show_certificato') == 'on'
    prefs.show_aggiornamento = request.form.get('show_aggiornamento') == 'on'
    
    # Push enabled è gestito separatamente via JS, ma possiamo salvarlo anche qui se presente nel form
    # (in questo caso il form è solo per i filtri bacheca, ma mettiamo il supporto per completezza)
    if 'push_enabled' in request.form:
        prefs.push_enabled = request.form.get('push_enabled') == 'on'
        
    db.session.commit()
    flash('Preferenze notifiche aggiornate.', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/')
@login_required 
def home():
    now = datetime.now()

    # Aggiorna streak per tutti gli utenti (safe: dopo le 09:00 e max 1/giorno)
    maybe_update_all_streaks(now=now)

    # Controllo scadenza certificato medico dell'utente corrente
    check_medical_certificate_expiry(current_user)

    # Controlla se oggi è matchday e invia notifica (dopo le 10:00, una sola volta)
    check_matchday_notification()

    next_match = Event.query.filter(Event.date_start > now).order_by(Event.date_start.asc()).first()
    
    # Recupera ultima partita giocata (nel passato con risultato)
    last_match = Event.query.filter(
        Event.date_start < now,
        Event.sets_us + Event.sets_them > 0  # Ha un risultato
    ).order_by(Event.date_start.desc()).first()
    
    # Recupera Classifica (Impostazioni Globali)
    rank_obj = GlobalSettings.query.filter_by(key='rank').first()
    points_obj = GlobalSettings.query.filter_by(key='points').first()
    rank = rank_obj.value if rank_obj else "-"
    points = points_obj.value if points_obj else "-"

    # Recupera multe non pagate dell'utente corrente
    unpaid_fines = Fine.query.filter(
        Fine.user_id == current_user.id,
        Fine.paid == False,
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).order_by(Fine.deadline.asc()).all()

    # MVP Logic
    mvp_voting_open = False
    mvp_revealed = False
    user_voted = False
    mvp_winners = []
    players = []

    if last_match and not last_match.is_friendly:
        # MVP Logic solo per partite non amichevoli
        deadline = get_mvp_deadline(last_match.date_start)

        if now >= deadline:
            mvp_revealed = True
            # Calcola MVP dai voti
            votes = Vote.query.filter_by(event_id=last_match.id).all()
            if votes:
                from collections import Counter
                vote_counts = Counter([v.voted_user_id for v in votes])
                max_votes = max(vote_counts.values())
                winner_ids = [uid for uid, count in vote_counts.items() if count == max_votes]
                mvp_winners = User.query.filter(User.id.in_(winner_ids)).all()

                # Crea notifica MVP se non esiste già per questa partita
                mvp_notifica_key = f"mvp_{last_match.id}"
                existing_mvp_notifica = Notification.query.filter(
                    Notification.tipo == 'mvp',
                    Notification.messaggio.contains(f"vs {last_match.opponent_name}")
                ).first()

                if not existing_mvp_notifica and mvp_winners:
                    nomi_mvp = ", ".join([get_nome_giocatore(w) for w in mvp_winners])
                    crea_notifica(
                        'mvp',
                        f"👑 MVP della partita vs {last_match.opponent_name}: {nomi_mvp}!",
                        icon='👑'
                    )
        else:
            mvp_voting_open = True
            players = User.query.order_by(User.nome_completo).all()
            if Vote.query.filter_by(user_id=current_user.id, event_id=last_match.id).first():
                user_voted = True

    # Recupera Turni Pizza/Birra imminenti (da oggi a +7 giorni)
    today = date.today()
    limit_date = today + timedelta(days=7)
    upcoming_shifts = []
    for turno in current_user.turni:
        if not turno.is_cancelled and today <= turno.date <= limit_date:
            upcoming_shifts.append(turno)
    upcoming_shifts.sort(key=lambda x: x.date)

    # Recupera tutti i giocatori per il form tabellino
    players = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()

    # Recupera classifica campionato
    classifica = ClassificaCampionato.query.order_by(ClassificaCampionato.posizione.asc()).all()
    classifica_info = ClassificaInfo.query.first()

    # Recupera notifiche bacheca (ultime 7 giorni, escluse quelle nascoste dall'utente)
    una_settimana_fa = now - timedelta(days=7)

    # Ottieni gli ID delle notifiche nascoste per questo utente
    hidden_ids = [h.notification_id for h in HiddenNotification.query.filter_by(user_id=current_user.id).all()]

    # Ottieni preferenze filtro notifiche dell'utente
    notif_prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()

    notifiche_raw = Notification.query.filter(
        Notification.data_creazione >= una_settimana_fa,
        ~Notification.id.in_(hidden_ids) if hidden_ids else True
    ).order_by(Notification.data_creazione.desc()).limit(10).all()

    # Applica filtri per tipo se l'utente ha preferenze salvate
    if notif_prefs:
        notifiche = []
        for n in notifiche_raw:
            tipo = n.tipo.lower() if n.tipo else ''
            if tipo == 'mvp' and not notif_prefs.show_mvp:
                continue
            elif 'streak' in tipo and not notif_prefs.show_streak:
                continue
            elif 'turno' in tipo and not notif_prefs.show_turno:
                continue
            elif 'denuncia' in tipo and not notif_prefs.show_denuncia:
                continue
            elif ('flappy' in tipo or 'floppy' in tipo) and not notif_prefs.show_flappy:
                continue
            elif 'donator' in tipo and not notif_prefs.show_donatore:
                continue
            elif ('certificato' in tipo or 'medical' in tipo) and not notif_prefs.show_certificato:
                continue
            elif 'aggiornamento' in tipo and not notif_prefs.show_aggiornamento:
                continue
            notifiche.append(n)
    else:
        notifiche = notifiche_raw

    # Controlla se c'è un aggiornamento non visto dall'utente
    unseen_release = None
    latest_release = AppRelease.query.order_by(AppRelease.release_date.desc()).first()
    if latest_release:
        already_seen = UserSeenRelease.query.filter_by(
            user_id=current_user.id, 
            release_id=latest_release.id
        ).first()
        if not already_seen:
            unseen_release = latest_release

    # Restituisce tutto al template
    return render_template('index.html', 
                           next_match=next_match,
                           last_match=last_match,
                           rank=rank,
                           points=points,
                           unpaid_fines=unpaid_fines,
                           turni_imminenti=upcoming_shifts,
                           mvp_voting_open=mvp_voting_open,
                           mvp_revealed=mvp_revealed,
                           user_voted=user_voted,
                           mvp_winners=mvp_winners,
                           players=players,
                           classifica=classifica,
                           classifica_info=classifica_info,
                           notifiche=notifiche,
                           notif_prefs=notif_prefs,
                           unseen_release=unseen_release)

def calcola_streak_completate(user):
    """Calcola quante volte l'utente ha completato streak settimanali (7+ giorni) e mensili (30+ giorni)"""
    # Filtra multe solo dal 1° gennaio 2026
    anno_corrente = datetime.now().year
    inizio_anno = datetime(anno_corrente, 1, 1)
    multe = Fine.query.filter(
        Fine.user_id == user.id,
        Fine.date >= inizio_anno
    ).order_by(Fine.date.asc()).all()
    
    if not multe:
        # Nessuna multa dal 1° gennaio 2026
        giorni_totali = (datetime.now() - inizio_anno).days
        
        # Calcola quante streak complete
        streak_settimanali = giorni_totali // 7
        streak_mensili = giorni_totali // 30
        
        return {
            'settimanali': streak_settimanali,
            'mensili': streak_mensili
        }
    
    # Conta quante volte ha raggiunto 7 e 30 giorni consecutivi senza multe
    streak_settimanali = 0
    streak_mensili = 0
    
    # Periodo prima della prima multa (dal 1° gennaio 2026)
    prima_multa = multe[0].date
    giorni_prima = (prima_multa - inizio_anno).days
    streak_settimanali += giorni_prima // 7
    streak_mensili += giorni_prima // 30
    
    # Gap tra multe consecutive
    for i in range(len(multe) - 1):
        giorni_gap = (multe[i+1].date - multe[i].date).days
        streak_settimanali += giorni_gap // 7
        streak_mensili += giorni_gap // 30
    
    # Periodo dopo l'ultima multa fino a oggi
    ultima_multa = multe[-1].date
    giorni_dopo = (datetime.now() - ultima_multa).days
    streak_settimanali += giorni_dopo // 7
    streak_mensili += giorni_dopo // 30
    
    return {
        'settimanali': streak_settimanali,
        'mensili': streak_mensili
    }

@main_bp.route('/profilo')
@login_required
def profilo():
    profile_summary = get_user_profile_summary(current_user)

    # Calcola streak completate
    streak_completate = calcola_streak_completate(current_user)

    return render_template('profilo.html',
                           user=current_user,
                           mvp_count=profile_summary['mvp_count'],
                           total_points=profile_summary['total_points'],
                           total_aces=profile_summary['total_aces'],
                           total_blocks=profile_summary['total_blocks'],
                           total_multe_count=profile_summary['total_multe_count'],
                           denunce_fatte=profile_summary['denunce_fatte'],
                           denunce_prese=profile_summary['denunce_prese'],
                           viewing_other=False,
                           achievements_list=profile_summary['achievements_list'],
                           streak_completate=streak_completate)

@main_bp.route('/profilo/<int:user_id>')
@login_required
def profilo_giocatore(user_id):
    user = User.query.get_or_404(user_id)
    profile_summary = get_user_profile_summary(user)

    # Calcola streak completate
    streak_completate = calcola_streak_completate(user)

    return render_template('profilo.html',
                           user=user,
                           mvp_count=profile_summary['mvp_count'],
                           total_points=profile_summary['total_points'],
                           total_aces=profile_summary['total_aces'],
                           total_blocks=profile_summary['total_blocks'],
                           total_multe_count=profile_summary['total_multe_count'],
                           denunce_fatte=profile_summary['denunce_fatte'],
                           denunce_prese=profile_summary['denunce_prese'],
                           viewing_other=True,
                           achievements_list=profile_summary['achievements_list'],
                           streak_completate=streak_completate)

@main_bp.route('/salva_bio', methods=['POST'])
@login_required
def salva_bio():
    bio = request.form.get('bio', '').strip()
    current_user.bio = bio if bio else None
    db.session.commit()
    flash('Bio aggiornata!', 'success')
    return redirect(url_for('main.profilo'))

@main_bp.route('/upload_certificato', methods=['POST'])
@login_required
def upload_certificato():
    """Gestisce l'upload del certificato medico e la data di scadenza"""
    try:
        # Controlla se è presente il file
        if 'certificato_file' not in request.files:
            flash('Nessun file selezionato', 'danger')
            return redirect(url_for('main.profilo'))
        
        file = request.files['certificato_file']
        data_scadenza_str = request.form.get('data_scadenza')
        
        # Se l'utente ha solo aggiornato la data senza file
        if file.filename == '' and data_scadenza_str:
            # Aggiorna solo la data
            try:
                data_scadenza = datetime.strptime(data_scadenza_str, '%Y-%m-%d').date()
                current_user.medical_expiry = data_scadenza
                db.session.commit()
                flash('✅ Data di scadenza aggiornata con successo!', 'success')
                return redirect(url_for('main.profilo'))
            except ValueError:
                flash('Formato data non valido', 'danger')
                return redirect(url_for('main.profilo'))
        
        # Se c'è un file, deve esserci anche la data
        if file.filename == '':
            flash('Seleziona un file da caricare', 'warning')
            return redirect(url_for('main.profilo'))
        
        if not data_scadenza_str:
            flash('Inserisci la data di scadenza', 'warning')
            return redirect(url_for('main.profilo'))
        
        # Verifica estensione file
        if not allowed_file(file.filename):
            flash('❌ Formato file non consentito. Usa: PDF, JPG, JPEG, PNG', 'danger')
            return redirect(url_for('main.profilo'))
        
        # Prepara il nome del file
        username_clean = current_user.username.replace(' ', '_').lower()
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"cert_{current_user.id}_{username_clean}.{file_ext}"
        
        # Elimina vecchio certificato se esiste
        if current_user.medical_file:
            old_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.medical_file)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as e:
                    print(f"Errore eliminazione vecchio certificato: {e}")
        
        # Salva il nuovo file
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Aggiorna database
        try:
            data_scadenza = datetime.strptime(data_scadenza_str, '%Y-%m-%d').date()
            current_user.medical_file = filename
            current_user.medical_expiry = data_scadenza
            db.session.commit()
            
            flash('✅ Certificato medico caricato con successo!', 'success')
        except ValueError:
            flash('Formato data non valido', 'danger')
            # Elimina file appena caricato in caso di errore
            if os.path.exists(filepath):
                os.remove(filepath)
        
    except Exception as e:
        flash(f'❌ Errore durante il caricamento: {str(e)}', 'danger')
        print(f"Errore upload certificato: {e}")
    
    return redirect(url_for('main.profilo'))

@main_bp.route('/admin/assegna-badge-mensili', methods=['GET', 'POST'])
@login_required
def admin_assegna_badge_mensili():
    if not current_user.is_admin:
        flash('Accesso negato. Solo gli admin possono accedere a questa sezione.', 'danger')
        return redirect(url_for('main.home'))
    
    risultati = []
    mese_assegnato = None
    anno_assegnato = None
    
    if request.method == 'POST':
        try:
            risultati, mese_assegnato, anno_assegnato = process_previous_month_badges()
            flash(f'Badge mensili processati per {mese_assegnato}/{anno_assegnato}!', 'success')
            
        except Exception as e:
            flash(f'Errore durante l\'assegnazione: {str(e)}', 'danger')
    
    return render_template('admin_badge.html', risultati=risultati, mese=mese_assegnato, anno=anno_assegnato)

@main_bp.route('/denuncia_infrazione', methods=['POST'])
@login_required
def denuncia_infrazione():
    user_id = int(request.form.get('user_id'))
    data_infrazione_str = request.form.get('data_infrazione')
    motivazione = request.form.get('motivazione')
    importo = float(request.form.get('importo', 2))
    note = request.form.get('note', '').strip()  # Note facoltative

    # Controlla limite di 3 denunce al giorno
    oggi_inizio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    oggi_fine = oggi_inizio + timedelta(days=1)
    denunce_oggi = Fine.query.filter(
        Fine.denunciante_id == current_user.id,
        Fine.date >= oggi_inizio,
        Fine.date < oggi_fine
    ).count()

    if denunce_oggi >= 3:
        flash('Hai raggiunto il limite massimo di 3 denunce per oggi!', 'danger')
        return redirect(url_for('main.rosa'))

    # Converti data
    data_infrazione = datetime.strptime(data_infrazione_str, '%Y-%m-%d')

    # Calcola scadenza (3 settimane dalla data infrazione)
    deadline = data_infrazione + timedelta(weeks=3)

    # Crea la multa come "da approvare"
    f = Fine(
        user_id=user_id,
        amount=importo,
        reason=motivazione,
        date=data_infrazione,
        deadline=deadline,
        pending_approval=True,  # Da approvare
        denunciante_id=current_user.id,  # Chi ha denunciato
        note=note if note else None  # Note facoltative
    )
    db.session.add(f)
    db.session.commit()

    # Crea notifica per la denuncia
    denunciato = User.query.get(user_id)
    denunciante_nome = get_nome_giocatore(current_user)
    denunciato_nome = get_nome_giocatore(denunciato)

    # Costruisci messaggio notifica con note se presenti
    msg = f"⚖️ {denunciante_nome} ha denunciato {denunciato_nome}. Motivazione: {motivazione}"
    if note:
        msg += f" | Note: {note}"
    msg += " (in attesa di approvazione)"

    crea_notifica('denuncia', msg, icon='⚖️')

    flash(f'Denuncia inviata per {denunciato_nome}! In attesa di approvazione.', 'warning')
    return redirect(url_for('main.rosa'))

@main_bp.route('/update_rank', methods=['POST'])
@login_required
def update_rank():
    if not current_user.is_admin: return redirect(url_for('main.home'))
    
    new_rank = request.form.get('rank')
    new_points = request.form.get('points')
    
    # Salva o Aggiorna Rank
    r = GlobalSettings.query.filter_by(key='rank').first()
    if not r: r = GlobalSettings(key='rank')
    r.value = new_rank
    db.session.add(r)
    
    # Salva o Aggiorna Punti
    p = GlobalSettings.query.filter_by(key='points').first()
    if not p: p = GlobalSettings(key='points')
    p.value = new_points
    db.session.add(p)
    
    db.session.commit()
    return redirect(url_for('main.home'))

@main_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw = request.form.get('current_password')
    new_pw = request.form.get('new_password')
    confirm_pw = request.form.get('confirm_password')

    if not current_pw or not new_pw or not confirm_pw:
        flash('Compila tutti i campi', 'danger')
        return redirect(url_for('main.profilo'))

    if not bcrypt.check_password_hash(current_user.password_hash, current_pw):
        flash('Password attuale non corretta', 'danger')
        return redirect(url_for('main.profilo'))

    if new_pw != confirm_pw:
        flash('Le nuove password non coincidono', 'danger')
        return redirect(url_for('main.profilo'))

    if len(new_pw) < 6:
        flash('La password deve avere almeno 6 caratteri', 'danger')
        return redirect(url_for('main.profilo'))

    current_user.password_hash = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    flash('Password aggiornata con successo!', 'success')
    return redirect(url_for('main.profilo'))

@main_bp.route('/salva_classifica', methods=['POST'])
@login_required
def salva_classifica():
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi per modificare la classifica!', 'danger')
        return redirect(url_for('main.home'))

    # Aggiorna info giornata
    giornata_attuale = request.form.get('giornata_attuale', type=int)
    giornate_totali = request.form.get('giornate_totali', type=int)

    info = ClassificaInfo.query.first()
    if not info:
        info = ClassificaInfo()
        db.session.add(info)

    if giornata_attuale is not None:
        info.giornata_attuale = giornata_attuale
    if giornate_totali is not None:
        info.giornate_totali = giornate_totali

    # Aggiorna punti di ogni squadra
    classifica = ClassificaCampionato.query.all()
    for squadra in classifica:
        punti = request.form.get(f'punti_{squadra.id}', type=int)
        if punti is not None:
            squadra.punti = punti

    db.session.commit()

    # Riordina le posizioni in base ai punti
    squadre_ordinate = ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all()
    for i, squadra in enumerate(squadre_ordinate, 1):
        squadra.posizione = i
    db.session.commit()

    flash('Classifica aggiornata!', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/aggiungi_squadra', methods=['POST'])
@login_required
def aggiungi_squadra():
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.home'))

    nome_squadra = request.form.get('nome_squadra')
    punti = request.form.get('punti', type=int, default=0)
    is_artiglio = request.form.get('is_artiglio') == 'on'

    if not nome_squadra:
        flash('Inserisci il nome della squadra!', 'danger')
        return redirect(url_for('main.home'))

    # Conta le squadre esistenti per la posizione
    num_squadre = ClassificaCampionato.query.count()

    nuova_squadra = ClassificaCampionato(
        posizione=num_squadre + 1,
        squadra=nome_squadra,
        punti=punti,
        is_artiglio=is_artiglio
    )
    db.session.add(nuova_squadra)
    db.session.commit()

    # Riordina in base ai punti
    squadre_ordinate = ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all()
    for i, squadra in enumerate(squadre_ordinate, 1):
        squadra.posizione = i
    db.session.commit()

    flash(f'Squadra "{nome_squadra}" aggiunta!', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/rimuovi_squadra/<int:squadra_id>', methods=['POST'])
@login_required
def rimuovi_squadra(squadra_id):
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.home'))

    squadra = ClassificaCampionato.query.get(squadra_id)
    if squadra:
        db.session.delete(squadra)
        db.session.commit()

        # Riordina le posizioni
        squadre_ordinate = ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all()
        for i, s in enumerate(squadre_ordinate, 1):
            s.posizione = i
        db.session.commit()

        flash('Squadra rimossa!', 'success')

    return redirect(url_for('main.home'))

@main_bp.route('/rosa')
@login_required
def rosa():
    # Ordine ruoli: Palleggiatore, Opposto, Libero, Schiacciatore, Centrale, Jolly, Allenatore, Dirigente
    role_order = {
        'Palleggiatore': 1,
        'Opposto': 2,
        'Libero': 3,
        'Schiacciatore': 4,
        'Centrale': 5,
        'Jolly': 6,
        'Allenatore': 7,
        'Dirigente': 8
    }
    giocatori = User.query.all()
    giocatori_ordinati = sorted(giocatori, key=lambda g: role_order.get(g.ruolo_volley, 99))
    # Achievements per ogni giocatore
    achievements_dict = {}
    for g in giocatori_ordinati:
        achievements_dict[g.id] = [
            {
                'icon': ua.achievement.icon,
                'name': ua.achievement.name,
                'desc': ua.achievement.description,
                'color': ua.achievement.color if ua.achievement.color else 'bg-warning',
                'is_monthly': ua.achievement.is_monthly,
                'month': ua.month,
                'year': ua.year
            }
            for ua in g.achievements
        ]
    return render_template('rosa.html', elenco_giocatori=giocatori_ordinati, now=datetime.now(), achievements_dict=achievements_dict)

@main_bp.route('/aggiungi_giocatore', methods=['POST'])
@login_required
def aggiungi_giocatore():
    if not current_user.is_admin: return redirect(url_for('main.rosa'))
    if User.query.filter_by(username=request.form.get('username')).first():
        flash('Username esistente', 'danger')
        return redirect(url_for('main.rosa'))
    roles = get_roles_from_form(request)
    temporary_password = generate_temporary_password()
    u = User(username=request.form.get('username'), password_hash=bcrypt.generate_password_hash(temporary_password).decode('utf-8'), nome_completo=request.form.get('nome_completo'), soprannome=request.form.get('soprannome'), numero_maglia=int(request.form.get('numero_maglia') or 0), ruolo_volley=request.form.get('ruolo_volley'), **roles)
    db.session.add(u)
    db.session.commit()
    flash(f'Giocatore aggiunto. Password temporanea per {u.username}: {temporary_password}', 'success')
    return redirect(url_for('main.rosa'))

@main_bp.route('/modifica_giocatore', methods=['POST'])
@login_required
def modifica_giocatore():
    if not current_user.is_admin: return redirect(url_for('main.rosa'))
    u = User.query.get(int(request.form.get('user_id')))
    if u:
        u.nome_completo = request.form.get('nome_completo')
        u.soprannome = request.form.get('soprannome')
        u.numero_maglia = request.form.get('numero_maglia')
        u.ruolo_volley = request.form.get('ruolo_volley')
        roles = get_roles_from_form(request)
        for k, v in roles.items(): setattr(u, k, v)
        db.session.commit()
        flash('Aggiornato', 'success')
    return redirect(url_for('main.rosa'))

@main_bp.route('/upload_regolamento', methods=['POST'])
@login_required
def upload_regolamento():
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))

    if 'regolamento_file' not in request.files:
        flash('Nessun file selezionato', 'danger')
        return redirect(url_for('main.multe'))

    file = request.files['regolamento_file']
    if file.filename == '':
        flash('Nessun file selezionato', 'warning')
        return redirect(url_for('main.multe'))

    if file and file.filename.lower().endswith('.pdf'):
        filename = 'regolamento.pdf'
        file.save(os.path.join(current_app.config['FILES_UPLOAD_FOLDER'], filename))
        flash('Regolamento caricato con successo!', 'success')
    else:
        flash('Solo file PDF sono consentiti', 'danger')
        
    return redirect(url_for('main.multe'))

@main_bp.route('/multe')
@login_required
def multe():
    check_and_apply_late_fees()
    # Filtro per mese
    filter_month = request.args.get('month', 'all')
    # Filtro per persona
    filter_person = request.args.get('person', 'all')
    
    # Totale multe PAGATE (entrate effettive in cassa)
    totale_pagate = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).scalar() or 0.0
    
    # Calcola ripartizione contanti/PayPal
    totale_contanti = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        Fine.payment_method == 'contanti',
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).scalar() or 0.0
    
    totale_paypal = db.session.query(func.sum(Fine.amount)).filter(
        Fine.paid == True,
        Fine.payment_method == 'paypal',
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).scalar() or 0.0
    
    # Totale cassa: tutte le multe approvate (per visualizzazione)
    totale = db.session.query(func.sum(Fine.amount)).filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).scalar() or 0.0

    # Query base: escludi denunce in attesa di approvazione
    query = Fine.query.filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    )

    # Applica filtro mese se necessario
    if filter_month != 'all':
        try:
            year, month = map(int, filter_month.split('-'))
            # Primo e ultimo giorno del mese
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1)
            else:
                last_day = datetime(year, month + 1, 1)
            query = query.filter(Fine.date >= first_day, Fine.date < last_day)
        except:
            pass
    
    # Applica filtro persona se necessario
    if filter_person != 'all':
        try:
            person_id = int(filter_person)
            query = query.filter(Fine.user_id == person_id)
        except:
            pass
    
    registro_multe = query.order_by(Fine.paid.asc(), desc(Fine.date)).all()
    
    # Check if regulation file exists
    has_regulation = os.path.exists(os.path.join(current_app.config['FILES_UPLOAD_FOLDER'], 'regolamento.pdf'))

    # Controlla e chiudi votazioni scadute
    check_and_close_expired_votes()

    # Denunce in attesa di approvazione (visibili solo a admin/notai)
    denunce_in_attesa = Fine.query.filter(Fine.pending_approval == True).order_by(desc(Fine.date)).all()

    # Denunce in votazione attiva
    denunce_in_votazione = Fine.query.filter(Fine.voting_active == True).order_by(desc(Fine.voting_end)).all()
    
    # Dati per la votazione
    import json
    user_votes = {}  # {fine_id: True/False/None}
    vote_counts = {}  # {fine_id: {'approve': X, 'reject': Y}}
    excluded_voters_data = {}  # {fine_id: [list of excluded user ids]}
    quorum_per_vote = {}  # {fine_id: quorum_value}
    
    eligible_voters_base = get_eligible_voters_count()  # Base count (no coach/presidente)
    
    for denuncia in denunce_in_votazione:
        # Verifica se l'utente ha già votato
        user_vote = FineVote.query.filter_by(fine_id=denuncia.id, user_id=current_user.id).first()
        user_votes[denuncia.id] = user_vote.vote if user_vote else None
        
        # Conta i voti
        approve_count = FineVote.query.filter_by(fine_id=denuncia.id, vote=True).count()
        reject_count = FineVote.query.filter_by(fine_id=denuncia.id, vote=False).count()
        vote_counts[denuncia.id] = {'approve': approve_count, 'reject': reject_count}
        
        # Parse excluded voters
        try:
            excluded = json.loads(denuncia.excluded_voters or '[]')
        except:
            excluded = []
        excluded_voters_data[denuncia.id] = excluded
        
        # Calcola quorum considerando esclusi e l'accusato (che non vota)
        effective_voters = eligible_voters_base - len(excluded) - 1  # -1 per l'accusato
        quorum_per_vote[denuncia.id] = max(1, (effective_voters // 2) + 1)
    
    eligible_voters = eligible_voters_base
    quorum = max(1, ((eligible_voters - 1) // 2) + 1)  # -1 per l'accusato

    # ULTIME SANZIONI (Ultime 2 giornate con multe approvate)
    # Trova le ultime 2 date distinte (YYYY-MM-DD)
    last_dates_query = db.session.query(func.strftime('%Y-%m-%d', Fine.date)).filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).distinct().order_by(desc(func.strftime('%Y-%m-%d', Fine.date))).limit(2).all()
    last_dates = [d[0] for d in last_dates_query]

    if last_dates:
        ultime_sanzioni = Fine.query.filter(
            func.strftime('%Y-%m-%d', Fine.date).in_(last_dates),
            (Fine.pending_approval == False) | (Fine.pending_approval == None),
            (Fine.voting_active == False) | (Fine.voting_active == None)
        ).order_by(desc(Fine.date)).all()
    else:
        ultime_sanzioni = []

    # Genera lista mesi disponibili
    months_with_fines = db.session.query(
        func.strftime('%Y-%m', Fine.date).label('month')
    ).distinct().order_by(desc('month')).all()
    
    available_months = [m[0] for m in months_with_fines]

    # --- CLASSIFICHE ---

    # 1. Classifica Generale (All Time) - solo multe approvate
    classifica_generale = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).group_by(User.id).order_by(desc('total')).all()

    # 2. Classifica Mensile
    # Se è selezionato un mese specifico, usiamo quello.
    # Se è selezionato 'all', usiamo il mese corrente per default (o nascondiamo? Meglio mostrare il corrente).
    if filter_month != 'all':
        try:
            y, m = map(int, filter_month.split('-'))
            m_start = datetime(y, m, 1)
            if m == 12:
                m_end = datetime(y + 1, 1, 1)
            else:
                m_end = datetime(y, m + 1, 1)
            month_label = filter_month
        except:
            # Fallback su mese corrente
            now = datetime.now()
            m_start = datetime(now.year, now.month, 1)
            if now.month == 12:
                m_end = datetime(now.year + 1, 1, 1)
            else:
                m_end = datetime(now.year, now.month + 1, 1)
            month_label = now.strftime('%Y-%m')
    else:
        # Default: mese corrente
        now = datetime.now()
        m_start = datetime(now.year, now.month, 1)
        if now.month == 12:
            m_end = datetime(now.year + 1, 1, 1)
        else:
            m_end = datetime(now.year, now.month + 1, 1)
        month_label = now.strftime('%Y-%m')

    classifica_mensile = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        Fine.date >= m_start,
        Fine.date < m_end,
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).group_by(User.id).order_by(desc('total')).all()

    # Storico transazioni cassa
    transazioni = CashTransaction.query.order_by(desc(CashTransaction.date)).all()
    
    # Calcola totale uscite
    totale_uscite = db.session.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == 'uscita'
    ).scalar() or 0.0
    
    # Calcola totale entrate manuali (registrate nello storico cassa)
    totale_entrate_manuali = db.session.query(func.sum(CashTransaction.amount)).filter(
        CashTransaction.transaction_type == 'entrata'
    ).scalar() or 0.0

    # Saldo reale = multe PAGATE + entrate manuali - uscite
    saldo_cassa = totale_pagate + totale_entrate_manuali - totale_uscite

    # Lista utenti eleggibili per votazione (per modal impostazioni)
    votanti_eleggibili = User.query.filter(
        User.is_coach.isnot(True),
        User.is_presidente.isnot(True)
    ).order_by(User.nome_completo).all()
    
    return render_template('multe.html',
                          totale_cassa=totale,
                          totale_pagate=totale_pagate,
                          totale_contanti=totale_contanti,
                          totale_paypal=totale_paypal,
                          saldo_cassa=saldo_cassa,
                          totale_uscite=totale_uscite,
                          totale_entrate_manuali=totale_entrate_manuali,
                          transazioni=transazioni,
                          registro_multe=registro_multe,
                          ultime_sanzioni=ultime_sanzioni,
                          denunce_in_attesa=denunce_in_attesa,
                          denunce_in_votazione=denunce_in_votazione,
                          user_votes=user_votes,
                          vote_counts=vote_counts,
                          eligible_voters=eligible_voters,
                          quorum=quorum,
                          excluded_voters_data=excluded_voters_data,
                          quorum_per_vote=quorum_per_vote,
                          votanti_eleggibili=votanti_eleggibili,
                          elenco_giocatori=User.query.order_by(User.nome_completo).all(),
                          User=User,
                          now=datetime.now(),
                          has_regulation=has_regulation,
                          filter_month=filter_month,
                          filter_person=filter_person,
                          available_months=available_months,
                          classifica_generale=classifica_generale,
                          classifica_mensile=classifica_mensile,
                          month_label=month_label)

@main_bp.route('/stats_multe')
@login_required
def stats_multe():
    from collections import defaultdict
    
    # === DATI MULTE ===
    # 1. Trend multe mensili (ultimi 12 mesi)
    multe_approvate = Fine.query.filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).all()
    
    multe_per_mese = defaultdict(lambda: {'count': 0, 'total': 0})
    for multa in multe_approvate:
        mese_key = multa.date.strftime('%Y-%m')
        multe_per_mese[mese_key]['count'] += 1
        multe_per_mese[mese_key]['total'] += multa.amount
    
    # Ordina per mese (ultimi 12)
    mesi_sorted = sorted(multe_per_mese.keys(), reverse=True)[:12]
    mesi_sorted.reverse()  # Dal più vecchio al più recente
    
    # 2. Multe per giocatore
    multe_per_giocatore = db.session.query(
        User.soprannome, User.nome_completo, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(
        (Fine.pending_approval == False) | (Fine.pending_approval == None)
    ).group_by(User.id).order_by(desc('total')).all()
    
    # 3. Top 5 denunciatori
    denunciatori = db.session.query(
        User.soprannome, User.nome_completo, func.count(Fine.id).label('count')
    ).join(Fine, Fine.denunciante_id == User.id).filter(
        Fine.denunciante_id != None
    ).group_by(User.id).order_by(desc('count')).limit(5).all()
    
    # 4. Distribuzione multe per range di importo (tipologia)
    multa_ranges = {
        '€0-5': 0,
        '€5-10': 0,
        '€10-20': 0,
        '€20+': 0
    }
    for multa in multe_approvate:
        if multa.amount < 5:
            multa_ranges['€0-5'] += 1
        elif multa.amount < 10:
            multa_ranges['€5-10'] += 1
        elif multa.amount < 20:
            multa_ranges['€10-20'] += 1
        else:
            multa_ranges['€20+'] += 1
    
    return render_template('stats_multe.html',
                          mesi_multe=mesi_sorted,
                          multe_count_per_mese=[multe_per_mese[m]['count'] for m in mesi_sorted],
                          multe_importo_per_mese=[multe_per_mese[m]['total'] for m in mesi_sorted],
                          multe_per_giocatore=multe_per_giocatore,
                          denunciatori=denunciatori,
                          multa_ranges=multa_ranges)

@main_bp.route('/stats_partite')
@login_required
def stats_partite():
    from collections import defaultdict
    
    # === DATI PARTITE === (escludi amichevoli)
    partite = Event.query.filter(
        Event.sets_us + Event.sets_them > 0,
        Event.is_friendly == False
    ).order_by(Event.date_start).all()
    
    # 1. Andamento vittorie/sconfitte nel tempo
    vittorie_tempo = []
    sconfitte_tempo = []
    date_partite = []
    for partita in partite:
        date_partite.append(partita.date_start.strftime('%d/%m/%y'))
        if partita.sets_us > partita.sets_them:
            vittorie_tempo.append(1)
            sconfitte_tempo.append(0)
        else:
            vittorie_tempo.append(0)
            sconfitte_tempo.append(1)
    
    # 2. Set vinti/persi per mese
    set_per_mese = defaultdict(lambda: {'vinti': 0, 'persi': 0})
    for partita in partite:
        mese_key = partita.date_start.strftime('%Y-%m')
        set_per_mese[mese_key]['vinti'] += partita.sets_us
        set_per_mese[mese_key]['persi'] += partita.sets_them
    
    mesi_partite_sorted = sorted(set_per_mese.keys())
    
    # 3. % vittorie/sconfitte totali
    vittorie_totali = sum(1 for p in partite if p.sets_us > p.sets_them)
    sconfitte_totali = len(partite) - vittorie_totali
    
    return render_template('stats_partite.html',
                          date_partite=date_partite,
                          vittorie_tempo=vittorie_tempo,
                          sconfitte_tempo=sconfitte_tempo,
                          mesi_partite=mesi_partite_sorted,
                          set_vinti_per_mese=[set_per_mese[m]['vinti'] for m in mesi_partite_sorted],
                          set_persi_per_mese=[set_per_mese[m]['persi'] for m in mesi_partite_sorted],
                          vittorie_totali=vittorie_totali,
                          sconfitte_totali=sconfitte_totali)

@main_bp.route('/aggiungi_transazione', methods=['POST'])
@login_required
def aggiungi_transazione():
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))

    amount = float(request.form.get('amount'))
    description = request.form.get('description')
    transaction_type = request.form.get('transaction_type', 'uscita')

    date_str = request.form.get('date')
    if date_str:
        trans_date = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        trans_date = datetime.now()

    t = CashTransaction(
        amount=amount,
        description=description,
        date=trans_date,
        transaction_type=transaction_type,
        created_by_id=current_user.id
    )
    db.session.add(t)
    db.session.commit()

    flash(f'{"Uscita" if transaction_type == "uscita" else "Entrata"} registrata: €{amount:.2f}', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/elimina_transazione/<int:trans_id>', methods=['POST'])
@login_required
def elimina_transazione(trans_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))

    t = CashTransaction.query.get(trans_id)
    if t:
        db.session.delete(t)
        db.session.commit()
        flash('Transazione eliminata.', 'success')

    return redirect(url_for('main.multe'))

@main_bp.route('/aggiungi_multa', methods=['POST'])
@login_required
def aggiungi_multa():
    if not (current_user.is_admin or current_user.is_notaio): return redirect(url_for('main.multe'))

    try:
        fine_data = parse_new_fine_form(request.form)
    except ValidationError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('main.multe'))

    multato = fine_data['user']
    f = Fine(
        user_id=multato.id,
        amount=fine_data['amount'],
        reason=fine_data['reason'],
        date=fine_data['date'],
        deadline=fine_data['deadline']
    )
    db.session.add(f)

    # Reset streak del multato
    if multato:
        multato.current_streak = 0

    db.session.commit()

    # Crea notifica per la multa
    multato_nome = get_nome_giocatore(multato)
    crea_notifica(
        'multa',
        f"💸 {multato_nome} è stato multato. Motivazione: {fine_data['reason']}",
        icon='💸'
    )

    flash('Multa assegnata', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/modifica_multa', methods=['POST'])
@login_required
def modifica_multa():
    if not (current_user.is_admin or current_user.is_notaio): return redirect(url_for('main.multe'))

    try:
        fine_data = parse_fine_update_form(request.form)
    except ValidationError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('main.multe'))

    f = db.session.get(Fine, fine_data['fine_id'])
    if f:
        f.amount = fine_data['amount']
        f.reason = fine_data['reason']
        f.paid = fine_data['paid']
        f.payment_method = fine_data['payment_method']

        db.session.commit()
        flash('Multa aggiornata.', 'success')
    else:
        flash('Multa non trovata.', 'danger')
    return redirect(url_for('main.multe'))

@main_bp.route('/paga_multa/<int:fine_id>', methods=['POST'])
@login_required
def paga_multa(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non autorizzato', 'danger')
        return redirect(url_for('main.multe'))

    fine = Fine.query.get_or_404(fine_id)

    try:
        metodo = normalize_payment_method(request.form.get('metodo'), required=True)
    except ValidationError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('main.multe'))

    fine.paid = True
    fine.payment_method = metodo # Salva il metodo
    db.session.commit()

    # Verifica se il giocatore è entrato nella top 3 donatori
    giocatore = db.session.get(User, fine.user_id)
    giocatore_nome = get_nome_giocatore(giocatore)

    # Classifica generale
    classifica_generale = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(Fine.paid == True).group_by(User.id).order_by(desc('total')).all()

    for i, (user, total) in enumerate(classifica_generale[:3]):
        if user.id == fine.user_id:
            posizione_str = {0: '🥇 PRIMO', 1: '🥈 SECONDO', 2: '🥉 TERZO'}[i]
            # Controlla se esiste già una notifica recente per questo
            existing = Notification.query.filter(
                Notification.tipo == 'donatore_top3',
                Notification.messaggio.contains(giocatore_nome),
                Notification.messaggio.contains('classifica generale')
            ).first()
            if not existing:
                crea_notifica(
                    'donatore_top3',
                    f"💰 {giocatore_nome} è {posizione_str} nella classifica generale donatori con €{total:.2f}!",
                    icon='💰'
                )
            break

    # Classifica mensile (mese corrente)
    now = datetime.now()
    m_start = datetime(now.year, now.month, 1)
    if now.month == 12:
        m_end = datetime(now.year + 1, 1, 1)
    else:
        m_end = datetime(now.year, now.month + 1, 1)

    classifica_mensile = db.session.query(
        User, func.sum(Fine.amount).label('total')
    ).join(Fine, Fine.user_id == User.id).filter(Fine.paid == True, Fine.date >= m_start, Fine.date < m_end).group_by(User.id).order_by(desc('total')).all()

    for i, (user, total) in enumerate(classifica_mensile[:3]):
        if user.id == fine.user_id:
            posizione_str = {0: '🥇 PRIMO', 1: '🥈 SECONDO', 2: '🥉 TERZO'}[i]
            mese_nome = now.strftime('%B %Y')
            # Controlla se esiste già una notifica recente per questo mese
            existing = Notification.query.filter(
                Notification.tipo == 'donatore_top3',
                Notification.messaggio.contains(giocatore_nome),
                Notification.messaggio.contains(mese_nome)
            ).first()
            if not existing:
                crea_notifica(
                    'donatore_top3',
                    f"💰 {giocatore_nome} è {posizione_str} nella classifica donatori di {mese_nome} con €{total:.2f}!",
                    icon='💰'
                )
            break

    flash(f'Multa segnata come pagata ({metodo})', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/elimina_multa/<int:fine_id>')
@login_required
def elimina_multa(fine_id):
    if not (current_user.is_admin or current_user.is_notaio): return redirect(url_for('main.multe'))
    f = Fine.query.get(fine_id)
    if f: 
        db.session.delete(f)
        db.session.commit()
    return redirect(url_for('main.multe'))

@main_bp.route('/approva_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def approva_denuncia(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))

    f = Fine.query.get(fine_id)
    if f and f.pending_approval:
        f.pending_approval = False

        # Reset streak del multato
        multato = User.query.get(f.user_id)
        if multato:
            multato.current_streak = 0

        db.session.commit()

        # Crea notifica per approvazione
        multato_nome = get_nome_giocatore(multato)
        crea_notifica(
            'denuncia_approvata',
            f"✅ La denuncia contro {multato_nome} è stata approvata. Motivazione: {f.reason}",
            icon='✅'
        )

        flash('Denuncia approvata!', 'success')

    return redirect(url_for('main.multe'))

@main_bp.route('/rifiuta_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def rifiuta_denuncia(fine_id):
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))

    f = Fine.query.get(fine_id)
    if f and f.pending_approval:
        multato = User.query.get(f.user_id)
        multato_nome = get_nome_giocatore(multato)
        reason = f.reason

        db.session.delete(f)
        db.session.commit()

        # Crea notifica per rifiuto
        crea_notifica(
            'denuncia_rifiutata',
            f"❌ La denuncia contro {multato_nome} è stata rifiutata. Motivazione originale: {reason}",
            icon='❌'
        )

        flash('Denuncia rifiutata e rimossa.', 'info')

    return redirect(url_for('main.multe'))

@main_bp.route('/ritira_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def ritira_denuncia(fine_id):
    f = Fine.query.get(fine_id)

    # Verifica che la denuncia esista, sia in attesa e sia stata fatta dall'utente corrente
    if not f or not f.pending_approval or f.denunciante_id != current_user.id:
        flash('Non puoi ritirare questa denuncia.', 'danger')
        return redirect(url_for('main.multe'))

    multato = User.query.get(f.user_id)
    multato_nome = get_nome_giocatore(multato)
    denunciante_nome = get_nome_giocatore(current_user)
    reason = f.reason

    # Prendi il motivo del ritiro dal form
    motivo_ritiro = request.form.get('note_ritiro', '').strip()

    db.session.delete(f)
    db.session.commit()

    # Crea notifica per ritiro con motivo se presente
    msg = f"🔙 {denunciante_nome} ha ritirato la denuncia contro {multato_nome}. Motivazione originale: {reason}"
    if motivo_ritiro:
        msg += f" | Motivo del ritiro: {motivo_ritiro}"

    crea_notifica('denuncia_ritirata', msg, icon='🔙')

    flash('Denuncia ritirata con successo.', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/avvia_votazione/<int:fine_id>', methods=['POST'])
@login_required
def avvia_votazione(fine_id):
    """Avvia una votazione pubblica su una denuncia (solo admin/notaio)"""
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))
    
    f = Fine.query.get(fine_id)
    if not f or not f.pending_approval:
        flash('Denuncia non trovata o già elaborata.', 'warning')
        return redirect(url_for('main.multe'))
    
    # Imposta la votazione
    now = datetime.now()
    f.voting_active = True
    f.voting_start = now
    f.voting_end = now + timedelta(hours=24)
    f.pending_approval = False  # Non più in attesa, ora in votazione
    
    db.session.commit()
    
    # Notifica
    multato = User.query.get(f.user_id)
    multato_nome = get_nome_giocatore(multato)
    # [TEST MODE] Notifica disabilitata
    crea_notifica(
        'denuncia_votazione',
        f"🗳️ Votazione aperta: multa a {multato_nome} per '{f.reason}'. Vota entro 24h!",
        icon='🗳️'
    )
    
    flash(f'Votazione avviata! Scadrà tra 24 ore.', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/vota_denuncia/<int:fine_id>', methods=['POST'])
@login_required
def vota_denuncia(fine_id):
    """Vota su una denuncia in corso (permette anche cambio voto)"""
    import json
    
    # Verifica che l'utente possa votare (non coach e non presidente)
    if current_user.is_coach or current_user.is_presidente:
        flash('Non puoi votare sulle multe.', 'warning')
        return redirect(url_for('main.multe'))
    
    f = Fine.query.get(fine_id)
    if not f or not f.voting_active:
        flash('Votazione non attiva.', 'warning')
        return redirect(url_for('main.multe'))
    
    # Verifica se l'utente è escluso dalla votazione
    try:
        excluded = json.loads(f.excluded_voters or '[]')
    except:
        excluded = []
    
    if current_user.id in excluded:
        flash('Sei stato escluso da questa votazione.', 'warning')
        return redirect(url_for('main.multe'))
    
    # L'accusato non può votare sulla propria multa
    if current_user.id == f.user_id:
        flash('Non puoi votare sulla tua stessa multa.', 'warning')
        return redirect(url_for('main.multe'))
    
    # Registra o aggiorna il voto
    vote_value = request.form.get('vote') == '1'  # '1' = approva, '0' = rifiuta
    existing_vote = FineVote.query.filter_by(fine_id=fine_id, user_id=current_user.id).first()
    
    if existing_vote:
        # Modifica voto esistente
        if existing_vote.vote != vote_value:
            existing_vote.vote = vote_value
            existing_vote.voted_at = datetime.now()
            db.session.commit()
            flash('Voto modificato!', 'success')
        else:
            flash('Hai già votato così.', 'info')
    else:
        # Nuovo voto
        new_vote = FineVote(
            fine_id=fine_id,
            user_id=current_user.id,
            vote=vote_value
        )
        db.session.add(new_vote)
        db.session.commit()
        flash('Voto registrato!', 'success')
    
    return redirect(url_for('main.multe'))

@main_bp.route('/modifica_impostazioni_votazione/<int:fine_id>', methods=['POST'])
@login_required
def modifica_impostazioni_votazione(fine_id):
    """Modifica impostazioni votazione: escludi/includi utenti (solo admin/notaio)"""
    import json
    
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))
    
    f = Fine.query.get(fine_id)
    if not f or not f.voting_active:
        flash('Votazione non trovata o non attiva.', 'warning')
        return redirect(url_for('main.multe'))
    
    # Recupera lista utenti esclusi dal form
    excluded_ids = request.form.getlist('excluded_users')
    excluded_ids = [int(uid) for uid in excluded_ids if uid.isdigit()]
    
    # Salva come JSON
    f.excluded_voters = json.dumps(excluded_ids)
    db.session.commit()
    
    flash(f'Impostazioni votazione aggiornate! {len(excluded_ids)} utenti esclusi.', 'success')
    return redirect(url_for('main.multe'))

@main_bp.route('/elimina_votazione/<int:fine_id>', methods=['POST'])
@login_required
def elimina_votazione(fine_id):
    """Elimina/annulla una votazione in corso (solo admin/notaio)"""
    if not (current_user.is_admin or current_user.is_notaio):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.multe'))
    
    f = Fine.query.get(fine_id)
    if not f or not f.voting_active:
        flash('Votazione non trovata o non attiva.', 'warning')
        return redirect(url_for('main.multe'))
    
    # Elimina tutti i voti associati
    FineVote.query.filter_by(fine_id=fine_id).delete()
    
    # Riporta la denuncia in stato pending_approval
    f.voting_active = False
    f.voting_start = None
    f.voting_end = None
    f.excluded_voters = '[]'
    f.pending_approval = True  # Torna in attesa di approvazione
    
    db.session.commit()
    
    # Notifica
    multato = User.query.get(f.user_id)
    multato_nome = get_nome_giocatore(multato)
    crea_notifica(
        'denuncia_votazione_annullata',
        f"🚫 Votazione annullata per la multa a {multato_nome}. La denuncia torna in attesa.",
        icon='🚫'
    )
    
    flash('Votazione annullata. La denuncia è tornata in attesa di approvazione.', 'info')
    return redirect(url_for('main.multe'))

def get_or_create_training(training_date):
    """Recupera o crea un allenamento per una data specifica"""
    training = Training.query.filter_by(date=training_date).first()
    if not training:
        training = Training(date=training_date, start_time='19:00', end_time='21:00')
        db.session.add(training)
        db.session.commit()
    return training

def generate_training_dates(weeks_ahead=4):
    """Genera le date degli allenamenti per le prossime settimane"""
    today = date.today()
    training_dates = []
    
    # Recupera le date delle partite future (anche passate per gestire quelle già esistenti)
    all_matches = Event.query.all()
    match_dates = set(m.date_start.date() for m in all_matches)
    
    for i in range(weeks_ahead * 7):
        check_date = today + timedelta(days=i)
        weekday = check_date.weekday()  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        
        # Martedì (1), Mercoledì (2) e Venerdì (4) solo se non c'è partita
        if weekday in [1, 2, 4] and check_date not in match_dates:
            training_dates.append(check_date)
    
    return training_dates

@main_bp.route('/presenze')
@login_required
def presenze():
    now = datetime.now()
    today = date.today()
    
    # Recupera partite future
    future_matches = Event.query.filter(Event.date_start >= now).order_by(Event.date_start).all()
    
    # Genera date allenamenti
    training_dates = generate_training_dates(4)
    
    # Crea/recupera gli allenamenti nel database
    trainings = []
    for td in training_dates:
        training = get_or_create_training(td)
        if not training.is_cancelled:
            trainings.append(training)
    
    # Combina tutti gli eventi futuri
    all_events = []
    
    # Aggiungi partite
    for match in future_matches:
        absences = Attendance.query.filter_by(event_id=match.id, status='absent').count()
        absent_users = [a.user for a in Attendance.query.filter_by(event_id=match.id, status='absent').all()]
        user_absent = Attendance.query.filter_by(event_id=match.id, user_id=current_user.id, status='absent').first()
        
        all_events.append({
            'type': 'match',
            'id': match.id,
            'date': match.date_start.date(),
            'datetime': match.date_start,
            'title': f"🏐 Partita vs {match.opponent_name}",
            'subtitle': f"{'Casa' if match.is_home else 'Trasferta'} - {match.date_start.strftime('%H:%M')}",
            'absences': absences,
            'absent_users': absent_users,
            'user_is_absent': user_absent is not None,
            'user_reason': user_absent.reason if user_absent else None,
            'location': match.location,
            'is_home': match.is_home,
            'is_friendly': match.is_friendly
        })
    
    # Aggiungi allenamenti
    for training in trainings:
        absences = Attendance.query.filter_by(training_id=training.id, status='absent').count()
        absent_users = [a.user for a in Attendance.query.filter_by(training_id=training.id, status='absent').all()]
        user_absent = Attendance.query.filter_by(training_id=training.id, user_id=current_user.id, status='absent').first()
        
        # Late tracking
        late_count = Attendance.query.filter_by(training_id=training.id, status='late').count()
        late_users = [(a.user, a.reason) for a in Attendance.query.filter_by(training_id=training.id, status='late').all()]
        user_late = Attendance.query.filter_by(training_id=training.id, user_id=current_user.id, status='late').first()
        
        weekday_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        weekday_name = weekday_names[training.date.weekday()]
        
        all_events.append({
            'type': 'training',
            'id': training.id,
            'date': training.date,
            'datetime': datetime.combine(training.date, datetime.strptime(training.start_time, '%H:%M').time()),
            'title': f"📋 Allenamento ({weekday_name})",
            'subtitle': f"{training.start_time} - {training.end_time}",
            'absences': absences,
            'absent_users': absent_users,
            'user_is_absent': user_absent is not None,
            'user_reason': user_absent.reason if user_absent else None,
            'late_count': late_count,
            'late_users': late_users,
            'user_is_late': user_late is not None,
            'user_late_reason': user_late.reason if user_late else None,
            'start_time': training.start_time,
            'end_time': training.end_time,
            'coach_notes': training.coach_notes,
            'coach_notes_private': training.coach_notes_private
        })
    
    # Ordina per data
    all_events.sort(key=lambda x: x['datetime'])
    
    # --- STORICO (ultimi 14 giorni) ---
    history_start_date = now - timedelta(days=14)
    
    # Partite passate
    past_matches = Event.query.filter(Event.date_start < now, Event.date_start >= history_start_date).order_by(Event.date_start.desc()).all()
    
    # Allenamenti passati
    past_trainings = Training.query.filter(Training.date < today, Training.date >= history_start_date.date()).order_by(Training.date.desc()).all()
    
    history_events = []
    
    for match in past_matches:
        absences = Attendance.query.filter_by(event_id=match.id, status='absent').count()
        absent_users = [a.user for a in Attendance.query.filter_by(event_id=match.id, status='absent').all()]
        history_events.append({
            'type': 'match',
            'id': match.id,
            'date': match.date_start.date(),
            'datetime': match.date_start,
            'title': f"🏐 Partita vs {match.opponent_name}",
            'subtitle': f"{'Casa' if match.is_home else 'Trasferta'} - {match.date_start.strftime('%H:%M')}",
            'absences': absences,
            'absent_users': absent_users,
            'result': f"{match.sets_us}-{match.sets_them}" if match.sets_us is not None else None,
            'is_friendly': match.is_friendly
        })
    
    for training in past_trainings:
        absences = Attendance.query.filter_by(training_id=training.id, status='absent').count()
        absent_users = [a.user for a in Attendance.query.filter_by(training_id=training.id, status='absent').all()]
        late_count = Attendance.query.filter_by(training_id=training.id, status='late').count()
        weekday_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        weekday_name = weekday_names[training.date.weekday()]
        
        history_events.append({
            'type': 'training',
            'id': training.id,
            'date': training.date,
            'datetime': datetime.combine(training.date, datetime.strptime(training.start_time, '%H:%M').time()),
            'title': f"📋 Allenamento ({weekday_name})",
            'subtitle': f"{training.start_time} - {training.end_time}",
            'absences': absences,
            'absent_users': absent_users,
            'late_count': late_count,
            'coach_notes': training.coach_notes,
            'coach_notes_private': training.coach_notes_private,
            'is_cancelled': training.is_cancelled
        })
    
    # Ordina storico per data (più recenti prima)
    history_events.sort(key=lambda x: x['datetime'], reverse=True)
    
    # --- FILTRI ---
    filter_type = request.args.get('filter', 'all')  # 'all', 'training', 'match'
    
    if filter_type == 'training':
        all_events = [e for e in all_events if e['type'] == 'training']
        history_events = [e for e in history_events if e['type'] == 'training']
    elif filter_type == 'match':
        all_events = [e for e in all_events if e['type'] == 'match']
        history_events = [e for e in history_events if e['type'] == 'match']
    
    # Recupera tutti i giocatori per la gestione manuale assenze
    players = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()
    
    # Controlla permessi
    can_manage = current_user.is_admin or current_user.is_capitano or current_user.is_coach
    
    return render_template('presenze.html', 
                          events=all_events, 
                          history_events=history_events,
                          players=players,
                          can_manage=can_manage,
                          current_filter=filter_type,
                          now=now)

@main_bp.route('/segna_assenza/<event_type>/<int:event_id>', methods=['POST'])
@login_required
def segna_assenza(event_type, event_id):
    try:
        reason = request.form.get('reason', '').strip()
        
        if event_type == 'match':
            existing = Attendance.query.filter_by(event_id=event_id, user_id=current_user.id).first()
            if existing:
                # Rimuovi assenza (toggle)
                db.session.delete(existing)
                flash('Assenza annullata!', 'success')
            else:
                # Segna assenza
                att = Attendance(event_id=event_id, user_id=current_user.id, status='absent', reason=reason if reason else None)
                db.session.add(att)
                flash('Assenza segnata!', 'warning')
        
        elif event_type == 'training':
            existing = Attendance.query.filter_by(training_id=event_id, user_id=current_user.id).first()
            if existing:
                # Rimuovi assenza (toggle)
                db.session.delete(existing)
                flash('Assenza annullata!', 'success')
            else:
                # Segna assenza
                att = Attendance(training_id=event_id, user_id=current_user.id, status='absent', reason=reason if reason else None)
                db.session.add(att)
                flash('Assenza segnata!', 'warning')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nel salvare l\'assenza. Riprova.', 'danger')
        print(f'[ERRORE] segna_assenza: {e}')
    return redirect(url_for('main.presenze'))

@main_bp.route('/segna_ritardo/<int:training_id>', methods=['POST'])
@login_required
def segna_ritardo(training_id):
    reason = request.form.get('reason', '').strip()
    
    # Check if already marked as absent or late
    existing = Attendance.query.filter_by(training_id=training_id, user_id=current_user.id).first()
    if existing:
        if existing.status == 'late':
            # Toggle off
            db.session.delete(existing)
            flash('Ritardo annullato!', 'success')
        else:
            # Already absent, update to late
            existing.status = 'late'
            existing.reason = reason if reason else None
            flash('Stato aggiornato a ritardo!', 'info')
    else:
        # Mark as late
        att = Attendance(training_id=training_id, user_id=current_user.id, status='late', reason=reason if reason else None)
        db.session.add(att)
        flash('Ritardo segnato!', 'info')
    
    db.session.commit()
    return redirect(url_for('main.presenze'))

@main_bp.route('/modifica_training/<int:training_id>', methods=['POST'])
@login_required
def modifica_training(training_id):
    # Solo admin, capitano, coach
    if not (current_user.is_admin or current_user.is_capitano or current_user.is_coach):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.presenze'))
    
    training = Training.query.get_or_404(training_id)
    
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    is_cancelled = request.form.get('is_cancelled') == 'on'
    coach_notes = request.form.get('coach_notes', '').strip()
    
    if start_time:
        training.start_time = start_time
    if end_time:
        training.end_time = end_time
    training.is_cancelled = is_cancelled
    training.coach_notes = coach_notes if coach_notes else None
    
    # Private notes (solo coach/admin)
    coach_notes_private = request.form.get('coach_notes_private', '').strip()
    training.coach_notes_private = coach_notes_private if coach_notes_private else None
    
    db.session.commit()
    flash('Allenamento modificato!', 'success')
    return redirect(url_for('main.presenze'))

@main_bp.route('/segna_assenza_membro/<event_type>/<int:event_id>/<int:user_id>', methods=['POST'])
@login_required
def segna_assenza_membro(event_type, event_id, user_id):
    # Solo admin, capitano, coach
    if not (current_user.is_admin or current_user.is_capitano or current_user.is_coach):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('main.presenze'))
    
    try:
        reason = request.form.get('reason', '').strip()
        user = User.query.get_or_404(user_id)
        
        if event_type == 'match':
            existing = Attendance.query.filter_by(event_id=event_id, user_id=user_id).first()
            if existing:
                db.session.delete(existing)
                flash(f'Assenza di {get_nome_giocatore(user)} annullata!', 'success')
            else:
                att = Attendance(event_id=event_id, user_id=user_id, status='absent', reason=reason if reason else None)
                db.session.add(att)
                flash(f'Assenza di {get_nome_giocatore(user)} segnata!', 'warning')
        
        elif event_type == 'training':
            existing = Attendance.query.filter_by(training_id=event_id, user_id=user_id).first()
            if existing:
                db.session.delete(existing)
                flash(f'Assenza di {get_nome_giocatore(user)} annullata!', 'success')
            else:
                att = Attendance(training_id=event_id, user_id=user_id, status='absent', reason=reason if reason else None)
                db.session.add(att)
                flash(f'Assenza di {get_nome_giocatore(user)} segnata!', 'warning')
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nel salvare l\'assenza. Riprova.', 'danger')
        print(f'[ERRORE] segna_assenza_membro: {e}')
    return redirect(url_for('main.presenze'))

@main_bp.route('/partite') 
@login_required
def partite():
    now = datetime.now()
    all_events = Event.query.order_by(Event.date_start.asc()).all()
    future, past = [], []
    for e in all_events:
        deadline = get_mvp_deadline(e.date_start)
        # Skip MVP calculation for friendly matches
        if e.date_start < now and e.mvp_id is None and now > deadline and not e.is_friendly:
            # Calcola MVP se non ancora assegnato e scadenza passata
            top = db.session.query(Vote.voted_user_id, func.count(Vote.voted_user_id).label('c')).filter_by(event_id=e.id).group_by(Vote.voted_user_id).order_by(desc('c')).first()
            if top:
                e.mvp_id = top.voted_user_id
                db.session.commit()
        e.voting_closed = (now > deadline)
        if e.date_start > now: future.append(e)
        else: past.append(e)
    past.reverse()
    players = User.query.filter(User.is_coach.isnot(True)).order_by(User.nome_completo).all()
    return render_template('partite.html', future=future, past=past, players=players, now=now)

@main_bp.route('/crea_partita', methods=['POST'])
@login_required
def crea_partita():
    if not current_user.is_admin: return redirect(url_for('main.partite'))
    dt = datetime.strptime(f"{request.form.get('data')} {request.form.get('ora')}", '%Y-%m-%d %H:%M')
    is_home = (request.form.get('casa_trasferta') == 'casa')
    loc = "PalaArtiglio" if is_home else request.form.get('location')
    is_friendly = request.form.get('is_friendly') == 'on'
    e = Event(opponent_name=request.form.get('opponent_name'), date_start=dt, is_home=is_home, location=loc, is_friendly=is_friendly)
    db.session.add(e)
    
    # Cancella allenamento se esiste nella stessa data
    match_date = dt.date()
    existing_training = Training.query.filter_by(date=match_date).first()
    if existing_training:
        db.session.delete(existing_training)
        flash('Partita aggiunta e allenamento dello stesso giorno rimosso', 'success')
    else:
        flash('Partita aggiunta', 'success')
    
    db.session.commit()
    return redirect(url_for('main.partite'))

@main_bp.route('/modifica_partita', methods=['POST'])
@login_required
def modifica_partita():
    if not current_user.is_admin: return redirect(url_for('main.partite'))
    e = Event.query.get(int(request.form.get('event_id')))
    if e:
        old_date = e.date_start.date()
        e.opponent_name = request.form.get('opponent_name')
        e.location = request.form.get('location')
        e.is_home = (request.form.get('casa_trasferta') == 'casa')
        e.is_friendly = request.form.get('is_friendly') == 'on'
        d, t = request.form.get('data'), request.form.get('ora')
        if d and t:
            new_dt = datetime.strptime(f"{d} {t}", '%Y-%m-%d %H:%M')
            e.date_start = new_dt
            new_date = new_dt.date()
            
            # Se la data è cambiata, cancella allenamento nella nuova data
            if old_date != new_date:
                existing_training = Training.query.filter_by(date=new_date).first()
                if existing_training:
                    db.session.delete(existing_training)
        
        db.session.commit()
    return redirect(url_for('main.partite'))

@main_bp.route('/elimina_partita/<int:event_id>')
@login_required
def elimina_partita(event_id):
    if not current_user.is_admin: return redirect(url_for('main.partite'))
    e = Event.query.get(event_id)
    if e:
        Attendance.query.filter_by(event_id=event_id).delete()
        db.session.delete(e)
        db.session.commit()
    return redirect(url_for('main.partite'))

@main_bp.route('/segnala_assenza/<int:event_id>', methods=['GET', 'POST'])
@login_required
def segnala_assenza(event_id):
    try:
        p = Attendance.query.filter_by(user_id=current_user.id, event_id=event_id).first()
        if p:
            db.session.delete(p)
            flash('Assenza annullata!', 'success')
        else:
            db.session.add(Attendance(user_id=current_user.id, event_id=event_id, status='absent'))
            flash('Assenza segnata!', 'warning')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nel salvare l\'assenza. Riprova.', 'danger')
        print(f'[ERRORE] segnala_assenza: {e}')
    return redirect(url_for('main.partite'))

@main_bp.route('/salva_risultato', methods=['POST'])
@login_required
def salva_risultato():
    if not current_user.is_admin: return redirect(url_for('main.partite'))
    e = Event.query.get(int(request.form.get('event_id')))
    if e:
        e.sets_us = int(request.form.get('sets_us'))
        e.sets_them = int(request.form.get('sets_them'))
        db.session.commit()
        
        # Notifica apertura votazione MVP (solo partite ufficiali)
        if not e.is_friendly:
            deadline = get_mvp_deadline(e.date_start)
            deadline_str = deadline.strftime('%A %d/%m alle %H:%M').capitalize()
            risultato = f"{e.sets_us}-{e.sets_them}"
            notifica_key = f"mvp_voting_{e.id}"
            # Evita duplicati
            existing = Notification.query.filter(
                Notification.tipo == 'mvp',
                Notification.messaggio.contains(f"vs {e.opponent_name}")
            ).filter(
                Notification.messaggio.contains(risultato)
            ).first()
            if not existing:
                crea_notifica(
                    'mvp',
                    f"🗳️ Votazione MVP aperta! Partita vs {e.opponent_name} ({risultato}). Vota il migliore in campo entro {deadline_str}!",
                    icon='🗳️'
                )
    return redirect(url_for('main.partite'))

@main_bp.route('/vote_mvp/<int:event_id>', methods=['POST'])
@login_required
def vote_mvp(event_id):
    event = Event.query.get_or_404(event_id)
    voted_user_id = request.form.get('voted_user_id')

    # Block voting for friendly matches
    if event.is_friendly:
        flash('Le partite amichevoli non hanno votazione MVP!', 'warning')
        return redirect(url_for('main.home'))

    if not voted_user_id:
        flash('Devi selezionare un giocatore!', 'danger')
        return redirect(url_for('main.home'))

    # Check if already voted
    if Vote.query.filter_by(user_id=current_user.id, event_id=event.id).first():
        flash('Hai già votato per questa partita!', 'warning')
        return redirect(url_for('main.home'))

    # Check deadline
    deadline = get_mvp_deadline(event.date_start)
    if datetime.now() > deadline:
        flash('Le votazioni sono chiuse!', 'danger')
        return redirect(url_for('main.home'))

    vote = Vote(user_id=current_user.id, event_id=event.id, voted_user_id=voted_user_id)
    db.session.add(vote)
    db.session.commit()

    flash('Voto registrato!', 'success')
    return redirect(url_for('main.home'))

@main_bp.route('/calendario')
@login_required
def calendario():
    year = request.args.get('year', type=int, default=datetime.now().year)
    month = request.args.get('month', type=int, default=datetime.now().month)
    
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    
    # 1. Recupera Turni Pizza/Birra
    turni_db = Turno.query.filter(Turno.date >= start_date, Turno.date <= end_date).all()
    # 2. Recupera Partite (Eventi)
    # Nota: Event.date_start è DateTime, dobbiamo convertire per il confronto o estrarre
    eventi_db = Event.query.filter(Event.date_start >= datetime(year, month, 1), Event.date_start <= datetime(year, month, last_day, 23, 59, 59)).all()

    # Creiamo una mappa unificata: 'YYYY-MM-DD' -> { 'turno': ..., 'match': ... }
    days_data = {}
    
    # Popola con Turni (può esserci sia pizza che birra nello stesso giorno)
    # Dedupe: a volte possono esistere record duplicati per (date, tipo).
    # In quel caso teniamo un solo record “canonico” e uniamo gli incaricati.
    canonical_by_key: dict[tuple[str, str], Turno] = {}
    for t in turni_db:
        d_str = t.date.strftime('%Y-%m-%d')
        key = (d_str, t.tipo)
        existing = canonical_by_key.get(key)
        if not existing:
            canonical_by_key[key] = t
            continue

        # Scegli come canonico quello con id maggiore (più recente)
        keep = t if (t.id or 0) > (existing.id or 0) else existing
        drop = existing if keep is t else t

        # Unisci incaricati (evita perdita dati)
        try:
            keep_ids = {u.id for u in keep.incaricati}
            for u in drop.incaricati:
                if u.id not in keep_ids:
                    keep.incaricati.append(u)
                    keep_ids.add(u.id)
        except Exception:
            pass

        # Se uno dei due è cancellato e l'altro no, preferisci quello non cancellato
        if getattr(existing, 'is_cancelled', False) and not getattr(t, 'is_cancelled', False):
            keep = t
        elif getattr(t, 'is_cancelled', False) and not getattr(existing, 'is_cancelled', False):
            keep = existing

        canonical_by_key[key] = keep

    for t in canonical_by_key.values():
        d_str = t.date.strftime('%Y-%m-%d')
        if d_str not in days_data:
            days_data[d_str] = {}

        if 'turni' not in days_data[d_str]:
            days_data[d_str]['turni'] = []
        days_data[d_str]['turni'].append(t)

        if 'turno' not in days_data[d_str]:
            days_data[d_str]['turno'] = t

    # Popola con Partite
    for e in eventi_db:
        d_str = e.date_start.strftime('%Y-%m-%d')
        if d_str not in days_data: days_data[d_str] = {}
        days_data[d_str]['match'] = e

    players = User.query.order_by(User.nome_completo).all()
    
    # Calcola quante volte ogni giocatore ha portato pizza/birra in passato
    # Conta solo i turni non cancellati
    turni_counts = {}
    # Dedupe anche nei conteggi per evitare doppioni.
    all_turni_raw = Turno.query.filter(Turno.is_cancelled == False).all()
    all_turni_map: dict[tuple[date, str], Turno] = {}
    for t in all_turni_raw:
        key = (t.date, t.tipo)
        existing = all_turni_map.get(key)
        if not existing or (t.id or 0) > (existing.id or 0):
            all_turni_map[key] = t
    all_turni = list(all_turni_map.values())
    for player in players:
        pizza_count = 0
        birra_count = 0
        for turno in all_turni:
            if player in turno.incaricati:
                if turno.tipo == 'pizza':
                    pizza_count += 1
                elif turno.tipo == 'birra':
                    birra_count += 1
        turni_counts[player.id] = {'pizza': pizza_count, 'birra': birra_count}

    prev_year, prev_month = (year, month - 1) if month > 1 else (year - 1, 12)
    next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

    return render_template('calendario.html', 
                           calendar=cal, year=year, month=month, month_name=month_name,
                           days_data=days_data, players=players, turni_counts=turni_counts,
                           prev_ym={'y': prev_year, 'm': prev_month},
                           next_ym={'y': next_year, 'm': next_month},
                           now=datetime.now())

@main_bp.route('/gestisci_turno', methods=['POST'])
@login_required
def gestisci_turno():
    payload = request.get_json(silent=True) or {}
    data_str = request.form.get('date') or payload.get('date')
    tipo = request.form.get('tipo') or payload.get('tipo')
    action = request.form.get('action') or payload.get('action')

    user_ids = request.form.getlist('user_ids')
    if not user_ids and isinstance(payload.get('user_ids'), list):
        user_ids = [str(x) for x in payload.get('user_ids') if x is not None]
    
    print(f"[TURNO] User: {current_user.username}, Data: {data_str}, Tipo: {tipo}, Action: {action}")
    print(f"[TURNO] Permessi - is_admin: {current_user.is_admin}, is_birra: {current_user.is_birra}, is_pizza: {current_user.is_pizza}")
    
    if not action and user_ids:
        action = 'assign'

    if not data_str or not tipo or not action:
        missing = []
        if not data_str:
            missing.append('date')
        if not tipo:
            missing.append('tipo')
        if not action:
            missing.append('action')
        flash('Dati mancanti! (' + ', '.join(missing) + ')', 'danger')
        print(f"[TURNO] Dati mancanti: missing={missing} form_keys={list(request.form.keys())} json_keys={list(payload.keys())}")
        return redirect(url_for('main.calendario'))
    
    # Permessi
    permesso_birra = (tipo == 'birra' and (current_user.is_admin or current_user.is_birra))
    permesso_pizza = (tipo == 'pizza' and (current_user.is_admin or current_user.is_pizza))
    
    print(f"[TURNO] Permesso birra: {permesso_birra}, Permesso pizza: {permesso_pizza}")
    
    if not (permesso_birra or permesso_pizza):
        flash(f'Non hai i permessi per gestire {tipo}!', 'danger')
        return redirect(url_for('main.calendario'))

    dt_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    # Cerca il turno specifico per tipo (può esserci sia pizza che birra lo stesso giorno)
    # Gestione robusta: se esistono duplicati per (date, tipo), consolida.
    turni_same_key = Turno.query.filter_by(date=dt_obj, tipo=tipo).order_by(Turno.id.desc()).all()
    turno = turni_same_key[0] if turni_same_key else None

    if len(turni_same_key) > 1 and turno:
        try:
            keep_ids = {u.id for u in turno.incaricati}
            for extra in turni_same_key[1:]:
                for u in extra.incaricati:
                    if u.id not in keep_ids:
                        turno.incaricati.append(u)
                        keep_ids.add(u.id)
                db.session.delete(extra)
            db.session.commit()
            print(f"[TURNO] Consolidati duplicati per {dt_obj} tipo={tipo} (tenuto id={turno.id}, rimossi {len(turni_same_key)-1})")
        except Exception as e:
            print(f"[TURNO] Errore consolidamento duplicati: {e}")
    
    if action == 'cancel':
        if not turno:
            turno = Turno(date=dt_obj, tipo=tipo)
            db.session.add(turno)
        turno.is_cancelled = True
        turno.incaricati = [] 
        db.session.commit()
    elif action == 'assign':
        print(f"[TURNO] Assegnazione - user_ids ricevuti: {user_ids}")
        
        if not turno:
            turno = Turno(date=dt_obj, tipo=tipo)
            db.session.add(turno)
            print(f"[TURNO] Creato nuovo turno per {dt_obj} tipo {tipo}")
        
        turno.is_cancelled = False
        turno.incaricati = [] 
        for uid in user_ids:
            try:
                u = User.query.get(int(uid))
                if u:
                    turno.incaricati.append(u)
                    print(f"[TURNO] Aggiunto incaricato: {get_nome_giocatore(u)}")
                else:
                    print(f"[TURNO] User con ID {uid} non trovato")
            except Exception as e:
                print(f"[TURNO] Errore aggiungendo user {uid}: {e}")
        
        db.session.commit()
        print(f"[TURNO] Salvato turno con {len(turno.incaricati)} incaricati")
        
        # Crea notifica per assegnazione turno
        if user_ids:
            responsabile = "Mastro Birraio" if tipo == 'birra' else "Resp. Pizza"
            assegnatore_nome = get_nome_giocatore(current_user)
            for uid in user_ids:
                u = User.query.get(int(uid))
                if u:
                    incaricato_nome = get_nome_giocatore(u)
                    emoji = '🍺' if tipo == 'birra' else '🍕'
                    crea_notifica(
                        'turno_assegnato',
                        f"{emoji} {incaricato_nome} è stato incaricato da {assegnatore_nome} ({responsabile}) per portare la {tipo} il {dt_obj.strftime('%d/%m/%Y')}",
                        icon=emoji
                    )
    elif action == 'delete':
        if turno:
            db.session.delete(turno)
            db.session.commit()

    return redirect(url_for('main.calendario', year=dt_obj.year, month=dt_obj.month))

@main_bp.route('/salva_statistiche', methods=['POST'])
@login_required
def salva_statistiche():
    if not (current_user.is_admin or current_user.is_scout):
        return redirect(url_for('main.partite'))

    event_id = int(request.form.get('event_id'))
    evento = Event.query.get(event_id)

    if not evento:
        flash('Partita non trovata', 'danger')
        return redirect(url_for('main.partite'))

    # Aggiorna statistiche di squadra
    evento.total_missed_serves = int(request.form.get('total_missed_serves', 0))

    # Aggiorna o crea statistiche individuali per ogni giocatore
    all_players = User.query.filter(User.is_coach.isnot(True)).all()

    for player in all_players:
        points = int(request.form.get(f'points_{player.id}', 0))
        aces = int(request.form.get(f'aces_{player.id}', 0))
        blocks = int(request.form.get(f'blocks_{player.id}', 0))

        # Cerca se esiste già una statistica per questo giocatore in questa partita
        stat = MatchStats.query.filter_by(user_id=player.id, event_id=event_id).first()

        if stat:
            # Aggiorna i valori esistenti
            stat.points = points
            stat.aces = aces
            stat.blocks = blocks
        else:
            # Crea nuova statistica solo se almeno un valore > 0
            if points > 0 or aces > 0 or blocks > 0:
                new_stat = MatchStats(
                    user_id=player.id,
                    event_id=event_id,
                    points=points,
                    aces=aces,
                    blocks=blocks
                )
                db.session.add(new_stat)

    db.session.commit()
    flash('Statistiche salvate con successo!', 'success')
    return redirect(url_for('main.partite'))

@main_bp.route('/export_calendar_ics')
@login_required
def export_calendar_ics():
    """Genera e scarica un file .ics con le partite future"""
    now = datetime.now()
    # Prendi tutte le partite future
    events = Event.query.filter(Event.date_start >= now).order_by(Event.date_start.asc()).all()
    
    if not events:
        flash('Nessuna partita futura da esportare.', 'warning')
        return redirect(url_for('main.calendario', year=now.year, month=now.month))

    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GS Artiglio//NONSGML Calendar//EN",
        "X-WR-CALNAME:GS Artiglio Partite",
        "CALSCALE:GREGORIAN",
    ]

    for event in events:
        # Assumiamo durata 2 ore
        start_time = event.date_start
        end_time = start_time + timedelta(hours=2)
        
        # Formattazione data ICS: YYYYMMDDTHHMMSS
        dtstart = start_time.strftime('%Y%m%dT%H%M%S')
        dtend = end_time.strftime('%Y%m%dT%H%M%S')
        dtstamp = datetime.now().strftime('%Y%m%dT%H%M%S')
        
        summary = f"Partita vs {event.opponent_name}"
        location = event.location or "Campo Sportivo"
        
        # Genera link Google Maps
        maps_link = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(location)}"
        description = f"Partita contro {event.opponent_name}.\\nLink Maps: {maps_link}"
        
        ics_content.append("BEGIN:VEVENT")
        ics_content.append(f"UID:event_{event.id}@gsartiglio.app")
        ics_content.append(f"DTSTAMP:{dtstamp}")
        ics_content.append(f"DTSTART:{dtstart}")
        ics_content.append(f"DTEND:{dtend}")
        ics_content.append(f"SUMMARY:{summary}")
        ics_content.append(f"LOCATION:{location}")
        ics_content.append(f"DESCRIPTION:{description}")
        ics_content.append("END:VEVENT")

    ics_content.append("END:VCALENDAR")
    
    response = Response("\r\n".join(ics_content), mimetype="text/calendar")
    response.headers["Content-Disposition"] = "attachment; filename=partite_gs_artiglio.ics"
    return response

@main_bp.route('/admin/assegna-skin', methods=['GET', 'POST'])
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
                user = User.query.get(int(uid))
                if not user:
                    continue
                profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = FlappyGameProfile(user_id=user.id)
                    db.session.add(profile)
                    db.session.commit()
                unlocked = json.loads(profile.unlocked_skins)
                player_name = get_nome_giocatore(user)
                if skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    crea_notifica('skin_unlock', f'🎨 {player_name} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]}', icon=skin_info['icon'])
                    risultati.append({'user': player_name, 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': 'Assegnata!'})
                else:
                    risultati.append({'user': player_name, 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': 'Già sbloccata'})
            db.session.commit()
        
        elif action == 'increment_counter':
            skin_id = request.form.get('skin_id')
            user_id = request.form.get('user_id')
            note = request.form.get('note', '').strip()
            
            if skin_id not in ASSIGNABLE_SKINS or ASSIGNABLE_SKINS[skin_id].get('type') != 'counter':
                flash('Skin non valida per incremento.', 'danger')
                return redirect(url_for('admin_custom.admin_assegna_skin'))
            
            skin_info = ASSIGNABLE_SKINS[skin_id]
            user = User.query.get(int(user_id))
            if user:
                profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
                if not profile:
                    profile = FlappyGameProfile(user_id=user.id)
                    db.session.add(profile)
                    db.session.commit()
                counter_field = skin_info['counter_field']
                current_val = getattr(profile, counter_field, 0) or 0
                new_val = current_val + 1
                setattr(profile, counter_field, new_val)
                
                # Save the note
                notes = json.loads(profile.bug_report_notes or '[]')
                notes.append({'note': note or '(nessuna descrizione)', 'date': datetime.now().strftime('%d/%m/%Y %H:%M')})
                profile.bug_report_notes = json.dumps(notes)
                
                player_name = get_nome_giocatore(user)
                unlocked = json.loads(profile.unlocked_skins)
                if new_val >= skin_info['threshold'] and skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    crea_notifica('skin_unlock', f'🎨 {player_name} ha sbloccato la skin {skin_info["name"]}! {skin_info["icon"]} {skin_info["event"]}', icon=skin_info['icon'])
                    risultati.append({'user': player_name, 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': f'Counter {new_val}/{skin_info["threshold"]} - SKIN SBLOCCATA! 🎉'})
                else:
                    risultati.append({'user': player_name, 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': f'Counter aggiornato: {new_val}/{skin_info["threshold"]}'})
                db.session.commit()
        
        elif action == 'decrement_counter':
            skin_id = request.form.get('skin_id')
            user_id = request.form.get('user_id')
            
            if skin_id not in ASSIGNABLE_SKINS or ASSIGNABLE_SKINS[skin_id].get('type') != 'counter':
                flash('Skin non valida.', 'danger')
                return redirect(url_for('admin_custom.admin_assegna_skin'))
            
            skin_info = ASSIGNABLE_SKINS[skin_id]
            user = User.query.get(int(user_id))
            if user:
                profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
                if profile:
                    counter_field = skin_info['counter_field']
                    current_val = getattr(profile, counter_field, 0) or 0
                    new_val = max(0, current_val - 1)
                    setattr(profile, counter_field, new_val)
                    player_name = get_nome_giocatore(user)
                    risultati.append({'user': player_name, 'skin': skin_info['name'], 'icon': skin_info['icon'], 'status': f'Counter aggiornato: {new_val}/{skin_info["threshold"]}'})
                    db.session.commit()
        
        elif action == 'delete_note':
            user_id = request.form.get('user_id')
            note_index = request.form.get('note_index')
            if user_id and note_index is not None:
                profile = FlappyGameProfile.query.filter_by(user_id=int(user_id)).first()
                if profile:
                    try:
                        idx = int(note_index)
                        notes = json.loads(profile.bug_report_notes or '[]')
                        if 0 <= idx < len(notes):
                            del notes[idx]
                            profile.bug_report_notes = json.dumps(notes)
                            db.session.commit()
                            user = User.query.get(int(user_id))
                            risultati.append({'user': get_nome_giocatore(user), 'skin': 'Segnalazioni', 'icon': '📝', 'status': 'Nota eliminata'})
                    except ValueError:
                        pass
        
        elif action == 'edit_note':
            user_id = request.form.get('user_id')
            note_index = request.form.get('note_index')
            new_text = request.form.get('new_text', '').strip()
            if user_id and note_index is not None and new_text:
                profile = FlappyGameProfile.query.filter_by(user_id=int(user_id)).first()
                if profile:
                    try:
                        idx = int(note_index)
                        notes = json.loads(profile.bug_report_notes or '[]')
                        if 0 <= idx < len(notes):
                            notes[idx]['note'] = new_text
                            profile.bug_report_notes = json.dumps(notes)
                            db.session.commit()
                            user = User.query.get(int(user_id))
                            risultati.append({'user': get_nome_giocatore(user), 'skin': 'Segnalazioni', 'icon': '📝', 'status': 'Nota modificata'})
                    except ValueError:
                        pass
    
    # GET: carica tutti i giocatori non-admin con i loro counter e skin
    from sqlalchemy import or_
    users = User.query.filter(or_(User.is_admin == False, User.is_admin == None)).order_by(User.nome_completo).all()
    users_data = []
    for u in users:
        profile = FlappyGameProfile.query.filter_by(user_id=u.id).first()
        if not profile:
            profile = FlappyGameProfile(user_id=u.id)
            db.session.add(profile)
            db.session.commit()
        unlocked = json.loads(profile.unlocked_skins) if profile else []
        counters = {}
        for sid, sinfo in ASSIGNABLE_SKINS.items():
            if sinfo.get('type') == 'counter' and profile:
                try:
                    counters[sid] = getattr(profile, sinfo['counter_field'], 0) or 0
                except Exception:
                    counters[sid] = 0
        users_data.append({
            'id': u.id,
            'nome': get_nome_giocatore(u),
            'skins': {sid: (sid in unlocked) for sid in ASSIGNABLE_SKINS},
            'counters': counters,
            'notes': json.loads(profile.bug_report_notes or '[]') if profile else []
        })
    
    return render_template('admin_assegna_skin.html', skins=ASSIGNABLE_SKINS, users=users_data, risultati=risultati)

@main_bp.route('/admin/fix-top-skins-retroattiva')
@login_required
def admin_fix_top_skins_retroattiva():
    if not current_user.is_admin:
        flash('Accesso non autorizzato!', 'danger')
        return redirect(url_for('main.home'))
    
    # Mappa: internal_badge_code -> skin_id_da_sbloccare
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
        if not badge:
            continue
        
        winners = UserAchievement.query.filter_by(achievement_id=badge.id).all()
        count_for_badge = 0
        
        for ua in winners:
            profile = FlappyGameProfile.query.filter_by(user_id=ua.user_id).first()
            if profile:
                unlocked = json.loads(profile.unlocked_skins)
                if skin_id not in unlocked:
                    unlocked.append(skin_id)
                    profile.unlocked_skins = json.dumps(unlocked)
                    
                    # Invia notifica push individuale
                    user = User.query.get(ua.user_id)
                    player_name = get_nome_giocatore(user)
                    skin_name = skin_id.capitalize()
                    if skin_id == 'mosquito': skin_name = "ZANZARA 🦟"
                    elif skin_id == 'raven': skin_name = "CORVO 🐦‍⬛"
                    elif skin_id == 'dove': skin_name = "COLOMBA 🕊️"
                    elif skin_id == 'goat': skin_name = "CAPRA 🐐"
                    
                    crea_notifica(
                        'skin_unlock', 
                        f'🎨 {player_name} ha sbloccato la skin {skin_name} tramite recupero premi passati!', 
                        icon='✨', 
                        send_push=True
                    )
                    
                    count_for_badge += 1
                    total_assigned += 1
        
        if count_for_badge > 0:
            assigned_details.append(f"{count_for_badge} {skin_id}")
            
    db.session.commit()
    
    if total_assigned > 0:
        details_str = ", ".join(assigned_details)
        flash(f'Sincronizzazione completata! Assegnate {total_assigned} skin retroattive ({details_str}).', 'success')
    else:
        flash('Tutti i vincitori dei Top Badge possiedono già le relative skin. Nessuna nuova assegnazione necessaria.', 'info')
        
    return redirect(url_for('main.admin_assegna_badge_mensili'))

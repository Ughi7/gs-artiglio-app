from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class GlobalSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False) # Es: 'classifica_rank', 'classifica_punti'
    value = db.Column(db.String(200))
    
# TABELLA CLASSIFICA CAMPIONATO
class ClassificaCampionato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    posizione = db.Column(db.Integer, nullable=False)
    squadra = db.Column(db.String(100), nullable=False)
    punti = db.Column(db.Integer, default=0)
    is_artiglio = db.Column(db.Boolean, default=False)  # Per evidenziare la nostra squadra

class ClassificaInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    giornata_attuale = db.Column(db.Integer, default=0)
    giornate_totali = db.Column(db.Integer, default=26)  # Default Serie CM

# TABELLA DI COLLEGAMENTO (Molti-a-Molti tra Turno e User)
turno_assignments = db.Table('turno_assignments',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('turno_id', db.Integer, db.ForeignKey('turno.id'))
)

# 1. TABELLA UTENTI
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    nome_completo = db.Column(db.String(50), nullable=False)
    soprannome = db.Column(db.String(30)) 
    bio = db.Column(db.String(500), nullable=True)  # Bio personale

    # Dati pallavolo
    numero_maglia = db.Column(db.Integer)
    ruolo_volley = db.Column(db.String(30)) 
    
    # RUOLI MULTIPLI
    is_admin = db.Column(db.Boolean, default=False)
    is_notaio = db.Column(db.Boolean, default=False)
    is_capitano = db.Column(db.Boolean, default=False)
    is_pizza = db.Column(db.Boolean, default=False)
    is_birra = db.Column(db.Boolean, default=False)
    is_smm = db.Column(db.Boolean, default=False)
    is_preparatore = db.Column(db.Boolean, default=False)
    is_convenzioni = db.Column(db.Boolean, default=False)
    is_abbigliamento = db.Column(db.Boolean, default=False)
    is_sponsor = db.Column(db.Boolean, default=False)
    is_pensionato = db.Column(db.Boolean, default=False)
    is_gemellaggi = db.Column(db.Boolean, default=False)
    is_coach = db.Column(db.Boolean, default=False)
    is_catering = db.Column(db.Boolean, default=False)
    is_scout = db.Column(db.Boolean, default=False)
    is_dirigente = db.Column(db.Boolean, default=False)
    is_presidente = db.Column(db.Boolean, default=False)

    # GIOCO
    flappy_high_score = db.Column(db.Integer, default=0)

    # STREAK SYSTEM - Giorni consecutivi senza infrazioni
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    last_streak_update = db.Column(db.Date, nullable=True)

    # CERTIFICATO MEDICO
    medical_expiry = db.Column(db.Date, nullable=True)  # Data scadenza certificato
    medical_file = db.Column(db.String(150), nullable=True)  # Nome file certificato

    # RELAZIONI
    multe = db.relationship('Fine', backref='giocatore', lazy=True, foreign_keys='Fine.user_id')
    statistiche = db.relationship('MatchStats', backref='giocatore', lazy=True)
    presenze_rel = db.relationship('Attendance', backref='user', lazy=True)
    # voti_ricevuti = db.relationship('Vote', backref='candidato', foreign_keys='Vote.voted_user_id', lazy=True)
    turni = db.relationship('Turno', secondary=turno_assignments, backref='incaricati')

    # Achievements/Badge
    achievements = db.relationship('UserAchievement', back_populates='user', lazy=True)

    def __init__(
        self,
        username: str,
        password_hash: str,
        nome_completo: str,
        soprannome: str | None = None,
        numero_maglia: int | None = None,
        ruolo_volley: str | None = None,
        is_admin: bool = False,
        is_notaio: bool = False,
        is_capitano: bool = False,
        is_pizza: bool = False,
        is_birra: bool = False,
        is_smm: bool = False,
        is_preparatore: bool = False,
        is_convenzioni: bool = False,
        is_abbigliamento: bool = False,
        is_sponsor: bool = False,
        is_pensionato: bool = False,
        is_gemellaggi: bool = False,
        is_coach: bool = False,
        is_catering: bool = False,
        is_scout: bool = False,
        is_dirigente: bool = False,
        is_presidente: bool = False,
    ):
        self.username = username
        self.password_hash = password_hash
        self.nome_completo = nome_completo
        self.soprannome = soprannome
        self.numero_maglia = numero_maglia
        self.ruolo_volley = ruolo_volley
        self.is_admin = is_admin
        self.is_notaio = is_notaio
        self.is_capitano = is_capitano
        self.is_pizza = is_pizza
        self.is_birra = is_birra
        self.is_smm = is_smm
        self.is_preparatore = is_preparatore
        self.is_convenzioni = is_convenzioni
        self.is_abbigliamento = is_abbigliamento
        self.is_sponsor = is_sponsor
        self.is_pensionato = is_pensionato
        self.is_gemellaggi = is_gemellaggi
        self.is_coach = is_coach
        self.is_catering = is_catering
        self.is_scout = is_scout
        self.is_dirigente = is_dirigente
        self.is_presidente = is_presidente

    def __str__(self):
        return self.soprannome if self.soprannome else self.nome_completo

# 2. TABELLA EVENTI
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    opponent_name = db.Column(db.String(50), nullable=False) 
    date_start = db.Column(db.DateTime, nullable=False)
    is_home = db.Column(db.Boolean, default=True) 
    location = db.Column(db.String(100)) 
    
    sets_us = db.Column(db.Integer, default=0)
    sets_them = db.Column(db.Integer, default=0)
    
    # Statistiche di squadra
    total_missed_serves = db.Column(db.Integer, default=0)
    
    mvp_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    mvp = db.relationship('User', foreign_keys=[mvp_id])
    
    # Partita amichevole - non influisce su statistiche e MVP disabilitato
    is_friendly = db.Column(db.Boolean, default=False)

    stats = db.relationship('MatchStats', backref='match', lazy=True)
    presenze = db.relationship('Attendance', backref='event', lazy=True)
    voti = db.relationship('Vote', backref='match', lazy=True)

    def count_presenti(self):
        totale = User.query.count()
        assenti = Attendance.query.filter_by(event_id=self.id, status='absent').count()
        return max(0, totale - assenti)

    def is_absent(self, user_id):
        a = Attendance.query.filter_by(event_id=self.id, user_id=user_id, status='absent').first()
        return True if a else False
        
    def has_voted(self, user_id):
        return Vote.query.filter_by(event_id=self.id, user_id=user_id).first() is not None

    def __str__(self):
        return f"{self.opponent_name} ({self.date_start.strftime('%d/%m/%Y')})"

# 3. TABELLA VOTI
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    voted_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    voter = db.relationship('User', foreign_keys=[user_id], backref='voti_espressi')
    candidate = db.relationship('User', foreign_keys=[voted_user_id], backref='voti_mvp_ricevuti')

    def __str__(self):
        return f"Voto da {self.voter} per {self.candidate}"

# 4. TABELLA MULTE
class Fine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    deadline = db.Column(db.DateTime, nullable=True) # Scadenza
    paid = db.Column(db.Boolean, default=False)

    payment_method = db.Column(db.String(20)) # 'contanti' or 'paypal'
    has_generated_mora = db.Column(db.Boolean, default=False)

    # Campi per denunce da approvare
    pending_approval = db.Column(db.Boolean, default=False)  # True se è una denuncia da approvare
    denunciante_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Chi ha denunciato
    note = db.Column(db.String(500), nullable=True)  # Note facoltative per la denuncia

    # Campi per sistema di votazione
    voting_active = db.Column(db.Boolean, default=False)  # True se la votazione è attiva
    voting_start = db.Column(db.DateTime, nullable=True)  # Quando è iniziata la votazione
    voting_end = db.Column(db.DateTime, nullable=True)  # Quando scade la votazione (24h dopo start)
    excluded_voters = db.Column(db.String(500), default='[]')  # JSON list of user IDs excluded from voting

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def is_overdue(self):
        if self.paid: return False
        # MODIFICA QUI:
        return datetime.now() > self.deadline if self.deadline else False

# 4b. VOTI SULLE MULTE (per sistema votazione)
class FineVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fine_id = db.Column(db.Integer, db.ForeignKey('fine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote = db.Column(db.Boolean, nullable=False)  # True = approva multa, False = rifiuta
    voted_at = db.Column(db.DateTime, default=datetime.now)
    
    fine = db.relationship('Fine', backref='votes')
    user = db.relationship('User')
    
    __table_args__ = (
        db.UniqueConstraint('fine_id', 'user_id', name='unique_fine_vote'),
    )

# 5. TABELLA TURNI
class Turno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    is_cancelled = db.Column(db.Boolean, default=False)

# 6. STATISTICHE & PRESENZE
class MatchStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sets_played = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    aces = db.Column(db.Integer, default=0)
    blocks = db.Column(db.Integer, default=0)
    attacks = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)

# 6b. ALLENAMENTI
class Training(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    start_time = db.Column(db.String(5), default='19:00')  # Formato HH:MM
    end_time = db.Column(db.String(5), default='21:00')    # Formato HH:MM
    is_cancelled = db.Column(db.Boolean, default=False)
    coach_notes = db.Column(db.String(500), nullable=True)  # Note pubbliche (visibili a tutti)
    coach_notes_private = db.Column(db.String(500), nullable=True)  # Note private (solo coach/admin)
    
    presenze = db.relationship('Attendance', backref='training', lazy=True, 
                               foreign_keys='Attendance.training_id')
    
    def count_assenti(self):
        return Attendance.query.filter_by(training_id=self.id, status='absent').count()

# 6c. PRESENZE (esteso per allenamenti)
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='present')  # 'present' or 'absent'
    reason = db.Column(db.String(200), nullable=True)     # Motivo assenza (opzionale)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    training_id = db.Column(db.Integer, db.ForeignKey('training.id'), nullable=True)

# 7. NOTIFICHE BACHECA
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)  # 'floppy_top3', 'donatore_top3', 'mvp', 'turno_assegnato', 'denuncia'
    messaggio = db.Column(db.String(500), nullable=False)
    data_creazione = db.Column(db.DateTime, nullable=False, default=datetime.now)
    icon = db.Column(db.String(10), default='📢')  # Emoji per la notifica

# 8. NOTIFICHE NASCOSTE (per utente)
class HiddenNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_id = db.Column(db.Integer, db.ForeignKey('notification.id'), nullable=False)

# 8b. PREFERENZE NOTIFICHE (filtri per utente)
class NotificationPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Push notifications globale
    push_enabled = db.Column(db.Boolean, default=True)
    
    # Filtri per tipo notifica (True = mostra, False = nascondi)
    show_mvp = db.Column(db.Boolean, default=True)
    show_streak = db.Column(db.Boolean, default=True)
    show_turno = db.Column(db.Boolean, default=True)
    show_denuncia = db.Column(db.Boolean, default=True)
    show_flappy = db.Column(db.Boolean, default=True)
    show_donatore = db.Column(db.Boolean, default=True)
    show_certificato = db.Column(db.Boolean, default=True)  # Certificato medico in scadenza
    show_aggiornamento = db.Column(db.Boolean, default=True)  # Aggiornamenti app
    
    user = db.relationship('User', backref=db.backref('notification_prefs', uselist=False))

# 9. STORICO CASSA (uscite/versamenti)
class CashTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Importo (positivo = entrata, negativo = uscita)
    description = db.Column(db.String(200), nullable=False)  # Descrizione
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'uscita' o 'entrata'
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Chi ha registrato

    created_by = db.relationship('User', backref='transazioni_registrate')


# --- SISTEMA BADGE/ACHIEVEMENTS ---
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # es: 'top_donatore_mese', 'top_mvp_mese', 'top_floppy_mese', 'top_criminale_mese', 'top_cecchino_mese', 'top_denunciatore_mese', 'top_floppy_generale', ...
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    icon = db.Column(db.String(10), default='🏅')
    color = db.Column(db.String(20), default='bg-warning')  # Colore badge (classe Bootstrap)
    is_monthly = db.Column(db.Boolean, default=True)  # True = badge mensile, False = generale


class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    month = db.Column(db.Integer, nullable=True)  # Mese di assegnazione (se mensile)
    year = db.Column(db.Integer, nullable=True)   # Anno di assegnazione (se mensile)
    date_awarded = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', back_populates='achievements')
    achievement = db.relationship('Achievement')


# --- SISTEMA PUNTEGGI FLAPPY EAGLE MENSILI ---
class FlappyMonthlyScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    year = db.Column(db.Integer, nullable=False)
    date_achieved = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='flappy_monthly_scores')
    
    # Indice unico per user_id + month + year
    __table_args__ = (
        db.UniqueConstraint('user_id', 'month', 'year', name='unique_user_month_year'),
    )


# 10. PUSH SUBSCRIPTIONS
class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)  # Chiave pubblica
    auth = db.Column(db.String(100), nullable=False)    # Auth secret
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='push_subscriptions')

# 11. FLOPPY EAGLE PROFILE
class FlappyGameProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Progression
    total_games_played = db.Column(db.Integer, default=0)
    total_items_collected = db.Column(db.Integer, default=0) # Total overall items
    
    # Missions (JSON format: {"mission_id": "completed_date", ...})
    # We will store active missions in session or compute them daily, 
    # but we store completed daily missions history here to unlocking things.
    # Actually, simpler: "missions_completed_count" for unlocking skins.
    missions_completed_count = db.Column(db.Integer, default=0)
    
    # Coins (in-game currency)
    coins = db.Column(db.Integer, default=0)
    
    # Skins
    # JSON list of unlocked skins IDs e.g. ["default", "duck", "pigeon"]
    unlocked_skins = db.Column(db.String(500), default='["default"]') 
    selected_skin = db.Column(db.String(50), default='default')
    
    # Streak
    # Daily streak for the game specifically
    last_played_date = db.Column(db.Date, nullable=True)
    current_game_streak = db.Column(db.Integer, default=0)
    
    # New Req
    games_over_2000 = db.Column(db.Integer, default=0)

    # Time specific tracking
    morning_plays = db.Column(db.Integer, default=0) # 5AM-7AM
    night_plays = db.Column(db.Integer, default=0)   # 1AM-5AM
    
    # Track unique dates for time-based unlocks (JSON list of dates)
    morning_play_dates = db.Column(db.String(500), default='[]')
    night_play_dates = db.Column(db.String(500), default='[]')
    
    # Counter per skin a soglia (es. 3 segnalazioni bug = sblocco coccinella)
    bug_report_count = db.Column(db.Integer, default=0)
    bug_report_notes = db.Column(db.Text, default='[]')  # JSON list of notes per bug report
    
    user = db.relationship('User', backref=db.backref('flappy_profile', uselist=False))


# 12. VIDEO ANALYSIS - Tabella di collegamento Video-Protagonisti (Many-to-Many)
video_protagonists = db.Table('video_protagonists',
    db.Column('video_id', db.Integer, db.ForeignKey('video.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Chi ha uploadato
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    filename = db.Column(db.String(200), nullable=False)  # Nome file salvato
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)  # Partita associata (opzionale)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relazioni
    uploader = db.relationship('User', backref='uploaded_videos', foreign_keys=[user_id])
    event = db.relationship('Event', backref='videos')
    protagonists = db.relationship('User', secondary=video_protagonists, backref='featured_in_videos')
    likes = db.relationship('VideoLike', backref='video', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('VideoComment', backref='video', lazy=True, cascade='all, delete-orphan', order_by='VideoComment.created_at.desc()')
    
    def like_count(self):
        return len(self.likes)
    
    def is_liked_by(self, user_id):
        return any(like.user_id == user_id for like in self.likes)


class VideoLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='video_likes')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'video_id', name='unique_video_like'),
    )


class VideoComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('video_comment.id'), nullable=True)  # Reply to another comment
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='video_comments')
    reply_to = db.relationship('VideoComment', remote_side=[id], backref='replies')


# 13. STORICO AGGIORNAMENTI APP
class AppRelease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False, unique=True)  # es. "2.1.0"
    title = db.Column(db.String(100), nullable=False)  # es. "Nuovo sistema notifiche"
    notes = db.Column(db.Text, nullable=False)  # Descrizione delle novità
    release_date = db.Column(db.DateTime, default=datetime.now)
    is_major = db.Column(db.Boolean, default=False)  # Per evidenziare release importanti


# 14. UTENTI CHE HANNO VISTO LA POPUP RELEASE
class UserSeenRelease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    release_id = db.Column(db.Integer, db.ForeignKey('app_release.id'), nullable=False)
    seen_at = db.Column(db.DateTime, default=datetime.now)
    
    user = db.relationship('User', backref='seen_releases')
    release = db.relationship('AppRelease', backref='seen_by')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'release_id', name='unique_user_release'),
    )


# 15. REPORT ATTIVITA MULTE/DENUNCE PER ADMIN E NOTAI
class AdminFineReportEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    fine_id = db.Column(db.Integer, nullable=True)  # No FK: alcune azioni cancellano la multa
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    summary = db.Column(db.String(500), nullable=False)
    details_json = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.now)

    actor = db.relationship('User', foreign_keys=[actor_id], backref='admin_fine_report_events_created')
    target_user = db.relationship('User', foreign_keys=[target_user_id], backref='admin_fine_report_events_received')


class UserSeenAdminFineReportEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('admin_fine_report_event.id'), nullable=False)
    seen_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='seen_admin_fine_report_events')
    event = db.relationship('AdminFineReportEvent', backref='seen_by')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'event_id', name='unique_user_admin_fine_report_event'),
    )


# 16. FEEDBACK UTENTI (Bug + Proposte)
class UserFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feedback_type = db.Column(db.String(20), nullable=False)  # 'bug' o 'proposal'
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    media_path = db.Column(db.String(500), nullable=True)  # Percorso file allegato
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, resolved, rejected
    created_at = db.Column(db.DateTime, default=datetime.now)
    admin_response = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref='feedbacks')


# 17. STORICO VOTAZIONI
class VoteHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fine_reason = db.Column(db.String(100), nullable=False)
    multato_name = db.Column(db.String(50), nullable=False)
    denunciante_name = db.Column(db.String(50), nullable=True)
    outcome = db.Column(db.String(50), nullable=False)
    approve_count = db.Column(db.Integer, nullable=False, default=0)
    reject_count = db.Column(db.Integer, nullable=False, default=0)
    total_voters = db.Column(db.Integer, nullable=False, default=0)
    quorum = db.Column(db.Integer, nullable=False, default=0)
    non_voters = db.Column(db.Text, nullable=False, default='[]')
    closed_at = db.Column(db.DateTime, default=datetime.now)

class UserSeenVoteHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vote_history_id = db.Column(db.Integer, db.ForeignKey('vote_history.id'), nullable=False)
    seen_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='seen_vote_histories')
    vote_history = db.relationship('VoteHistory', backref='seen_by')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'vote_history_id', name='unique_user_vote_history'),
    )

from flask import redirect, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from app.models import (
    db, User, Fine, Event, Turno, Notification, PushSubscription, Vote,
    GlobalSettings, ClassificaCampionato, ClassificaInfo,
    MatchStats, Training, Attendance, HiddenNotification, NotificationPreference,
    CashTransaction, Achievement, UserAchievement,
    Video, VideoLike, VideoComment,
    AppRelease, UserSeenRelease, UserFeedback, FineVote,
    FlappyGameProfile, FlappyMonthlyScore
)

class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login'))

class VoteView(MyModelView):
    column_list = ('id', 'voter', 'candidate', 'match')
    column_labels = {
        'voter': 'Chi ha votato',
        'candidate': 'Votato per',
        'match': 'Partita'
    }

class FineVoteView(MyModelView):
    column_list = ('fine', 'user', 'vote', 'voted_at')
    column_labels = {
        'fine': 'Multa (Giocatore punito)',
        'user': 'Chi ha votato',
        'vote': 'Esito Voto',
        'voted_at': 'Data Voto'
    }
    column_formatters = {
        'vote': lambda v, c, m, p: '✅ APPROVA' if m.vote else '❌ RESPINGE'
    }

def init_admin(app):
    admin = Admin(app, name='GS Artiglio Admin')
    
    # Core models
    admin.add_view(MyModelView(User, db.session, category='Utenti'))
    admin.add_view(MyModelView(Fine, db.session, category='Multe'))
    admin.add_view(FineVoteView(FineVote, db.session, category='Multe'))
    admin.add_view(MyModelView(Event, db.session, category='Partite'))
    admin.add_view(VoteView(Vote, db.session, category='Partite'))
    admin.add_view(MyModelView(MatchStats, db.session, category='Partite'))
    admin.add_view(MyModelView(Attendance, db.session, category='Presenze'))
    admin.add_view(MyModelView(Training, db.session, category='Presenze'))
    admin.add_view(MyModelView(Turno, db.session, category='Turni'))

    # Classifica
    admin.add_view(MyModelView(ClassificaCampionato, db.session, category='Classifica'))
    admin.add_view(MyModelView(ClassificaInfo, db.session, category='Classifica'))

    # Notifiche
    admin.add_view(MyModelView(Notification, db.session, category='Notifiche'))
    admin.add_view(MyModelView(HiddenNotification, db.session, category='Notifiche'))
    admin.add_view(MyModelView(NotificationPreference, db.session, category='Notifiche'))
    admin.add_view(MyModelView(PushSubscription, db.session, category='Notifiche'))

    # Flappy Eagle
    admin.add_view(MyModelView(FlappyGameProfile, db.session, category='Floppy Eagle'))
    admin.add_view(MyModelView(FlappyMonthlyScore, db.session, category='Floppy Eagle'))

    # Achievements
    admin.add_view(MyModelView(Achievement, db.session, category='Badge'))
    admin.add_view(MyModelView(UserAchievement, db.session, category='Badge'))

    # Video
    admin.add_view(MyModelView(Video, db.session, endpoint='admin_video', category='Video'))
    admin.add_view(MyModelView(VideoLike, db.session, endpoint='admin_videolike', category='Video'))
    admin.add_view(MyModelView(VideoComment, db.session, endpoint='admin_videocomment', category='Video'))

    # Sistema
    admin.add_view(MyModelView(GlobalSettings, db.session, category='Sistema'))
    admin.add_view(MyModelView(CashTransaction, db.session, category='Cassa'))
    admin.add_view(MyModelView(AppRelease, db.session, category='Aggiornamenti'))
    admin.add_view(MyModelView(UserSeenRelease, db.session, category='Aggiornamenti'))
    admin.add_view(MyModelView(UserFeedback, db.session, category='Feedback'))
    
    return admin

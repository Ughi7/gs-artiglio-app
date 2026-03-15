from datetime import datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import ClassificaCampionato, ClassificaInfo, GlobalSettings, HiddenNotification, Notification, NotificationPreference, db
from app.utils.badge_service import process_previous_month_badges
from app.utils.dashboard_service import build_home_context
from app.utils.fine_report_service import mark_admin_fine_report_events_seen


dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/elimina_notifica/<int:notifica_id>', methods=['POST'])
@login_required
def elimina_notifica(notifica_id):
    notification = db.session.get(Notification, notifica_id)
    if notification:
        existing = HiddenNotification.query.filter_by(user_id=current_user.id, notification_id=notifica_id).first()
        if not existing:
            db.session.add(HiddenNotification(user_id=current_user.id, notification_id=notifica_id))
            db.session.commit()

    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/elimina_tutte_notifiche', methods=['POST'])
@login_required
def elimina_tutte_notifiche():
    week_ago = datetime.now() - timedelta(days=7)
    notifications = Notification.query.filter(Notification.data_creazione >= week_ago).all()

    for notification in notifications:
        existing = HiddenNotification.query.filter_by(user_id=current_user.id, notification_id=notification.id).first()
        if not existing:
            db.session.add(HiddenNotification(user_id=current_user.id, notification_id=notification.id))

    db.session.commit()
    flash('Bacheca svuotata.', 'success')
    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/salva_filtro_notifiche', methods=['POST'])
@login_required
def salva_filtro_notifiche():
    prefs = NotificationPreference.query.filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = NotificationPreference(user_id=current_user.id, push_enabled=True)
        db.session.add(prefs)

    prefs.show_mvp = request.form.get('show_mvp') == 'on'
    prefs.show_streak = request.form.get('show_streak') == 'on'
    prefs.show_turno = request.form.get('show_turno') == 'on'
    prefs.show_denuncia = request.form.get('show_denuncia') == 'on'
    prefs.show_flappy = request.form.get('show_flappy') == 'on'
    prefs.show_donatore = request.form.get('show_donatore') == 'on'
    prefs.show_certificato = request.form.get('show_certificato') == 'on'
    prefs.show_aggiornamento = request.form.get('show_aggiornamento') == 'on'

    if 'push_enabled' in request.form:
        prefs.push_enabled = request.form.get('push_enabled') == 'on'

    db.session.commit()
    flash('Preferenze notifiche aggiornate.', 'success')
    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/')
@login_required
def home():
    now = datetime.now()
    return render_template('index.html', **build_home_context(current_user, now=now))


@dashboard_bp.route('/api/dismiss-admin-fine-report', methods=['POST'])
@login_required
def dismiss_admin_fine_report():
    if not (current_user.is_admin or current_user.is_notaio):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

    dismissed_count = mark_admin_fine_report_events_seen(current_user)
    return jsonify({'success': True, 'dismissed': dismissed_count})


@dashboard_bp.route('/api/dismiss-vote-histories', methods=['POST'])
@login_required
def dismiss_vote_histories():
    from app.models import VoteHistory, UserSeenVoteHistory, db
    
    seen_ids = db.session.query(UserSeenVoteHistory.vote_history_id).filter_by(user_id=current_user.id)
    unseen_votes = VoteHistory.query.filter(VoteHistory.id.notin_(seen_ids)).all()
    
    for v in unseen_votes:
        seen_entry = UserSeenVoteHistory(user_id=current_user.id, vote_history_id=v.id)
        db.session.add(seen_entry)
        
    if unseen_votes:
        db.session.commit()
        
    return jsonify({'success': True, 'dismissed': len(unseen_votes)})


@dashboard_bp.route('/admin/assegna-badge-mensili', methods=['GET', 'POST'])
@login_required
def admin_assegna_badge_mensili():
    if not current_user.is_admin:
        flash('Accesso negato. Solo gli admin possono accedere a questa sezione.', 'danger')
        return redirect(url_for('dashboard.home'))

    risultati = []
    mese_assegnato = None
    anno_assegnato = None
    if request.method == 'POST':
        try:
            risultati, mese_assegnato, anno_assegnato = process_previous_month_badges()
            flash(f'Badge mensili processati per {mese_assegnato}/{anno_assegnato}!', 'success')
        except Exception as exc:
            flash(f'Errore durante l\'assegnazione: {str(exc)}', 'danger')

    return render_template('admin_badge.html', risultati=risultati, mese=mese_assegnato, anno=anno_assegnato)


@dashboard_bp.route('/update_rank', methods=['POST'])
@login_required
def update_rank():
    if not current_user.is_admin:
        return redirect(url_for('dashboard.home'))

    rank_setting = GlobalSettings.query.filter_by(key='rank').first()
    if not rank_setting:
        rank_setting = GlobalSettings(key='rank')
    rank_setting.value = request.form.get('rank')
    db.session.add(rank_setting)

    points_setting = GlobalSettings.query.filter_by(key='points').first()
    if not points_setting:
        points_setting = GlobalSettings(key='points')
    points_setting.value = request.form.get('points')
    db.session.add(points_setting)

    db.session.commit()
    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/salva_classifica', methods=['POST'])
@login_required
def salva_classifica():
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi per modificare la classifica!', 'danger')
        return redirect(url_for('dashboard.home'))

    info = ClassificaInfo.query.first()
    if not info:
        info = ClassificaInfo()
        db.session.add(info)

    giornata_attuale = request.form.get('giornata_attuale', type=int)
    giornate_totali = request.form.get('giornate_totali', type=int)
    if giornata_attuale is not None:
        info.giornata_attuale = giornata_attuale
    if giornate_totali is not None:
        info.giornate_totali = giornate_totali

    for team in ClassificaCampionato.query.all():
        points = request.form.get(f'punti_{team.id}', type=int)
        if points is not None:
            team.punti = points

    db.session.commit()

    for position, team in enumerate(ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all(), 1):
        team.posizione = position
    db.session.commit()

    flash('Classifica aggiornata!', 'success')
    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/aggiungi_squadra', methods=['POST'])
@login_required
def aggiungi_squadra():
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('dashboard.home'))

    team_name = request.form.get('nome_squadra')
    if not team_name:
        flash('Inserisci il nome della squadra!', 'danger')
        return redirect(url_for('dashboard.home'))

    db.session.add(ClassificaCampionato(
        posizione=ClassificaCampionato.query.count() + 1,
        squadra=team_name,
        punti=request.form.get('punti', type=int, default=0),
        is_artiglio=request.form.get('is_artiglio') == 'on',
    ))
    db.session.commit()

    for position, team in enumerate(ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all(), 1):
        team.posizione = position
    db.session.commit()

    flash(f'Squadra "{team_name}" aggiunta!', 'success')
    return redirect(url_for('dashboard.home'))


@dashboard_bp.route('/rimuovi_squadra/<int:squadra_id>', methods=['POST'])
@login_required
def rimuovi_squadra(squadra_id):
    if not (current_user.is_admin or current_user.is_scout):
        flash('Non hai i permessi!', 'danger')
        return redirect(url_for('dashboard.home'))

    team = db.session.get(ClassificaCampionato, squadra_id)
    if team:
        db.session.delete(team)
        db.session.commit()
        for position, ordered_team in enumerate(ClassificaCampionato.query.order_by(ClassificaCampionato.punti.desc()).all(), 1):
            ordered_team.posizione = position
        db.session.commit()
        flash('Squadra rimossa!', 'success')

    return redirect(url_for('dashboard.home'))
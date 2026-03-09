import os
from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory
from flask_login import login_required, current_user
from app.models import db, User, Event, Video, VideoLike, VideoComment
from app.utils.notifications import crea_notifica, get_nome_giocatore

video_bp = Blueprint('video', __name__)

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

@video_bp.route('/video')
@login_required
def video_list():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    videos = Video.query.order_by(Video.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    players = User.query.order_by(User.nome_completo).all()
    events = Event.query.order_by(Event.date_start.desc()).all()
    
    return render_template('video.html', videos=videos, players=players, events=events)

@video_bp.route('/video/upload', methods=['POST'])
@login_required
def video_upload():
    from flask import current_app
    
    if 'video_file' not in request.files:
        flash('Nessun file video selezionato.', 'danger')
        return redirect(url_for('video.video_list'))
    
    file = request.files['video_file']
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    protagonist_ids = request.form.getlist('protagonists')
    event_id = request.form.get('event_id')
    
    if file.filename == '' or not title:
        flash('File e Titolo sono obbligatori.', 'warning')
        return redirect(url_for('video.video_list'))
    
    if not allowed_video_file(file.filename):
        flash('Formato video non consentito. Usa: MP4, MOV, AVI, WEBM', 'danger')
        return redirect(url_for('video.video_list'))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{current_user.id}_{timestamp}.{file_ext}"
    filepath = os.path.join(current_app.config['VIDEO_UPLOAD_FOLDER'], filename)
    
    try:
        file.save(filepath)
        
        video = Video(
            user_id=current_user.id,
            title=title[:100],
            description=description[:500] if description else None,
            filename=filename,
            event_id=int(event_id) if event_id else None
        )
        
        if protagonist_ids:
            protagonists = User.query.filter(User.id.in_([int(pid) for pid in protagonist_ids])).all()
            video.protagonists = protagonists
        
        db.session.add(video)
        db.session.commit()
        
        if video.protagonists:
            nomi = ", ".join([get_nome_giocatore(p) for p in video.protagonists[:3]])
            if len(video.protagonists) > 3: nomi += f" e altri {len(video.protagonists) - 3}"
            msg = f"🎬 {get_nome_giocatore(current_user)} ha caricato un video: \"{title}\" con {nomi}!"
        else:
            msg = f"🎬 {get_nome_giocatore(current_user)} ha caricato un nuovo video: \"{title}\""
            
        crea_notifica('video_upload', msg, icon='🎬', send_push=True)
        flash('✅ Video caricato con successo!', 'success')
        
    except Exception as e:
        flash(f'❌ Errore durante il caricamento: {str(e)}', 'danger')
        if os.path.exists(filepath): os.remove(filepath)
    
    return redirect(url_for('video.video_list'))

@video_bp.route('/video/<int:video_id>/like', methods=['POST'])
@login_required
def video_like(video_id):
    video = Video.query.get_or_404(video_id)
    existing_like = VideoLike.query.filter_by(user_id=current_user.id, video_id=video_id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        new_like = VideoLike(user_id=current_user.id, video_id=video_id)
        db.session.add(new_like)
        liked = True
        
    db.session.commit()
    return {'success': True, 'liked': liked, 'like_count': video.like_count()}

@video_bp.route('/video/<int:video_id>/comment', methods=['POST'])
@login_required
def video_comment(video_id):
    text = request.form.get('comment_text', '').strip()
    reply_to_id = request.form.get('reply_to_id')
    
    if not text:
        flash('Il commento non può essere vuoto.', 'warning')
        return redirect(url_for('video.video_comments', video_id=video_id))
    
    comment = VideoComment(
        user_id=current_user.id, video_id=video_id,
        text=text[:500], reply_to_id=int(reply_to_id) if reply_to_id else None
    )
    db.session.add(comment)
    db.session.commit()
    flash('💬 Commento aggiunto!', 'success')
    return redirect(url_for('video.video_comments', video_id=video_id))

@video_bp.route('/video/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def video_comment_delete(comment_id):
    comment = VideoComment.query.get_or_404(comment_id)
    video_id = comment.video_id
    
    if comment.user_id != current_user.id and not current_user.is_admin:
        flash('❌ Non puoi eliminare questo commento.', 'danger')
    else:
        db.session.delete(comment)
        db.session.commit()
        flash('🗑️ Commento eliminato.', 'success')
        
    return redirect(url_for('video.video_comments', video_id=video_id))

@video_bp.route('/video/<int:video_id>/download')
@login_required
def video_download(video_id):
    from flask import current_app
    video = Video.query.get_or_404(video_id)
    return send_from_directory(
        current_app.config['VIDEO_UPLOAD_FOLDER'],
        video.filename,
        as_attachment=True,
        download_name=f"{video.title.replace(' ', '_')}.{video.filename.rsplit('.', 1)[1]}"
    )

@video_bp.route('/video/<int:video_id>/delete', methods=['POST'])
@login_required
def video_delete(video_id):
    from flask import current_app
    video = Video.query.get_or_404(video_id)
    
    if video.user_id != current_user.id and not current_user.is_admin:
        flash('❌ Non hai i permessi per eliminare questo video.', 'danger')
        return redirect(url_for('video.video_list'))
    
    try:
        filepath = os.path.join(current_app.config['VIDEO_UPLOAD_FOLDER'], video.filename)
        if os.path.exists(filepath): os.remove(filepath)
        db.session.delete(video)
        db.session.commit()
        flash('🗑️ Video eliminato.', 'success')
    except Exception as e:
        flash(f'❌ Errore: {str(e)}', 'danger')
    
    return redirect(url_for('video.video_list'))

@video_bp.route('/video/<int:video_id>/edit', methods=['GET', 'POST'])
@login_required
def video_edit(video_id):
    video = Video.query.get_or_404(video_id)
    
    if video.user_id != current_user.id and not current_user.is_admin:
        flash('❌ Non hai i permessi.', 'danger')
        return redirect(url_for('video.video_list'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        protagonist_ids = request.form.getlist('protagonists')
        event_id = request.form.get('event_id')
        
        if not title: return redirect(url_for('video.video_edit', video_id=video_id))
        
        video.title = title[:100]
        video.description = description[:500] if description else None
        video.event_id = int(event_id) if event_id else None
        
        if protagonist_ids:
            video.protagonists = User.query.filter(User.id.in_([int(pid) for pid in protagonist_ids])).all()
        else: video.protagonists = []
        
        db.session.commit()
        flash('✅ Video aggiornato!', 'success')
        return redirect(url_for('video.video_list'))
    
    players = User.query.order_by(User.nome_completo).all()
    events = Event.query.order_by(Event.date_start.desc()).all()
    return render_template('video_edit.html', video=video, players=players, events=events)

@video_bp.route('/video/<int:video_id>/comments')
@login_required
def video_comments(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template('video_comments.html', video=video)

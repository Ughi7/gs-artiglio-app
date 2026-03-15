from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import login_required, current_user
from app.models import db, Video, VideoComment
from app.utils.video_service import (
    VideoPermissionError,
    VideoValidationError,
    add_video_comment,
    build_video_list_context,
    create_video_from_upload,
    delete_video,
    delete_video_comment,
    toggle_video_like,
    update_video,
)

video_bp = Blueprint('video', __name__)

@video_bp.route('/video')
@login_required
def video_list():
    page = request.args.get('page', 1, type=int)
    return render_template('video.html', **build_video_list_context(page=page))

@video_bp.route('/video/upload', methods=['POST'])
@login_required
def video_upload():
    if 'video_file' not in request.files:
        flash('Nessun file video selezionato.', 'danger')
        return redirect(url_for('video.video_list'))

    try:
        create_video_from_upload(
            request.files['video_file'],
            current_user,
            request.form.get('title', ''),
            request.form.get('description', ''),
            request.form.getlist('protagonists'),
            request.form.get('event_id'),
            current_app.config['VIDEO_UPLOAD_FOLDER'],
        )
        flash('✅ Video caricato con successo!', 'success')
    except VideoValidationError as exc:
        flash(str(exc), 'danger' if 'Formato' in str(exc) or 'Nessun file' in str(exc) else 'warning')
    except Exception as exc:
        flash(f'❌ Errore durante il caricamento: {str(exc)}', 'danger')
    
    return redirect(url_for('video.video_list'))

@video_bp.route('/video/<int:video_id>/like', methods=['POST'])
@login_required
def video_like(video_id):
    video = db.get_or_404(Video, video_id)
    liked = toggle_video_like(video, current_user.id)
    return {'success': True, 'liked': liked, 'like_count': video.like_count()}

@video_bp.route('/video/<int:video_id>/comment', methods=['POST'])
@login_required
def video_comment(video_id):
    try:
        add_video_comment(video_id, current_user.id, request.form.get('comment_text', ''), request.form.get('reply_to_id'))
        flash('💬 Commento aggiunto!', 'success')
    except VideoValidationError as exc:
        flash(str(exc), 'warning')
        return redirect(url_for('video.video_comments', video_id=video_id))

    return redirect(url_for('video.video_comments', video_id=video_id))

@video_bp.route('/video/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def video_comment_delete(comment_id):
    comment = db.get_or_404(VideoComment, comment_id)
    video_id = comment.video_id

    try:
        delete_video_comment(comment, current_user.id, current_user.is_admin)
        flash('🗑️ Commento eliminato.', 'success')
    except VideoPermissionError as exc:
        flash(str(exc), 'danger')

    return redirect(url_for('video.video_comments', video_id=video_id))

@video_bp.route('/video/<int:video_id>/download')
@login_required
def video_download(video_id):
    video = db.get_or_404(Video, video_id)
    return send_from_directory(
        current_app.config['VIDEO_UPLOAD_FOLDER'],
        video.filename,
        as_attachment=True,
        download_name=f"{video.title.replace(' ', '_')}.{video.filename.rsplit('.', 1)[1]}"
    )

@video_bp.route('/video/<int:video_id>/delete', methods=['POST'])
@login_required
def video_delete(video_id):
    video = db.get_or_404(Video, video_id)

    try:
        delete_video(video, current_user.id, current_user.is_admin, current_app.config['VIDEO_UPLOAD_FOLDER'])
        flash('🗑️ Video eliminato.', 'success')
    except VideoPermissionError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('video.video_list'))
    except Exception as exc:
        flash(f'❌ Errore: {str(exc)}', 'danger')

    return redirect(url_for('video.video_list'))

@video_bp.route('/video/<int:video_id>/edit', methods=['GET', 'POST'])
@login_required
def video_edit(video_id):
    video = db.get_or_404(Video, video_id)

    if request.method == 'POST':
        try:
            update_video(
                video,
                current_user.id,
                current_user.is_admin,
                request.form.get('title', ''),
                request.form.get('description', ''),
                request.form.getlist('protagonists'),
                request.form.get('event_id'),
            )
            flash('✅ Video aggiornato!', 'success')
            return redirect(url_for('video.video_list'))
        except VideoValidationError:
            return redirect(url_for('video.video_edit', video_id=video_id))
        except VideoPermissionError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('video.video_list'))

    if video.user_id != current_user.id and not current_user.is_admin:
        flash('❌ Non hai i permessi.', 'danger')
        return redirect(url_for('video.video_list'))

    context = build_video_list_context(page=1)
    return render_template('video_edit.html', video=video, players=context['players'], events=context['events'])

@video_bp.route('/video/<int:video_id>/comments')
@login_required
def video_comments(video_id):
    video = db.get_or_404(Video, video_id)
    return render_template('video_comments.html', video=video)

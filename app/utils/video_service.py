import os
from datetime import datetime

from app.models import Event, User, Video, VideoComment, VideoLike, db
from app.utils.notifications import crea_notifica, get_nome_giocatore


ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm'}


class VideoValidationError(ValueError):
    pass


class VideoPermissionError(PermissionError):
    pass


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def build_video_list_context(page, per_page=12):
    videos = Video.query.order_by(Video.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    players = User.query.order_by(User.nome_completo).all()
    events = Event.query.order_by(Event.date_start.desc()).all()
    return {
        'videos': videos,
        'players': players,
        'events': events,
    }


def create_video_from_upload(file_storage, uploader, title, description, protagonist_ids, event_id, upload_folder, now=None, notifier=crea_notifica):
    title = (title or '').strip()
    description = (description or '').strip()

    if file_storage is None:
        raise VideoValidationError('Nessun file video selezionato.')
    if file_storage.filename == '' or not title:
        raise VideoValidationError('File e Titolo sono obbligatori.')
    if not allowed_video_file(file_storage.filename):
        raise VideoValidationError('Formato video non consentito. Usa: MP4, MOV, AVI, WEBM')

    now = now or datetime.now()
    file_ext = file_storage.filename.rsplit('.', 1)[1].lower()
    filename = f'{uploader.id}_{now.strftime("%Y%m%d_%H%M%S")}.{file_ext}'
    filepath = os.path.join(upload_folder, filename)

    file_storage.save(filepath)

    try:
        video = Video(
            user_id=uploader.id,
            title=title[:100],
            description=description[:500] if description else None,
            filename=filename,
            event_id=int(event_id) if event_id else None,
        )

        if protagonist_ids:
            protagonists = User.query.filter(User.id.in_([int(player_id) for player_id in protagonist_ids])).all()
            video.protagonists = protagonists

        db.session.add(video)
        db.session.commit()
    except Exception:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise

    notifier('video_upload', build_video_upload_message(video, uploader), icon='🎬', send_push=True)
    return video, filepath


def build_video_upload_message(video, uploader):
    if video.protagonists:
        names = ', '.join(get_nome_giocatore(player) for player in video.protagonists[:3])
        if len(video.protagonists) > 3:
            names += f' e altri {len(video.protagonists) - 3}'
        return f'🎬 {get_nome_giocatore(uploader)} ha caricato un video: "{video.title}" con {names}!'
    return f'🎬 {get_nome_giocatore(uploader)} ha caricato un nuovo video: "{video.title}"'


def toggle_video_like(video, user_id):
    existing_like = VideoLike.query.filter_by(user_id=user_id, video_id=video.id).first()
    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        db.session.add(VideoLike(user_id=user_id, video_id=video.id))
        liked = True

    db.session.commit()
    return liked


def add_video_comment(video_id, user_id, text, reply_to_id=None):
    text = (text or '').strip()
    if not text:
        raise VideoValidationError('Il commento non può essere vuoto.')

    comment = VideoComment(
        user_id=user_id,
        video_id=video_id,
        text=text[:500],
        reply_to_id=int(reply_to_id) if reply_to_id else None,
    )
    db.session.add(comment)
    db.session.commit()
    return comment


def delete_video_comment(comment, requester_id, is_admin=False):
    if comment.user_id != requester_id and not is_admin:
        raise VideoPermissionError('❌ Non puoi eliminare questo commento.')

    video_id = comment.video_id
    db.session.delete(comment)
    db.session.commit()
    return video_id


def delete_video(video, requester_id, is_admin, upload_folder):
    if video.user_id != requester_id and not is_admin:
        raise VideoPermissionError('❌ Non hai i permessi per eliminare questo video.')

    filepath = os.path.join(upload_folder, video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(video)
    db.session.commit()
    return filepath


def update_video(video, requester_id, is_admin, title, description, protagonist_ids, event_id):
    if video.user_id != requester_id and not is_admin:
        raise VideoPermissionError('❌ Non hai i permessi.')

    title = (title or '').strip()
    if not title:
        raise VideoValidationError('Titolo obbligatorio.')

    video.title = title[:100]
    video.description = description[:500].strip() if description and description.strip() else None
    video.event_id = int(event_id) if event_id else None

    if protagonist_ids:
        video.protagonists = User.query.filter(User.id.in_([int(player_id) for player_id in protagonist_ids])).all()
    else:
        video.protagonists = []

    db.session.commit()
    return video
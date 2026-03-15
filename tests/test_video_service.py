import io
import os
import sys
import tempfile
import unittest
from datetime import datetime

from werkzeug.datastructures import FileStorage


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ALLOW_SETUP_ROUTES', '0')


from app import bcrypt, create_app  # noqa: E402
from app.models import User, Video, VideoComment, db  # noqa: E402
from app.utils.video_service import (  # noqa: E402
    VideoPermissionError,
    VideoValidationError,
    add_video_comment,
    create_video_from_upload,
    delete_video,
    toggle_video_like,
    update_video,
)


class VideoServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-video-service-', suffix='.db', delete=False)
        cls.temp_db.close()
        os.environ['DATABASE_URL'] = f'sqlite:///{cls.temp_db.name}'
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        try:
            os.unlink(cls.temp_db.name)
        except FileNotFoundError:
            pass

    def setUp(self):
        self.temp_video_dir = tempfile.mkdtemp(prefix='gs-artiglio-videos-')
        self.app.config['VIDEO_UPLOAD_FOLDER'] = self.temp_video_dir

        with self.app.app_context():
            db.drop_all()
            db.create_all()
            uploader = User(
                username='video_uploader',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Video Uploader',
                soprannome='Uploader',
                ruolo_volley='Schiacciatore',
            )
            other = User(
                username='video_other',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Video Other',
                soprannome='Other',
                ruolo_volley='Libero',
            )
            admin = User(
                username='video_admin',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Video Admin',
                soprannome='Admin',
                ruolo_volley='Allenatore',
                is_admin=True,
            )
            db.session.add_all([uploader, other, admin])
            db.session.commit()
            self.uploader_id = uploader.id
            self.other_id = other.id
            self.admin_id = admin.id

    def tearDown(self):
        for root, _, files in os.walk(self.temp_video_dir, topdown=False):
            for file_name in files:
                os.remove(os.path.join(root, file_name))
            os.rmdir(root)

    def test_create_video_from_upload_persists_file_and_record(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            uploader = db.session.get(User, self.uploader_id)
            file_storage = FileStorage(stream=io.BytesIO(b'video-bytes'), filename='service-video.mp4')

            video, path = create_video_from_upload(
                file_storage,
                uploader,
                'Service Video',
                'Descrizione di test',
                [],
                None,
                self.temp_video_dir,
                now=datetime(2026, 3, 12, 12, 0),
                notifier=notifier,
            )

            self.assertEqual(video.title, 'Service Video')
            self.assertTrue(os.path.exists(path))
            self.assertEqual(Video.query.count(), 1)
            self.assertEqual(len(notifications), 1)

    def test_toggle_like_and_comment_creation(self):
        with self.app.app_context():
            uploader = db.session.get(User, self.uploader_id)
            file_storage = FileStorage(stream=io.BytesIO(b'video-bytes'), filename='like-comment.mp4')
            video, _ = create_video_from_upload(file_storage, uploader, 'Like Me', '', [], None, self.temp_video_dir, notifier=lambda *args, **kwargs: None)

            liked = toggle_video_like(video, self.other_id)
            self.assertTrue(liked)
            self.assertEqual(video.like_count(), 1)

            unliked = toggle_video_like(video, self.other_id)
            self.assertFalse(unliked)
            self.assertEqual(video.like_count(), 0)

            comment = add_video_comment(video.id, self.other_id, 'Commento service')
            self.assertEqual(comment.text, 'Commento service')
            self.assertEqual(VideoComment.query.count(), 1)

    def test_delete_and_update_video_enforce_permissions(self):
        with self.app.app_context():
            uploader = db.session.get(User, self.uploader_id)
            file_storage = FileStorage(stream=io.BytesIO(b'video-bytes'), filename='delete-update.mp4')
            video, path = create_video_from_upload(file_storage, uploader, 'Original', '', [], None, self.temp_video_dir, notifier=lambda *args, **kwargs: None)

            with self.assertRaises(VideoPermissionError):
                update_video(video, self.other_id, False, 'Hacked', '', [], None)

            updated = update_video(video, self.uploader_id, False, 'Updated Title', 'Nuova descrizione', [], None)
            self.assertEqual(updated.title, 'Updated Title')

            with self.assertRaises(VideoPermissionError):
                delete_video(video, self.other_id, False, self.temp_video_dir)

            delete_video(video, self.admin_id, True, self.temp_video_dir)
            self.assertIsNone(db.session.get(Video, video.id))
            self.assertFalse(os.path.exists(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date, datetime, timedelta


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ALLOW_SETUP_ROUTES', '0')


from app import bcrypt, create_app  # noqa: E402
from app.models import (  # noqa: E402
    AdminFineReportEvent,
    AppRelease,
    Event,
    Fine,
    FlappyGameProfile,
    NotificationPreference,
    PushSubscription,
    Turno,
    User,
    UserFeedback,
    UserSeenAdminFineReportEvent,
    UserSeenRelease,
    Video,
    VideoComment,
    db,
)


CSRF_META_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)">')


class SmokeCriticalFlowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-smoke-', suffix='.db', delete=False)
        cls.temp_db.close()
        os.environ['DATABASE_URL'] = f"sqlite:///{cls.temp_db.name}"

        cls.app = create_app()
        cls.app.config.update(TESTING=True)

        with cls.app.app_context():
            db.drop_all()
            db.create_all()

            admin = User(
                username='admin_test',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Admin Test',
                soprannome='Admin',
                ruolo_volley='Allenatore',
                is_admin=True,
            )
            player = User(
                username='player_test',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Player Test',
                soprannome='Player',
                ruolo_volley='Schiacciatore',
            )
            notaio = User(
                username='notaio_test',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Notaio Test',
                soprannome='Notaio',
                ruolo_volley='Libero',
                is_notaio=True,
            )
            skin_player = User(
                username='skin_test',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Skin Test',
                soprannome='Skin',
                ruolo_volley='Centrale',
            )
            release = AppRelease(version='9.9.9', title='Smoke Release', notes='Smoke release notes', is_major=False)
            feedback = UserFeedback(user=player, feedback_type='bug', title='Smoke bug', description='Smoke description')

            db.session.add_all([admin, player, notaio, skin_player, release, feedback])
            db.session.commit()

            cls.admin_id = admin.id
            cls.player_id = player.id
            cls.notaio_id = notaio.id
            cls.skin_player_id = skin_player.id
            cls.release_id = release.id
            cls.feedback_id = feedback.id

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
        self.client = self.app.test_client()

    def extract_csrf_token(self, response):
        html = response.get_data(as_text=True)
        match = CSRF_META_RE.search(html)
        self.assertIsNotNone(match, 'CSRF meta token non trovato nella pagina renderizzata')
        return match.group(1)

    def create_user(self, username, password, nome_completo):
        """Create a user directly in the database for testing"""
        with self.app.app_context():
            existing = User.query.filter_by(username=username).first()
            if existing:
                return existing
            user = User(
                username=username,
                password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
                nome_completo=nome_completo,
            )
            db.session.add(user)
            db.session.commit()
            return user

    def login(self, username, password):
        login_page = self.client.get('/login')
        self.assertEqual(login_page.status_code, 200)
        csrf_token = self.extract_csrf_token(login_page)

        response = self.client.post(
            '/login',
            data={
                'username': username,
                'password': password,
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response.headers['Location'])

    def get_csrf_from_page(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        return self.extract_csrf_token(response)

    def json_post(self, path, payload, csrf_token):
        return self.client.post(
            path,
            json=payload,
            headers={'X-CSRFToken': csrf_token},
        )

    @contextmanager
    def app_context(self):
        with self.app.app_context():
            yield

    def test_login_flow(self):
        self.login('player_test', 'Password123!')

    def test_push_subscription_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')

        subscribe_payload = {
            'endpoint': 'https://example.push.test/subscription/1',
            'keys': {
                'p256dh': 'test-p256dh-key',
                'auth': 'test-auth-key',
            },
        }

        subscribe_response = self.json_post('/api/push/subscribe', subscribe_payload, csrf_token)
        self.assertEqual(subscribe_response.status_code, 200)
        self.assertTrue(subscribe_response.get_json()['success'])

        with self.app_context():
            self.assertIsNotNone(PushSubscription.query.filter_by(user_id=self.player_id).first())
            prefs = NotificationPreference.query.filter_by(user_id=self.player_id).first()
            self.assertIsNotNone(prefs)
            self.assertTrue(prefs.push_enabled)

        unsubscribe_response = self.json_post(
            '/api/push/unsubscribe',
            {'endpoint': subscribe_payload['endpoint']},
            csrf_token,
        )
        self.assertEqual(unsubscribe_response.status_code, 200)
        self.assertTrue(unsubscribe_response.get_json()['success'])

        with self.app_context():
            self.assertIsNone(PushSubscription.query.filter_by(endpoint=subscribe_payload['endpoint']).first())

    def test_profile_update_and_password_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/profilo')

        profile_response = self.client.get('/profilo')
        self.assertEqual(profile_response.status_code, 200)
        self.assertIn('Player Test', profile_response.get_data(as_text=True))

        save_bio_response = self.client.post(
            '/salva_bio',
            data={
                'bio': 'Schiacciatore da smoke test',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(save_bio_response.status_code, 302)

        with self.app_context():
            player = db.session.get(User, self.player_id)
            self.assertEqual(player.bio, 'Schiacciatore da smoke test')

        change_password_response = self.client.post(
            '/change_password',
            data={
                'current_password': 'Password123!',
                'new_password': 'Password456!',
                'confirm_password': 'Password456!',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(change_password_response.status_code, 302)

        self.client.get('/logout')
        self.login('player_test', 'Password456!')

        with self.app_context():
            player = db.session.get(User, self.player_id)
            player.password_hash = bcrypt.generate_password_hash('Password123!').decode('utf-8')
            db.session.commit()

    def test_medical_certificate_upload_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/profilo')

        upload_response = self.client.post(
            '/upload_certificato',
            data={
                'certificato_file': (io.BytesIO(b'%PDF-1.4\n% smoke certificate\n'), 'smoke-cert.pdf'),
                'data_scadenza': '2026-12-31',
                'csrf_token': csrf_token,
            },
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        self.assertEqual(upload_response.status_code, 302)

        with self.app_context():
            player = db.session.get(User, self.player_id)
            self.assertIsNotNone(player.medical_file)
            self.assertEqual(player.medical_expiry.isoformat(), '2026-12-31')
            uploaded_file = os.path.join(self.app.config['UPLOAD_FOLDER'], player.medical_file)
            self.assertTrue(os.path.exists(uploaded_file))

            os.remove(uploaded_file)
            player.medical_file = None
            player.medical_expiry = None
            db.session.commit()

    def test_multe_validation_and_payment_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        with self.app_context():
            initial_fine_count = Fine.query.count()

        invalid_add = self.client.post(
            '/aggiungi_multa',
            data={
                'user_id': str(self.player_id),
                'amount': 'abc',
                'reason': 'Ritardo',
                'fine_date': '2026-03-08',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(invalid_add.status_code, 302)

        with self.app_context():
            self.assertEqual(Fine.query.count(), initial_fine_count)

        valid_add = self.client.post(
            '/aggiungi_multa',
            data={
                'user_id': str(self.player_id),
                'amount': '2.50',
                'reason': 'Ritardo allenamento',
                'fine_date': '2026-03-08',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(valid_add.status_code, 302)

        with self.app_context():
            self.assertEqual(Fine.query.count(), initial_fine_count + 1)
            fine = Fine.query.order_by(Fine.id.desc()).first()
            self.assertEqual(fine.amount, 2.5)
            self.assertEqual(fine.reason, 'Ritardo allenamento')
            fine_id = fine.id

        invalid_payment = self.client.post(
            f'/paga_multa/{fine_id}',
            data={
                'metodo': 'bonifico',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(invalid_payment.status_code, 302)

        valid_payment = self.client.post(
            f'/paga_multa/{fine_id}',
            data={
                'metodo': 'paypal',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(valid_payment.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertTrue(fine.paid)
            self.assertEqual(fine.payment_method, 'paypal')

    def test_multa_modify_and_delete_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        create_response = self.client.post(
            '/aggiungi_multa',
            data={
                'user_id': str(self.player_id),
                'amount': '4.00',
                'reason': 'Smoke edit/delete fine',
                'fine_date': '2026-03-10',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(create_response.status_code, 302)

        with self.app_context():
            fine = Fine.query.order_by(Fine.id.desc()).first()
            fine_id = fine.id

        edit_response = self.client.post(
            '/modifica_multa',
            data={
                'fine_id': str(fine_id),
                'amount': '7.50',
                'reason': 'Fine aggiornata da smoke',
                'paid': 'on',
                'payment_method': 'contanti',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(edit_response.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertEqual(fine.amount, 7.5)
            self.assertEqual(fine.reason, 'Fine aggiornata da smoke')
            self.assertTrue(fine.paid)
            self.assertEqual(fine.payment_method, 'contanti')

        delete_response = self.client.get(f'/elimina_multa/{fine_id}', follow_redirects=False)
        self.assertEqual(delete_response.status_code, 302)

        with self.app_context():
            self.assertIsNone(db.session.get(Fine, fine_id))

    def test_stats_pages_render_populated_payloads(self):
        with self.app_context():
            fine = Fine(
                user_id=self.player_id,
                amount=6.5,
                reason='Smoke stats fine',
                date=datetime(2026, 3, 8, 20, 0),
                paid=True,
                payment_method='contanti',
            )
            match = Event(
                opponent_name='Stats Opponent',
                date_start=datetime(2026, 3, 9, 21, 0),
                is_home=True,
                location='PalaArtiglio',
                sets_us=3,
                sets_them=1,
                is_friendly=False,
            )
            db.session.add_all([fine, match])
            db.session.commit()

        self.login('admin_test', 'Password123!')

        multe_stats_response = self.client.get('/stats_multe')
        self.assertEqual(multe_stats_response.status_code, 200)
        multe_html = multe_stats_response.get_data(as_text=True)
        self.assertIn('window.__statsMulteData', multe_html)
        self.assertIn('2026-03', multe_html)
        self.assertIn('Player', multe_html)

        partite_stats_response = self.client.get('/stats_partite')
        self.assertEqual(partite_stats_response.status_code, 200)
        partite_html = partite_stats_response.get_data(as_text=True)
        self.assertIn('window.__statsPartiteData', partite_html)
        self.assertIn('09/03/26', partite_html)
        self.assertIn('3', partite_html)

    def test_denuncia_voting_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/rosa')

        denuncia_response = self.client.post(
            '/denuncia_infrazione',
            data={
                'user_id': str(self.skin_player_id),
                'data_infrazione': '2026-03-11',
                'motivazione': 'Ritardo in palestra',
                'importo': '2',
                'note': 'Entrato dopo il briefing',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(denuncia_response.status_code, 302)

        with self.app_context():
            fine = Fine.query.filter_by(
                denunciante_id=self.player_id,
                note='Entrato dopo il briefing',
            ).order_by(Fine.id.desc()).first()
            self.assertIsNotNone(fine)
            self.assertTrue(fine.pending_approval)
            fine_id = fine.id

        self.client.get('/logout')
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        start_vote_response = self.client.post(
            f'/avvia_votazione/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(start_vote_response.status_code, 302)

        vote_response = self.client.post(
            f'/vota_denuncia/{fine_id}',
            data={
                'vote': '1',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(vote_response.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertTrue(fine.voting_active)
            self.assertEqual(len(fine.votes), 1)

        self.client.get('/logout')
        self.login('skin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        blocked_vote_response = self.client.post(
            f'/vota_denuncia/{fine_id}',
            data={
                'vote': '1',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(blocked_vote_response.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertEqual(len(fine.votes), 1)

    def test_denuncia_expired_vote_with_quorum_is_approved(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/rosa')

        denuncia_response = self.client.post(
            '/denuncia_infrazione',
            data={
                'user_id': str(self.skin_player_id),
                'data_infrazione': '2026-03-12',
                'motivazione': 'Test quorum raggiunto',
                'importo': '2',
                'note': 'Smoke quorum reached',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(denuncia_response.status_code, 302)

        with self.app_context():
            fine = Fine.query.order_by(Fine.id.desc()).first()
            fine_id = fine.id

        self.client.get('/logout')
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        start_vote_response = self.client.post(
            f'/avvia_votazione/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(start_vote_response.status_code, 302)

        admin_vote = self.client.post(
            f'/vota_denuncia/{fine_id}',
            data={'vote': '1', 'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(admin_vote.status_code, 302)

        self.client.get('/logout')
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')
        second_vote = self.client.post(
            f'/vota_denuncia/{fine_id}',
            data={'vote': '1', 'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(second_vote.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            fine.voting_end = datetime.now() - timedelta(minutes=1)
            db.session.commit()

        # Trigger automatic vote closure through fines page context build
        self.client.get('/multe')

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertIsNotNone(fine)
            self.assertFalse(fine.voting_active)
            self.assertFalse(fine.pending_approval)

    def test_denuncia_expired_vote_without_quorum_is_removed(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/rosa')

        denuncia_response = self.client.post(
            '/denuncia_infrazione',
            data={
                'user_id': str(self.skin_player_id),
                'data_infrazione': '2026-03-12',
                'motivazione': 'Test quorum non raggiunto',
                'importo': '2',
                'note': 'Smoke quorum missing',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(denuncia_response.status_code, 302)

        with self.app_context():
            fine = Fine.query.order_by(Fine.id.desc()).first()
            fine_id = fine.id

        self.client.get('/logout')
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        start_vote_response = self.client.post(
            f'/avvia_votazione/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(start_vote_response.status_code, 302)

        # Single vote is not enough to reach quorum in default smoke setup
        admin_vote = self.client.post(
            f'/vota_denuncia/{fine_id}',
            data={'vote': '1', 'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(admin_vote.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            fine.voting_end = datetime.now() - timedelta(minutes=1)
            db.session.commit()

        self.client.get('/multe')

        with self.app_context():
            self.assertIsNone(db.session.get(Fine, fine_id))

    def test_denuncia_daily_limit_blocks_fourth_submission(self):
        self.login('skin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/rosa')

        with self.app_context():
            initial_count = Fine.query.filter_by(denunciante_id=self.skin_player_id).count()

        for day_offset in ['2026-02-01', '2026-02-02', '2026-02-03']:
            response = self.client.post(
                '/denuncia_infrazione',
                data={
                    'user_id': str(self.player_id),
                    'data_infrazione': day_offset,
                    'motivazione': 'Smoke limite giornaliero',
                    'importo': '2',
                    'note': 'Denuncia retrodatata',
                    'csrf_token': csrf_token,
                },
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 302)

        blocked_response = self.client.post(
            '/denuncia_infrazione',
            data={
                'user_id': str(self.player_id),
                'data_infrazione': '2026-01-01',
                'motivazione': 'Quarta denuncia',
                'importo': '2',
                'note': 'Deve essere bloccata',
                'csrf_token': csrf_token,
            },
            follow_redirects=True,
        )
        self.assertEqual(blocked_response.status_code, 200)
        self.assertIn('Hai raggiunto il limite massimo di 3 denunce per oggi!', blocked_response.get_data(as_text=True))

        with self.app_context():
            final_count = Fine.query.filter_by(denunciante_id=self.skin_player_id).count()
            self.assertEqual(final_count, initial_count + 3)

    def test_feedback_and_release_json_validation(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/admin/feedback')

        invalid_feedback_update = self.json_post(
            f'/admin/feedback/{self.feedback_id}/update',
            {'status': 'unsupported'},
            csrf_token,
        )
        self.assertEqual(invalid_feedback_update.status_code, 400)
        self.assertFalse(invalid_feedback_update.get_json()['success'])

        valid_feedback_update = self.json_post(
            f'/admin/feedback/{self.feedback_id}/update',
            {'status': 'resolved', 'admin_response': 'Gestito via smoke test'},
            csrf_token,
        )
        self.assertEqual(valid_feedback_update.status_code, 200)
        self.assertTrue(valid_feedback_update.get_json()['success'])

        with self.app_context():
            feedback = db.session.get(UserFeedback, self.feedback_id)
            self.assertEqual(feedback.status, 'resolved')
            self.assertEqual(feedback.admin_response, 'Gestito via smoke test')

        self.client.get('/logout')
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')

        dismiss_response = self.json_post(
            '/api/dismiss-release',
            {'release_id': self.release_id},
            csrf_token,
        )
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertTrue(dismiss_response.get_json()['success'])

        with self.app_context():
            seen = UserSeenRelease.query.filter_by(user_id=self.player_id, release_id=self.release_id).first()
            self.assertIsNotNone(seen)

    def test_admin_feedback_delete_and_release_crud_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')

        create_release_response = self.client.post(
            '/admin/aggiornamenti/nuovo',
            data={
                'version': '10.0.0',
                'title': 'Release integrazione',
                'notes': 'Contenuto release creato da smoke test',
                'is_major': 'on',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(create_release_response.status_code, 302)

        with self.app_context():
            release = AppRelease.query.filter_by(version='10.0.0').first()
            self.assertIsNotNone(release)
            release_id = release.id

            media_filename = 'feedback-delete-smoke.txt'
            media_path = os.path.join(self.app.config['FEEDBACK_UPLOAD_FOLDER'], media_filename)
            with open(media_path, 'w', encoding='utf-8') as file_handle:
                file_handle.write('smoke feedback file')

            feedback = UserFeedback(
                user_id=self.player_id,
                feedback_type='proposal',
                title='Feedback da eliminare',
                description='Contenuto eliminabile',
                media_path=f'feedback/{media_filename}',
            )
            db.session.add(feedback)
            db.session.commit()
            feedback_id = feedback.id

        update_release_response = self.json_post(
            f'/admin/aggiornamenti/{release_id}/update',
            {
                'title': 'Release integrazione aggiornata',
                'notes': 'Note aggiornate via smoke test',
                'is_major': False,
            },
            csrf_token,
        )
        self.assertEqual(update_release_response.status_code, 200)
        self.assertTrue(update_release_response.get_json()['success'])

        delete_feedback_response = self.client.post(
            f'/admin/feedback/{feedback_id}/delete',
            headers={'X-CSRFToken': csrf_token},
        )
        self.assertEqual(delete_feedback_response.status_code, 200)
        self.assertTrue(delete_feedback_response.get_json()['success'])

        delete_release_response = self.client.post(
            f'/admin/aggiornamenti/{release_id}/delete',
            headers={'X-CSRFToken': csrf_token},
        )
        self.assertEqual(delete_release_response.status_code, 200)
        self.assertTrue(delete_release_response.get_json()['success'])

        with self.app_context():
            self.assertIsNone(db.session.get(AppRelease, release_id))
            self.assertIsNone(db.session.get(UserFeedback, feedback_id))
            self.assertFalse(os.path.exists(media_path))

    def test_fines_admin_moderation_flow(self):
        self.create_user('moderation_reporter', 'Moderation123!', 'Moderation Reporter')
        self.login('moderation_reporter', 'Moderation123!')
        csrf_token = self.get_csrf_from_page('/rosa')

        denuncia_response = self.client.post(
            '/denuncia_infrazione',
            data={
                'user_id': str(self.skin_player_id),
                'data_infrazione': '2026-03-10',
                'motivazione': 'Assenza briefing',
                'importo': '2',
                'note': 'Moderation smoke',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(denuncia_response.status_code, 302)

        with self.app_context():
            reporter = User.query.filter_by(username='moderation_reporter').first()
            fine = Fine.query.filter_by(
                denunciante_id=reporter.id,
                note='Moderation smoke',
            ).order_by(Fine.id.desc()).first()
            self.assertIsNotNone(fine)
            self.assertTrue(fine.pending_approval)
            fine_id = fine.id

        self.client.get('/logout')
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        start_vote_response = self.client.post(
            f'/avvia_votazione/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(start_vote_response.status_code, 302)

        exclusions_response = self.client.post(
            f'/modifica_impostazioni_votazione/{fine_id}',
            data={
                'excluded_users': str(self.notaio_id),
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(exclusions_response.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertTrue(fine.voting_active)
            self.assertIn(str(self.notaio_id), fine.excluded_voters)

        cancel_vote_response = self.client.post(
            f'/elimina_votazione/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(cancel_vote_response.status_code, 302)

        with self.app_context():
            fine = db.session.get(Fine, fine_id)
            self.assertFalse(fine.voting_active)
            self.assertTrue(fine.pending_approval)

        reject_response = self.client.post(
            f'/rifiuta_denuncia/{fine_id}',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(reject_response.status_code, 302)

        with self.app_context():
            self.assertIsNone(db.session.get(Fine, fine_id))

    def test_calendar_turno_management_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/calendario')

        assign_response = self.client.post(
            '/gestisci_turno',
            data={
                'date': '2026-03-17',
                'tipo': 'birra',
                'action': 'assign',
                'user_ids': str(self.player_id),
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(assign_response.status_code, 302)

        with self.app_context():
            turno = Turno.query.filter_by(tipo='birra', date=date(2026, 3, 17)).first()
            self.assertIsNotNone(turno)
            self.assertFalse(turno.is_cancelled)
            self.assertEqual([user.id for user in turno.incaricati], [self.player_id])

        cancel_response = self.client.post(
            '/gestisci_turno',
            data={
                'date': '2026-03-17',
                'tipo': 'birra',
                'action': 'cancel',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(cancel_response.status_code, 302)

        with self.app_context():
            turno = Turno.query.filter_by(tipo='birra', date=date(2026, 3, 17)).first()
            self.assertIsNotNone(turno)
            self.assertTrue(turno.is_cancelled)
            self.assertEqual(len(turno.incaricati), 0)
            db.session.delete(turno)
            db.session.commit()

    def test_admin_skin_counter_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/admin/assegna-skin')

        page_response = self.client.get('/admin/assegna-skin')
        self.assertEqual(page_response.status_code, 200)
        self.assertIn('Skin', page_response.get_data(as_text=True))

        increment_response = self.client.post(
            '/admin/assegna-skin',
            data={
                'action': 'increment_counter',
                'skin_id': 'ladybug',
                'user_id': str(self.skin_player_id),
                'note': 'Smoke bug report',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(increment_response.status_code, 200)

        with self.app_context():
            profile = FlappyGameProfile.query.filter_by(user_id=self.skin_player_id).first()
            self.assertIsNotNone(profile)
            self.assertEqual(profile.bug_report_count, 1)
            self.assertIn('Smoke bug report', profile.bug_report_notes)
            profile.bug_report_count = 0
            profile.bug_report_notes = '[]'
            db.session.commit()

    def test_video_upload_like_comment_and_delete_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/video')

        upload_response = self.client.post(
            '/video/upload',
            data={
                'title': 'Smoke Video',
                'description': 'Upload video smoke test',
                'csrf_token': csrf_token,
                'video_file': (io.BytesIO(b'fake video bytes'), 'smoke-video.mp4'),
            },
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        self.assertEqual(upload_response.status_code, 302)

        with self.app_context():
            video = Video.query.order_by(Video.id.desc()).first()
            self.assertIsNotNone(video)
            self.assertEqual(video.title, 'Smoke Video')
            self.assertEqual(video.user_id, self.player_id)
            video_id = video.id
            video_path = os.path.join(self.app.config['VIDEO_UPLOAD_FOLDER'], video.filename)
            self.assertTrue(os.path.exists(video_path))

        like_response = self.client.post(
            f'/video/{video_id}/like',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(like_response.status_code, 200)
        self.assertTrue(like_response.get_json()['liked'])

        comment_response = self.client.post(
            f'/video/{video_id}/comment',
            data={
                'comment_text': 'Smoke comment',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(comment_response.status_code, 302)

        comments_page = self.client.get(f'/video/{video_id}/comments')
        self.assertEqual(comments_page.status_code, 200)
        self.assertIn('Smoke comment', comments_page.get_data(as_text=True))

        with self.app_context():
            comment = VideoComment.query.filter_by(video_id=video_id, user_id=self.player_id).first()
            self.assertIsNotNone(comment)
            comment_id = comment.id

        delete_comment_response = self.client.post(
            f'/video/comment/{comment_id}/delete',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(delete_comment_response.status_code, 302)

        delete_video_response = self.client.post(
            f'/video/{video_id}/delete',
            data={'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(delete_video_response.status_code, 302)

        with self.app_context():
            self.assertIsNone(db.session.get(Video, video_id))
            self.assertIsNone(db.session.get(VideoComment, comment_id))
            self.assertFalse(os.path.exists(video_path))

    def test_admin_fine_report_popup_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

        with self.app_context():
            initial_events = AdminFineReportEvent.query.count()
            initial_seen_admin = UserSeenAdminFineReportEvent.query.filter_by(user_id=self.admin_id).count()

        add_response = self.client.post(
            '/aggiungi_multa',
            data={
                'user_id': str(self.player_id),
                'amount': '3.75',
                'reason': 'Smoke report fine',
                'fine_date': '2026-03-09',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(add_response.status_code, 302)

        with self.app_context():
            fine = Fine.query.order_by(Fine.id.desc()).first()
            self.assertIsNotNone(fine)
            self.assertGreaterEqual(AdminFineReportEvent.query.count(), initial_events + 1)

        pay_response = self.client.post(
            f'/paga_multa/{fine.id}',
            data={
                'metodo': 'contanti',
                'csrf_token': csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(pay_response.status_code, 302)

        with self.app_context():
            self.assertGreaterEqual(AdminFineReportEvent.query.count(), initial_events + 2)

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        home_html = home_response.get_data(as_text=True)
        self.assertIn('adminFineReportModal', home_html)

        home_csrf = self.extract_csrf_token(home_response)
        dismiss_response = self.json_post('/api/dismiss-admin-fine-report', {}, home_csrf)
        self.assertEqual(dismiss_response.status_code, 200)
        self.assertTrue(dismiss_response.get_json()['success'])

        with self.app_context():
            self.assertGreaterEqual(
                UserSeenAdminFineReportEvent.query.filter_by(user_id=self.admin_id).count(),
                initial_seen_admin + 2,
            )

        self.client.get('/logout')
        self.login('player_test', 'Password123!')
        player_home = self.client.get('/')
        self.assertNotIn('id="adminFineReportModal"', player_home.get_data(as_text=True))

        self.client.get('/logout')
        self.login('notaio_test', 'Password123!')
        notaio_home = self.client.get('/')
        self.assertIn('id="adminFineReportModal"', notaio_home.get_data(as_text=True))

    def test_game_json_validation_and_progress_flow(self):
        self.login('player_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')

        invalid_coins = self.json_post('/api/flappy/save_coins', {'coins': -5}, csrf_token)
        self.assertEqual(invalid_coins.status_code, 400)
        self.assertFalse(invalid_coins.get_json()['success'])

        valid_coins = self.json_post('/api/flappy/save_coins', {'coins': 7}, csrf_token)
        self.assertEqual(valid_coins.status_code, 200)
        self.assertTrue(valid_coins.get_json()['success'])

        save_progress = self.json_post('/api/flappy/save_progress', {'score': 2500, 'level': 3}, csrf_token)
        self.assertEqual(save_progress.status_code, 200)
        self.assertTrue(save_progress.get_json()['success'])

        save_score = self.json_post('/api/save_score', {'score': 2500}, csrf_token)
        self.assertEqual(save_score.status_code, 200)
        self.assertEqual(save_score.get_json()['high_score'], 2500)

        with self.app_context():
            profile = FlappyGameProfile.query.filter_by(user_id=self.player_id).first()
            self.assertIsNotNone(profile)
            self.assertEqual(profile.coins, 7)
            self.assertEqual(profile.games_over_2000, 1)


    def test_flappy_save_with_high_scores(self):
        """Regression: Verify high scores (>2000) save correctly with robust transactioning"""
        # Use dedicated user for this test to avoid cross-test pollution
        self.create_user('high_score_tester', 'HighScore123!', 'Alto Punteggiatore')
        self.login('high_score_tester', 'HighScore123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')
        
        # Ensure profile exists
        with self.app_context():
            user = User.query.filter_by(username='high_score_tester').first()
            profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
            if not profile:
                profile = FlappyGameProfile(user_id=user.id)
                db.session.add(profile)
                db.session.commit()
        
        # Test multiple high scores to ensure they all persist
        test_scores = [2000, 2500, 3000, 5000, 7500]
        for score in test_scores:
            save_resp = self.json_post('/api/flappy/save_progress', 
                {'score': score, 'level': 5, 'coins': 10}, csrf_token)
            self.assertEqual(save_resp.status_code, 200)
            self.assertTrue(save_resp.get_json()['success'])
            self.assertEqual(save_resp.get_json()['high_score'], score)
        
        # Verify last high score persisted in database
        with self.app_context():
            user = User.query.filter_by(username='high_score_tester').first()
            self.assertEqual(user.flappy_high_score, 7500)
            profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
            # 5 games over 2000
            self.assertEqual(profile.games_over_2000, 5)

    def test_flappy_json_corruption_resilience(self):
        """Regression: Verify save_progress doesn't crash on corrupted JSON, and handles gracefully"""
        # Use dedicated user  
        self.create_user('json_corruption_tester', 'JsonTest123!', 'JSON Tester')
        self.login('json_corruption_tester', 'JsonTest123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')
        
        # Ensure profile exists and corrupt it
        with self.app_context():
            user = User.query.filter_by(username='json_corruption_tester').first()
            user_id = user.id
            profile = FlappyGameProfile.query.filter_by(user_id=user_id).first()
            if not profile:
                profile = FlappyGameProfile(user_id=user_id)
                db.session.add(profile)
            # Corrupt the unlocked_skins JSON (always read regardless of time)
            profile.unlocked_skins = "invalid json ["
            db.session.commit()
        
        # Save progress should still work despite corrupted unlocked_skins JSON
        save_resp = self.json_post('/api/flappy/save_progress', 
            {'score': 2000, 'level': 3}, csrf_token)
        self.assertEqual(save_resp.status_code, 200)
        self.assertTrue(save_resp.get_json()['success'])
        
        # Verify data was auto-recovered
        with self.app_context():
            profile = FlappyGameProfile.query.filter_by(user_id=user_id).first()
            # Should have fixed the corrupted JSON
            try:
                unlocked = json.loads(profile.unlocked_skins)
                self.assertIsInstance(unlocked, list)
                # Should have reset to default
                self.assertIn('default', unlocked)
            except json.JSONDecodeError:
                self.fail("JSON still corrupted after save_progress")

    def test_flappy_mission_with_error_handling(self):
        """Regression: Verify mission completion works with robust error handling"""
        # Use dedicated user
        self.create_user('mission_tester', 'MissionTest123!', 'Mission Tester')
        self.login('mission_tester', 'MissionTest123!')
        csrf_token = self.get_csrf_from_page('/aggiornamenti')
        
        # Complete missions to unlock skins
        for i in range(5):
            resp = self.json_post('/api/flappy/complete_mission', {}, csrf_token)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.get_json()['success'])
            
            # Verify mission count increments correctly
            self.assertEqual(resp.get_json()['total_missions'], i + 1)
        
        # Verify database consistent
        with self.app_context():
            user = User.query.filter_by(username='mission_tester').first()
            profile = FlappyGameProfile.query.filter_by(user_id=user.id).first()
            self.assertEqual(profile.missions_completed_count, 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
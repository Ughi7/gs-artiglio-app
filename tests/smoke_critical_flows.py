import os
import re
import sys
import tempfile
import unittest
from contextlib import contextmanager


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ALLOW_SETUP_ROUTES', '0')


from app import bcrypt, create_app  # noqa: E402
from app.models import (  # noqa: E402
    AppRelease,
    Fine,
    FlappyGameProfile,
    NotificationPreference,
    PushSubscription,
    User,
    UserFeedback,
    UserSeenRelease,
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
            release = AppRelease(version='9.9.9', title='Smoke Release', notes='Smoke release notes', is_major=False)
            feedback = UserFeedback(user=player, feedback_type='bug', title='Smoke bug', description='Smoke description')

            db.session.add_all([admin, player, release, feedback])
            db.session.commit()

            cls.admin_id = admin.id
            cls.player_id = player.id
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

    def test_multe_validation_and_payment_flow(self):
        self.login('admin_test', 'Password123!')
        csrf_token = self.get_csrf_from_page('/multe')

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
            self.assertEqual(Fine.query.count(), 0)

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
            fine = Fine.query.one()
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
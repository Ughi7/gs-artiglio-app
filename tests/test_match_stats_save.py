import os
import re
import sys
import tempfile
import unittest
from datetime import datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ALLOW_SETUP_ROUTES', '0')


from app import bcrypt, create_app  # noqa: E402
from app.models import Event, MatchStats, User, db  # noqa: E402


CSRF_META_RE = re.compile(r'<meta name="csrf-token" content="([^"]+)">')


class MatchStatsSaveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-match-stats-', suffix='.db', delete=False)
        cls.temp_db.close()
        os.environ['DATABASE_URL'] = f"sqlite:///{cls.temp_db.name}"

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
        with self.app.app_context():
            db.drop_all()
            db.create_all()

            admin = User(
                username='admin_stats',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Admin Stats',
                soprannome='Admin',
                ruolo_volley='Scout',
                is_admin=True,
            )
            player = User(
                username='player_stats',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Player Stats',
                soprannome='Player',
                ruolo_volley='Schiacciatore',
            )
            event = Event(opponent_name='Opponent', date_start=datetime(2026, 3, 1, 21, 0), is_home=True, location='PalaArtiglio')

            db.session.add_all([admin, player, event])
            db.session.commit()

            self.admin_id = admin.id
            self.player_id = player.id
            self.event_id = event.id

        self.client = self.app.test_client()

    def extract_csrf_token(self, response):
        html = response.get_data(as_text=True)
        match = CSRF_META_RE.search(html)
        self.assertIsNotNone(match, 'CSRF meta token non trovato nella pagina renderizzata')
        return match.group(1)

    def login_admin(self):
        login_page = self.client.get('/login')
        self.assertEqual(login_page.status_code, 200)
        csrf_token = self.extract_csrf_token(login_page)

        response = self.client.post(
            '/login',
            data={'username': 'admin_stats', 'password': 'Password123!', 'csrf_token': csrf_token},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    def test_save_stats_accepts_empty_numeric_fields(self):
        self.login_admin()

        # Grab a fresh CSRF token from an authenticated page.
        partite_page = self.client.get('/partite')
        self.assertEqual(partite_page.status_code, 200)
        csrf_token = self.extract_csrf_token(partite_page)

        # Simulate user clearing numeric fields (browser submits empty strings).
        resp = self.client.post(
            '/salva_statistiche',
            data={
                'csrf_token': csrf_token,
                'event_id': str(self.event_id),
                'total_missed_serves': '',
                f'points_{self.player_id}': '',
                f'aces_{self.player_id}': '2',
                f'blocks_{self.player_id}': '',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)

        with self.app.app_context():
            event = db.session.get(Event, self.event_id)
            self.assertIsNotNone(event)
            self.assertEqual(event.total_missed_serves, 0)

            stat = MatchStats.query.filter_by(user_id=self.player_id, event_id=self.event_id).first()
            self.assertIsNotNone(stat)
            self.assertEqual((stat.points, stat.aces, stat.blocks), (0, 2, 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)


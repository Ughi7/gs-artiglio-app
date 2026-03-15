import json
import os
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
from app.models import Achievement, FlappyGameProfile, User, UserAchievement, db  # noqa: E402
from app.utils.admin_skin_service import (  # noqa: E402
    apply_retroactive_top_skins,
    build_admin_skin_users_data,
    get_or_create_flappy_profile,
    increment_skin_counter,
)


class AdminSkinServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-admin-skins-', suffix='.db', delete=False)
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
        with self.app.app_context():
            db.drop_all()
            db.create_all()

            admin = User(
                username='admin_service',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Admin Service',
                soprannome='Admin',
                ruolo_volley='Allenatore',
                is_admin=True,
            )
            player = User(
                username='player_service',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Player Service',
                soprannome='Player',
                ruolo_volley='Centrale',
            )
            winner = User(
                username='winner_service',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Winner Service',
                soprannome='Winner',
                ruolo_volley='Libero',
            )
            donor_badge = Achievement(
                code='top_donatore_mese',
                name='Top Donatore',
                description='Badge test top donatore',
                icon='💸',
            )

            db.session.add_all([admin, player, winner, donor_badge])
            db.session.commit()

            db.session.add(UserAchievement(user_id=winner.id, achievement_id=donor_badge.id, month=2, year=2026))
            db.session.commit()

            self.player_id = player.id
            self.winner_id = winner.id

    def test_increment_skin_counter_unlocks_threshold_skin(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            profile = get_or_create_flappy_profile(self.player_id)
            profile.bug_report_count = 2
            profile.unlocked_skins = '["default"]'
            db.session.commit()

            result = increment_skin_counter(
                'ladybug',
                self.player_id,
                note='Terza segnalazione',
                now=datetime(2026, 3, 12, 10, 30),
                notifier=notifier,
            )

            refreshed = FlappyGameProfile.query.filter_by(user_id=self.player_id).first()
            self.assertEqual(refreshed.bug_report_count, 3)
            self.assertIn('ladybug', json.loads(refreshed.unlocked_skins))
            self.assertIn('Terza segnalazione', refreshed.bug_report_notes)
            self.assertIn('SKIN SBLOCCATA', result['status'])
            self.assertEqual(len(notifications), 1)

    def test_build_admin_skin_users_data_creates_missing_profiles(self):
        with self.app.app_context():
            self.assertEqual(FlappyGameProfile.query.count(), 0)
            users_data = build_admin_skin_users_data()
            names = {entry['nome'] for entry in users_data}

            self.assertIn('Player', names)
            self.assertIn('Winner', names)
            self.assertNotIn('Admin', names)
            self.assertEqual(FlappyGameProfile.query.count(), 2)

    def test_apply_retroactive_top_skins_assigns_mapped_skin(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            total_assigned, assigned_details = apply_retroactive_top_skins(notifier=notifier)
            profile = FlappyGameProfile.query.filter_by(user_id=self.winner_id).first()

            self.assertEqual(total_assigned, 1)
            self.assertIn('1 mosquito', assigned_details)
            self.assertIsNotNone(profile)
            self.assertIn('mosquito', json.loads(profile.unlocked_skins))
            self.assertEqual(len(notifications), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
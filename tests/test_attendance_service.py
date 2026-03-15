import os
import sys
import tempfile
import unittest
from datetime import date, datetime


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('ALLOW_SETUP_ROUTES', '0')


from app import bcrypt, create_app  # noqa: E402
from app.models import Attendance, Event, Training, User, db  # noqa: E402
from app.utils.attendance_service import (  # noqa: E402
    AttendanceValidationError,
    can_manage_attendance,
    toggle_member_absence,
    toggle_training_late,
    toggle_user_absence,
    update_training,
)


class AttendanceServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-attendance-service-', suffix='.db', delete=False)
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

            player = User(
                username='attendance_player',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Attendance Player',
                soprannome='Player',
                ruolo_volley='Schiacciatore',
            )
            captain = User(
                username='attendance_captain',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Attendance Captain',
                soprannome='Captain',
                ruolo_volley='Libero',
                is_capitano=True,
            )
            event = Event(opponent_name='Smoke Opponent', date_start=datetime(2026, 3, 20, 21, 0), is_home=True, location='PalaArtiglio')
            training = Training(date=date(2026, 3, 18), start_time='19:00', end_time='21:00')

            db.session.add_all([player, captain, event, training])
            db.session.commit()

            self.player_id = player.id
            self.captain_id = captain.id
            self.event_id = event.id
            self.training_id = training.id

    def test_toggle_user_absence_adds_then_removes_record(self):
        with self.app.app_context():
            message, category = toggle_user_absence('match', self.event_id, self.player_id, 'Impegno')
            self.assertEqual((message, category), ('Assenza segnata!', 'warning'))
            self.assertEqual(Attendance.query.count(), 1)

            message, category = toggle_user_absence('match', self.event_id, self.player_id, 'Impegno')
            self.assertEqual((message, category), ('Assenza annullata!', 'success'))
            self.assertEqual(Attendance.query.count(), 0)

    def test_toggle_training_late_cycles_status(self):
        with self.app.app_context():
            message, category = toggle_training_late(self.training_id, self.player_id, 'Traffico')
            self.assertEqual((message, category), ('Ritardo segnato!', 'info'))
            record = Attendance.query.filter_by(training_id=self.training_id, user_id=self.player_id).first()
            self.assertEqual(record.status, 'late')

            message, category = toggle_training_late(self.training_id, self.player_id, 'Traffico')
            self.assertEqual((message, category), ('Ritardo annullato!', 'success'))
            self.assertIsNone(Attendance.query.filter_by(training_id=self.training_id, user_id=self.player_id).first())

    def test_update_training_and_member_absence_and_permissions(self):
        with self.app.app_context():
            training = db.session.get(Training, self.training_id)
            update_training(training, start_time='20:00', end_time='22:00', is_cancelled=True, coach_notes='Pubbliche', coach_notes_private='Private')
            updated_training = db.session.get(Training, self.training_id)
            self.assertEqual(updated_training.start_time, '20:00')
            self.assertTrue(updated_training.is_cancelled)
            self.assertEqual(updated_training.coach_notes_private, 'Private')

            player = db.session.get(User, self.player_id)
            message, category = toggle_member_absence('training', self.training_id, player, 'Influenza')
            self.assertEqual((message, category), ('Assenza di Player segnata!', 'warning'))

            captain = db.session.get(User, self.captain_id)
            self.assertTrue(can_manage_attendance(captain))
            self.assertFalse(can_manage_attendance(player))

    def test_invalid_event_type_raises_validation_error(self):
        with self.app.app_context():
            with self.assertRaises(AttendanceValidationError):
                toggle_user_absence('invalid', self.event_id, self.player_id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
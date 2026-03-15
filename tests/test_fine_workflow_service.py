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
from app.models import AdminFineReportEvent, Fine, FineVote, User, db  # noqa: E402
from app.utils.fine_workflow_service import (  # noqa: E402
    FineWorkflowError,
    approve_denuncia,
    cancel_denuncia_vote,
    cast_denuncia_vote,
    mark_fine_paid,
    start_denuncia_vote,
    submit_denuncia,
    update_vote_exclusions,
)


class FineWorkflowServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(prefix='gs-artiglio-fines-service-', suffix='.db', delete=False)
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
                username='fines_admin',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Fines Admin',
                soprannome='Admin',
                ruolo_volley='Allenatore',
                is_admin=True,
            )
            reporter = User(
                username='fines_reporter',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Fines Reporter',
                soprannome='Reporter',
                ruolo_volley='Libero',
            )
            accused = User(
                username='fines_accused',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Fines Accused',
                soprannome='Accused',
                ruolo_volley='Centrale',
            )
            voter = User(
                username='fines_voter',
                password_hash=bcrypt.generate_password_hash('Password123!').decode('utf-8'),
                nome_completo='Fines Voter',
                soprannome='Voter',
                ruolo_volley='Schiacciatore',
            )

            db.session.add_all([admin, reporter, accused, voter])
            db.session.commit()

            accused.current_streak = 8
            db.session.commit()

            self.admin_id = admin.id
            self.reporter_id = reporter.id
            self.accused_id = accused.id
            self.voter_id = voter.id

    def test_submit_denuncia_creates_pending_fine(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            reporter = db.session.get(User, self.reporter_id)
            fine, accused = submit_denuncia(
                reporter,
                {
                    'user_id': str(self.accused_id),
                    'data_infrazione': '2026-03-10',
                    'motivazione': 'Ritardo cronico',
                    'importo': '3.50',
                    'note': 'Arrivato dopo il riscaldamento',
                },
                now=datetime(2026, 3, 12, 12, 0),
                notifier=notifier,
            )

            self.assertTrue(fine.pending_approval)
            self.assertEqual(accused.id, self.accused_id)
            self.assertEqual(Fine.query.count(), 1)
            self.assertEqual(len(notifications), 1)

    def test_mark_fine_paid_updates_report_event(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            admin = db.session.get(User, self.admin_id)
            fine = Fine(
                user_id=self.accused_id,
                amount=5.0,
                reason='Mancata divisa',
                date=datetime(2026, 3, 8, 20, 0),
            )
            db.session.add(fine)
            db.session.commit()

            metodo = mark_fine_paid(fine, admin, 'paypal', notifier=notifier)

            self.assertEqual(metodo, 'paypal')
            refreshed = db.session.get(Fine, fine.id)
            self.assertTrue(refreshed.paid)
            self.assertEqual(refreshed.payment_method, 'paypal')
            self.assertEqual(AdminFineReportEvent.query.filter_by(action='mark_fine_paid').count(), 1)
            self.assertGreaterEqual(len(notifications), 1)

    def test_voting_flow_handles_votes_exclusions_and_cancel(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            admin = db.session.get(User, self.admin_id)
            reporter = db.session.get(User, self.reporter_id)
            voter = db.session.get(User, self.voter_id)
            fine = Fine(
                user_id=self.accused_id,
                amount=4.0,
                reason='Urlo fuori tempo',
                date=datetime(2026, 3, 9, 21, 0),
                deadline=datetime(2026, 3, 30, 21, 0),
                pending_approval=True,
                denunciante_id=reporter.id,
            )
            db.session.add(fine)
            db.session.commit()

            voting_end = start_denuncia_vote(fine, admin, now=datetime(2026, 3, 12, 10, 0), notifier=notifier)
            self.assertIsNotNone(voting_end)
            self.assertTrue(db.session.get(Fine, fine.id).voting_active)

            message, category = cast_denuncia_vote(db.session.get(Fine, fine.id), voter, '1', now=datetime(2026, 3, 12, 11, 0))
            self.assertEqual((message, category), ('Voto registrato!', 'success'))

            message, category = cast_denuncia_vote(db.session.get(Fine, fine.id), voter, '0', now=datetime(2026, 3, 12, 11, 5))
            self.assertEqual((message, category), ('Voto modificato!', 'success'))

            with self.assertRaises(FineWorkflowError):
                cast_denuncia_vote(db.session.get(Fine, fine.id), db.session.get(User, self.accused_id), '1')

            excluded_count = update_vote_exclusions(db.session.get(Fine, fine.id), [str(self.reporter_id)])
            self.assertEqual(excluded_count, 1)

            with self.assertRaises(FineWorkflowError):
                cast_denuncia_vote(db.session.get(Fine, fine.id), reporter, '1')

            cancel_denuncia_vote(db.session.get(Fine, fine.id), notifier=notifier)
            cancelled = db.session.get(Fine, fine.id)
            self.assertFalse(cancelled.voting_active)
            self.assertTrue(cancelled.pending_approval)
            self.assertEqual(FineVote.query.filter_by(fine_id=fine.id).count(), 0)

    def test_approve_denuncia_resets_streak(self):
        notifications = []

        def notifier(*args, **kwargs):
            notifications.append((args, kwargs))

        with self.app.app_context():
            admin = db.session.get(User, self.admin_id)
            fine = Fine(
                user_id=self.accused_id,
                amount=2.0,
                reason='Ritardo riunione',
                date=datetime(2026, 3, 7, 18, 0),
                deadline=datetime(2026, 3, 28, 18, 0),
                pending_approval=True,
                denunciante_id=self.reporter_id,
            )
            db.session.add(fine)
            db.session.commit()

            approve_denuncia(fine, admin, notifier=notifier)

            accused = db.session.get(User, self.accused_id)
            refreshed = db.session.get(Fine, fine.id)
            self.assertFalse(refreshed.pending_approval)
            self.assertEqual(accused.current_streak, 0)
            self.assertEqual(AdminFineReportEvent.query.filter_by(action='approve_denuncia').count(), 1)
            self.assertEqual(len(notifications), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
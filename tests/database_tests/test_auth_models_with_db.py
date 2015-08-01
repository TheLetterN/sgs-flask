import unittest
from datetime import datetime, timedelta
from flask import current_app
from app import create_app, db
from app.auth.models import EmailRequest, get_user_from_confirmation_token, \
    Serializer, User


class TestUserWithDB(unittest.TestCase):
    """Test User model methods that need to access the database."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_email_request_too_soon(self):
        """Return False if not too soon, True if too soon."""
        user = User()
        user.name = 'AzureDiamond'
        user.email = 'gullible@bash.org'
        user.set_password('hunter2')
        req_time = datetime.utcnow() - timedelta(minutes=6)
        user.email_requests.append(EmailRequest('confirm account',
                                                time=req_time))
        db.session.add(user)
        db.session.commit()
        self.assertTrue(user.email_request_too_soon('confirm account',
                                                    minutes=10))
        self.assertFalse(user.email_request_too_soon('confirm account',
                                                     minutes=5))

    def test_email_request_too_many(self):
        """Return True if too many requests made by sender, False if not."""
        user = User()
        user.name = 'AzureDiamond'
        user.email = 'gullible@bash.org'
        user.set_password('hunter2')
        for i in range(0, 10):
            user.email_requests.append(EmailRequest('confirm account'))
        db.session.add(user)
        db.session.commit()
        self.assertTrue(user.email_request_too_many('confirm account',
                                                    days=30,
                                                    maximum=10))
        self.assertFalse(user.email_request_too_many('confirm account',
                                                     days=30,
                                                     maximum=9))

    def test_get_user_from_confirmation_token_bad_or_wrong_token(self):
        """get_user_from... should raise exception with bad/wrong token."""
        s = Serializer(current_app.config['SECRET_KEY'])
        wrongtoken = s.dumps({'whee': 'beep!'})
        with self.assertRaises(KeyError):
            get_user_from_confirmation_token(wrongtoken)
        with self.assertRaises(ValueError):
            get_user_from_confirmation_token('badtoken')

    def test_get_user_from_confirmation_token(self):
        """get_user_from... raises exeption if user already confirmed."""
        user = User()
        user.id = 42
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        token = user.generate_account_confirmation_token()
        with self.assertRaises(ValueError):
            get_user_from_confirmation_token(token)

    def test_get_user_from_confirmation_token_with_valid_token(self):
        """get_user_from_confirmation_token should work given a valid token."""
        user1 = User()
        user1.name = 'AzureDiamond'
        user1.set_password('hunter2')
        user1.email = 'gullible@bash.org'
        db.session.add(user1)
        db.session.commit()
        token = user1.generate_account_confirmation_token()
        user2 = get_user_from_confirmation_token(token)
        self.assertEqual(user1.id, user2.id)

    def test_prune_email_requests(self):
        """Email requests older than timespan specified should be deleted."""
        user = User()
        user.name = 'AzureDiamond'
        user.email = 'gullible@bash.org'
        user.set_password('hunter2')
        forty_days_ago = datetime.utcnow() - timedelta(days=40)
        for i in range(0, 4):
            user.email_requests.append(EmailRequest('confirm email',
                                                    time=forty_days_ago))
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        for i in range(0, 6):
            user.email_requests.append(EmailRequest('confirm email',
                                                    time=thirty_days_ago))
        db.session.add(user)
        db.session.commit()
        reqs = user.email_requests.filter_by(sender='confirm email').all()
        self.assertEqual(len(reqs), 10)
        user.prune_email_requests('confirm email', days=31)
        reqs = user.email_requests.filter_by(sender='confirm email').all()
        self.assertEqual(len(reqs), 6)


if __name__ == '__main__':
    unittest.main()

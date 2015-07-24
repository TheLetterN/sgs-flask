import unittest
from app import create_app, db
from app.auth.models import get_user_from_confirmation_token, Serializer, User
from flask import current_app


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


if __name__ == '__main__':
    unittest.main()

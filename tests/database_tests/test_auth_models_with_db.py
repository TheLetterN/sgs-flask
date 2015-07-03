import unittest
from app import create_app, db
from app.auth.models import get_user_from_confirmation_token, User


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

    def test_get_user_from_confirmation_token_with_valid_token(self):
        """get_user_from_confirmation_token should work given a valid token."""
        user1 = User()
        user1.name = 'AzureDiamond'
        user1.set_password('hunter2')
        user1.email = 'gullible@bash.org'
        db.session.add(user1)
        db.session.commit()
        token = user1.generate_confirmation_token()
        user2 = get_user_from_confirmation_token(token)
        self.assertEqual(user1.id, user2.id)


if __name__ == '__main__':
    unittest.main()

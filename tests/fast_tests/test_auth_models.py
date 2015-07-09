import unittest
from app import create_app
from app.auth.models import Role, User


class TestRole(unittest.TestCase):
    """Unit tests for the Role class in app/auth/models"""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_repr(self):
        """Role.__repr__ should return "<Role 'Role.name'>"."""
        role = Role()
        role.name = 'Peasant'
        self.assertEqual(repr(role), '<Role \'Peasant\'>')


class TestUser(unittest.TestCase):
    """Unit tests for the User class in app/auth/models"""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_confirm_account_works_with_generated_token(self):
        """confirm_account should return True if given a valid token."""
        user = User()
        user.id = 42
        token = user.generate_account_confirmation_token()
        self.assertTrue(user.confirm_account(token))

    def test_confirm_new_email_works_with_generated_token(self):
        """confirm_new_mail should return True & set email w/ valid token."""
        user = User()
        user.id = 42
        user.email = 'fprefect@h2g2.com'
        new_email = 'frood@towels.com'
        token = user.generate_new_email_token(new_email)
        self.assertTrue(user.confirm_new_email(token))
        self.assertEqual(new_email, user.email)

    def test_password_attribute_raises_exception(self):
        """Trying to read User.password should raise an attribute error."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        with self.assertRaises(AttributeError):
            dummy.password

    def test_password_hashing(self):
        """verify_password() should return true if given correct password."""
        dummy = User()
        password = 'enlargeyourpennies'
        dummy.set_password(password)
        self.assertTrue(dummy.verify_password(password))

    def test_password_reset(self):
        """Password should be reset if given a valid token and a new pass."""
        user = User()
        user.id = 42
        user.set_password('hunter2')
        token = user.generate_password_reset_token()
        newpass = 'hunter2000'
        self.assertTrue(user.reset_password(token, newpass))
        self.assertTrue(user.verify_password(newpass))

    def test_password_setter(self):
        """User.password = <pw> should set User.password_hash."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        self.assertTrue(dummy.password_hash is not None)

    def test_repr(self):
        """User.__repr__ should return "<User 'User.name'>"."""
        dummy = User()
        dummy.name = 'Gabbo'
        self.assertEqual(repr(dummy), '<User \'Gabbo\'>')


if __name__ == '__main__':
    unittest.main()

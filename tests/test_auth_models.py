import unittest
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
        pass

    def tearDown(self):
        pass

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

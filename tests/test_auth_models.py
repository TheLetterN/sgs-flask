import unittest
from app.auth.models import User


class TestUser(unittest.TestCase):
    """Unit tests for the user class in app/auth/models"""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_password_hashing(self):
        """verify_password() should return true if given correct password."""
        dummy = User()
        password = 'enormouspennies'
        dummy.password = password
        self.assertTrue(dummy.verify_password(password))

    def test_password_attribute_raises_exception(self):
        """Trying to read User.password should raise an attribute error."""
        dummy = User()
        dummy.password = 'enormouspennies'
        with self.assertRaises(AttributeError):
            print(dummy.password)


if __name__ == '__main__':
    unittest.main()

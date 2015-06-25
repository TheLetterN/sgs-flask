import unittest
from app import create_app, db
from app.auth.models import User


class TestAuthRoutes(unittest.TestCase):
    """Tests routes in the auth module."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.tc = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_login_returns_valid_page(self):
        retval = self.tc.get('/auth/login')
        self.assertEqual(retval.status_code, 200)


if __name__ == '__main__':
    unittest.main()

import unittest
from app import create_app


class TestAuthRoutes(unittest.TestCase):
    """Tests routes in the auth module."""
    def setUp(self):
        app = create_app('testing')
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_login_returns_valid_page(self):
        retval = self.app.get('/auth/login')
        self.assertEqual(retval.status_code, 200)


if __name__ == '__main__':
    unittest.main()

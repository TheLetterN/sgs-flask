import unittest
from app import create_app


class TestMainRoutes(unittest.TestCase):
    """Tests route functions in the main module."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.tc = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_index_returns_valid_page(self):
        """If the index page breaks due to code changes, we want to know."""
        retval = self.tc.get('/')
        self.assertEqual(retval.status_code, 200)


if __name__ == '__main__':
    unittest.main()

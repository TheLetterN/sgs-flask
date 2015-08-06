import unittest
from flask import url_for
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
        retval = self.tc.get(url_for('main.index'))
        self.assertEqual(retval.status_code, 200)

    def test_other_index_pages_redirect_to_main_index(self):
        """/index and /index.html should give 301 redirect responses."""
        retval1 = self.tc.get('/index', follow_redirects=False)
        retval2 = self.tc.get('/index.html', follow_redirects=False)
        self.assertEqual(retval1.status_code, 301)
        self.assertEqual(retval2.status_code, 301)


if __name__ == '__main__':
    unittest.main()

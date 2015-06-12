"""
    Tests views in the main module.
"""

import unittest
from app import create_app


class TestMainViews(unittest.TestCase):
    def setUp(self):
        app = create_app('testing')
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_index_returns_valid_page(self):
        retval = self.app.get('/')
        self.assertEqual(retval.status_code, 200)


if __name__ == '__main__':
    unittest.main()

import unittest
from flask import current_app
from app import create_app, make_breadcrumbs


class TestApp(unittest.TestCase):
    """Tests for base Flask application."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_make_breadcrumbs_bad_args(self):
        """Raise a ValueError given unusable args."""
        with self.assertRaises(ValueError):
            make_breadcrumbs('<a href="place.com">The Place</a>')
        with self.assertRaises(ValueError):
            make_breadcrumbs(('place/stuff', 'other/stuff', 'Stuff'))
        with self.assertRaises(ValueError):
            make_breadcrumbs(('and/how',))

    def test_make_breadcrumbs_valid_args(self):
        """Return a list of links given a set of valid tuples."""
        crumbs = make_breadcrumbs(
            ('relative/link.html', 'Relative Link'),
            ('http://absolu.te/link.html', 'Absolute Link'),
            ('parts/unknown', 'Parts Unknown')
        )
        self.assertIn('<a href="relative/link.html">Relative Link</a>',
                      crumbs)
        self.assertIn('<a href="http://absolu.te/link.html">Absolute Link</a>',
                      crumbs)
        self.assertIn('<a href="parts/unknown">Parts Unknown</a>', crumbs)


if __name__ == '__main__':
    unittest.main()

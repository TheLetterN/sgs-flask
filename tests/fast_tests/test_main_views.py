from flask import url_for
from tests.conftest import app  # noqa


class TestMainRoutes:
    """Tests route functions in the main module."""
    def test_index_returns_valid_page(self, app):
        """If the index page breaks due to code changes, we want to know."""
        with app.test_client() as tc:
            rv = tc.get(url_for('main.index'))
        assert rv.status_code == 200

    def test_other_index_pages_redirect_to_main_index(self, app):
        """/index and /index.html should give 301 redirect responses."""
        with app.test_client() as tc:
            rv1 = tc.get('/index', follow_redirects=False)
            rv2 = tc.get('/index.html', follow_redirects=False)
        assert rv1.status_code == 301
        assert rv2.status_code == 301

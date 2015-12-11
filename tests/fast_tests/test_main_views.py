from flask import url_for
from tests.conftest import app  # noqa


class TestMainRoutes:
    """Tests route functions in the main module."""
    def test_index_returns_valid_page(self, app):
        """If the index page breaks due to code changes, we want to know."""
        with app.test_client() as tc:
            rv = tc.get(url_for('main.index'))
        assert rv.status_code == 200

import pytest
from flask import current_app
from app import Anonymous, make_breadcrumbs
from tests.conftest import app  # noqa


@pytest.mark.usefixtures('app')
class TestApp:
    """Tests for base Flask application."""
    def test_app_exists(self):
        assert current_app is not None

    def test_is_testing(self):
        assert current_app.config['TESTING']

    def test_make_breadcrumbs_bad_args(self):
        """Raise a ValueError given unusable args."""
        with pytest.raises(ValueError):
            make_breadcrumbs('<a href="place.com">The Place</a>')
        with pytest.raises(ValueError):
            make_breadcrumbs(('place/stuff', 'other/stuff', 'Stuff'))
        with pytest.raises(ValueError):
            make_breadcrumbs(('and/how',))

    def test_make_breadcrumbs_valid_args(self):
        """Return a list of links given a set of valid tuples."""
        crumbs = make_breadcrumbs(
            ('relative/link.html', 'Relative Link'),
            ('http://absolu.te/link.html', 'Absolute Link'),
            ('parts/unknown', 'Parts Unknown')
        )
        assert '<a href="relative/link.html">Relative Link</a>' in crumbs
        assert '<a href="http://absolu.te/link.html">Absolute Link</a>' in\
            crumbs
        assert '<a href="parts/unknown">Parts Unknown</a>' in crumbs


@pytest.mark.usefixtures('app')
class TestAnonymous:
    """Tests for Anonymous user class."""
    def test_can(self):
        """Anonymous users are filthy savages who can do nothing."""
        user = Anonymous()
        assert not user.can(permission='1')

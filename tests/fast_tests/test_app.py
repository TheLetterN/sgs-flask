import pytest
from unittest import mock
from flask import current_app
from app import Anonymous, get_index_map, make_breadcrumbs


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

    def test_get_index_map_no_file(self):
        """Return an empty dict if no file is loaded."""
        assert get_index_map('/tmp/some_nonexistent_file.blargh') == {}

    @mock.patch('app.current_app.config.get')
    @mock.patch('app.os.path.exists')
    def test_get_index_map_uses_default_file(self, m_exists, m_get):
        """Use the file specified by config['INDEXES_JSON_FILE']"""
        m_exists.return_value = False
        get_index_map()
        m_get.assert_called_with('INDEXES_JSON_FILE')


@pytest.mark.usefixtures('app')
class TestAnonymous:
    """Tests for Anonymous user class."""
    def test_can(self):
        """Anonymous users are filthy savages who can do nothing."""
        user = Anonymous()
        assert not user.can(permission='1')

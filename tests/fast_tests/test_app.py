import pytest
from unittest import mock
from flask import current_app
from app import Anonymous, get_index_nav


@pytest.mark.usefixtures('app')
class TestApp:
    """Tests for base Flask application."""
    def test_app_exists(self):
        assert current_app is not None

    def test_is_testing(self):
        assert current_app.config['TESTING']

    def test_get_index_nav_no_file(self):
        """Return an empty dict if no file is loaded."""
        assert get_index_nav('/tmp/some_nonexistent_file.blargh') == {}

    @mock.patch('app.current_app.config.get')
    @mock.patch('app.os.path.exists')
    def test_get_index_nav_uses_default_file(self, m_exists, m_get):
        """Use the folder specified by config['JSON_FOLDER']"""
        m_exists.return_value = False
        get_index_nav()
        m_get.assert_called_with('JSON_FOLDER')


@pytest.mark.usefixtures('app')
class TestAnonymous:
    """Tests for Anonymous user class."""
    def test_can(self):
        """Anonymous users are filthy savages who can do nothing."""
        user = Anonymous()
        assert not user.can(permission='1')

import pytest
from unittest import mock
from flask import current_app
from app import Anonymous, load_nav_data


@pytest.mark.usefixtures('app')
class TestApp:
    """Tests for base Flask application."""
    def test_app_exists(self):
        assert current_app is not None

    def test_is_testing(self):
        assert current_app.config['TESTING']

    def test_load_nav_data_no_file(self):
        """Return an empty list if no file is loaded."""
        assert load_nav_data('/tmp/some_nonexistent_file.blargh') == []

    @mock.patch('app.current_app.config.get')
    def test_load_nav_data_uses_default_file(self, m_get):
        """Use the folder specified by config['JSON_FOLDER']"""
        m_get.return_value = 'nav_data.json'
        load_nav_data()
        m_get.assert_called_with('JSON_FOLDER')


@pytest.mark.usefixtures('app')
class TestAnonymous:
    """Tests for Anonymous user class."""
    def test_can(self):
        """Anonymous users are filthy savages who can do nothing."""
        user = Anonymous()
        assert not user.can(permission='1')

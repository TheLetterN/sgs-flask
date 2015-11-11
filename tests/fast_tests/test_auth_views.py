from flask import Markup, url_for
from app.auth.models import User
from app.auth.views import (
    support_mailto_address,
    update_permission
)
from tests.conftest import app  # noqa


class TestHelperFunctions:
    """Test helper functions that are not routes."""
    def test_support_mailto_address(self, app):
        """Return a mailto link as a Markup object."""
        app.config['SUPPORT_EMAIL'] = 'foo@bar.com'
        mailto1 = support_mailto_address('Test', 'Test subject')
        assert mailto1 == Markup('<a href="mailto:foo@bar.com?' +
                                 'subject=Test subject">Test</a>')
        mailto2 = support_mailto_address('Test')
        assert mailto2 == Markup('<a href="mailto:foo@bar.com">' +
                                 'Test</a>')


class TestAuthRoutes:
    """Tests routes in the auth module."""
    def test_confirm_account_bad_token(self, app):
        """confirm_account should redirect and flash error given bad token."""
        with app.test_client() as tc:
            rv = tc.get(url_for('auth.confirm_account', token='badtoken'),
                        follow_redirects=True)
        assert 'Token is malformed or invalid!' in str(rv.data)

    def test_confirm_account_no_token(self, app):
        """If no token given, confirm_account redirects to resend page."""
        with app.test_client() as tc:
            rv = tc.get(url_for('auth.confirm_account'))
        assert rv.location == url_for('auth.resend_confirmation',
                                      _external=True)

    def test_update_permission(self, app):
        """update_permission returns True if updated, false if not.

        It should also change the user's permission if updated.
        """
        user = User()
        user.permissions = 0
        perm1 = 0b1
        perm2 = 0b10
        assert update_permission(user, perm1, True, 'perm1')
        assert user.can(perm1)
        assert not update_permission(user, perm1, True, 'perm1')
        assert user.can(perm1)
        assert update_permission(user, perm2, True, 'perm2')
        assert user.can(perm2)
        assert update_permission(user, perm1, False, 'perm1')
        assert not user.can(perm1)
        assert user.can(perm2)

    def test_register_displays_form(self, app):
        """register w/ no POST should display the registration form page."""
        with app.test_client() as tc:
            rv = tc.get(url_for('auth.register'), follow_redirects=True)
        assert 'Account Registration' in str(rv.data)

    def test_resend_confirmation_displays_form(self, app):
        """resend_confirmation w/ no POST should display form page."""
        with app.test_client() as tc:
            rv = tc.get(url_for('auth.resend_confirmation'),
                        follow_redirects=True)
        assert 'Resend Account Confirmation' in str(rv.data)

    def test_select_user_no_target(self, app):
        """select_user should redirect to main.index if no target_route."""
        with app.test_client() as tc:
            rv = tc.get(url_for('auth.select_user'), follow_redirects=False)
        assert rv.location, url_for('main.index', _external=True)

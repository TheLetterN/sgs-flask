import unittest
from flask import url_for
from app import create_app
from app.auth.models import User
from app.auth.views import confirm_account, update_permission


class TestAuthRoutes(unittest.TestCase):
    """Tests routes in the auth module."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.tc = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_confirm_account_bad_token(self):
        """confirm_account should redirect and flash error given bad token."""
        retval = self.tc.get('/auth/confirm_account/badtoken',
                             follow_redirects=True)
        self.assertTrue('Token is malformed or invalid!' in str(retval.data))

    def test_confirm_account_no_token(self):
        """If no token given, confirm_account redirects to resend page."""
        retval = confirm_account(None)
        self.assertEqual(retval.location, '/auth/resend_confirmation')

    def test_confirm_new_email_no_token(self):
        """confirm_new_email returns a 404 error if given no token."""
        retval = self.tc.get('/auth/confirm_new_email/',
                             follow_redirects=True)
        self.assertEqual(retval.status_code, 404)

    def test_update_permission(self):
        """update_permission returns True if updated, false if not.

        It should also change the user's permission if updated.
        """
        user = User()
        user.permissions = 0
        perm1 = 0b1
        perm2 = 0b10
        self.assertTrue(update_permission(user, perm1, True, 'perm1'))
        self.assertTrue(user.can(perm1))
        self.assertFalse(update_permission(user, perm1, True, 'perm1'))
        self.assertTrue(user.can(perm1))
        self.assertTrue(update_permission(user, perm2, True, 'perm2'))
        self.assertTrue(user.can(perm2))
        self.assertTrue(update_permission(user, perm1, False, 'perm1'))
        self.assertFalse(user.can(perm1))
        self.assertTrue(user.can(perm2))

    def test_register_displays_form(self):
        """register w/ no POST should display the registration form page."""
        rv = self.tc.get('/auth/register', follow_redirects=True)
        self.assertTrue('Account Registration' in str(rv.data))

    def test_resend_confirmation_displays_form(self):
        """resend_confirmation w/ no POST should display form page."""
        rv = self.tc.get('/auth/resend_confirmation', follow_redirects=True)
        self.assertTrue('Resend Account Confirmation' in str(rv.data))

    def test_select_user_no_target(self):
        """select_user should redirect to main.index if no target_route."""
        rv = self.tc.get('/auth/select_user', follow_redirects=False)
        self.assertEqual(rv.location, url_for('main.index', _external=True))


if __name__ == '__main__':
    unittest.main()

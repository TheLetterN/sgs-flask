import unittest
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

    def test_confirm_account_no_token(self):
        """If no token given, confirm_account redirects to resend page."""
        retval = confirm_account(None)
        self.assertEqual(retval.location, '/auth/resend_confirmation')

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


if __name__ == '__main__':
    unittest.main()

import unittest
from app import create_app
from app.auth.models import User


class TestUser(unittest.TestCase):
    """Unit tests for the User class in app/auth/models"""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_can(self):
        """can should return True if user has permission, False if not.

        Note:
            Permissions are in the form of set bits in an integer. Since the
            actual Permission attributes may change in the future, we can
            more easily test can() with dummy permissions here, it works the
            same way as using Permission attributes insted.
        """
        user = User()
        perm1 = 0b1
        perm2 = 0b10
        perm3 = 0b100
        user.permissions = perm1 | perm3    # 0b101
        self.assertTrue(user.can(perm1))
        self.assertTrue(user.can(perm3))
        self.assertFalse(user.can(perm2))

    def test_confirm_account_works_with_generated_token(self):
        """confirm_account should return True if given a valid token."""
        user = User()
        user.id = 42
        token = user.generate_account_confirmation_token()
        self.assertTrue(user.confirm_account(token))

    def test_confirm_account_bad_token_or_wrong_user(self):
        """confirm_account returns false if token is bad or for wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_account_confirmation_token()
        self.assertFalse(user2.confirm_account(token))
        self.assertFalse(user1.confirm_account('badtoken'))

    def test_confirm_new_email_bad_token_or_wrong_user(self):
        """confirm_new_email returns false if token is bad or wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_new_email_token('foo@bar.com')
        self.assertFalse(user2.confirm_new_email(token))
        self.assertFalse(user1.confirm_account('badtoken'))

    def test_confirm_new_email_works_with_generated_token(self):
        """confirm_new_mail should return True & set email w/ valid token."""
        user = User()
        user.id = 42
        user.email = 'fprefect@h2g2.com'
        new_email = 'frood@towels.com'
        token = user.generate_new_email_token(new_email)
        self.assertTrue(user.confirm_new_email(token))
        self.assertEqual(new_email, user.email)

    def test_grant_permission(self):
        """grant_permission should set a permission and not unset it."""
        user = User()
        user.permissions = 0
        perm1 = 0b1
        perm2 = 0b10
        perm3 = 0b100
        user.grant_permission(perm1)
        self.assertEqual(user.permissions, 0b1)
        user.grant_permission(perm3)
        self.assertEqual(user.permissions, 0b101)
        user.grant_permission(perm2)
        self.assertEqual(user.permissions, 0b111)
        # Already set permissions should remain unchanged.
        user.grant_permission(perm1)
        self.assertEqual(user.permissions, 0b111)
        user.grant_permission(perm2)
        self.assertEqual(user.permissions, 0b111)
        user.grant_permission(perm3)
        self.assertEqual(user.permissions, 0b111)

    def test_password_attribute_raises_exception(self):
        """Trying to read User.password should raise an attribute error."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        with self.assertRaises(AttributeError):
            dummy.password

    def test_password_hashing(self):
        """verify_password() should return true if given correct password."""
        dummy = User()
        password = 'enlargeyourpennies'
        dummy.set_password(password)
        self.assertTrue(dummy.verify_password(password))

    def test_password_reset(self):
        """Password should be reset if given a valid token and a new pass."""
        user = User()
        user.id = 42
        user.set_password('hunter2')
        token = user.generate_password_reset_token()
        newpass = 'hunter2000'
        self.assertTrue(user.reset_password(token, newpass))
        self.assertTrue(user.verify_password(newpass))

    def test_password_setter(self):
        """User.password = <pw> should set User.password_hash."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        self.assertTrue(dummy.password_hash is not None)

    def test_reset_password_bad_token_or_wrong_user(self):
        """reset_password returns false with a bad token or wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_password_reset_token()
        self.assertFalse(user2.reset_password(token, 'foo'))
        self.assertFalse(user1.reset_password('badtoken', 'foo'))

    def test_reset_password_with_valid_token(self):
        """reset_password returns true with a valid token."""
        user = User()
        user.id = 42
        token = user.generate_password_reset_token()
        self.assertTrue(user.reset_password(token, 'foo'))

    def test_revoke_permission(self):
        """revoke_permission should remove perm if set.

        It should not change anything if the permission given isn't set.
        """
        user = User()
        user.permissions = 0b111
        user.revoke_permission(0b10)
        self.assertEqual(user.permissions, 0b101)
        user.revoke_permission(0b1)
        self.assertEqual(user.permissions, 0b100)
        # Revoking unset permissions shouldn't change anything.
        user.revoke_permission(0b10)
        self.assertEqual(user.permissions, 0b100)
        user.revoke_permission(0b1)
        self.assertEqual(user.permissions, 0b100)

    def test_repr(self):
        """User.__repr__ should return "<User 'User.name'>"."""
        dummy = User()
        dummy.name = 'Gabbo'
        self.assertEqual(repr(dummy), '<User \'Gabbo\'>')


if __name__ == '__main__':
    unittest.main()

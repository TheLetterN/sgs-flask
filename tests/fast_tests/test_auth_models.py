import pytest
from app.auth.models import EmailRequest, User
from tests.conftest import app  # noqa


class TestEmailRequest:
    """Unit tests for the EmailRequest class in app/auth/models"""
    def test_repr(self, app):
        """Returns a string formatted '<<class name> '<sender>'>'"""
        req = EmailRequest('test request')
        assert str(req) == '<EmailRequest \'test request\'>'


class TestUser:
    """Unit tests for the User class in app/auth/models"""
    def test_can(self, app):
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
        assert user.can(perm1)
        assert user.can(perm3)
        assert not user.can(perm2)

    def test_confirm_account_works_with_generated_token(self, app):
        """confirm_account should return True if given a valid token."""
        user = User()
        user.id = 42
        token = user.generate_account_confirmation_token()
        assert user.confirm_account(token)

    def test_confirm_account_bad_token_or_wrong_user(self, app):
        """confirm_account returns false if token is bad or for wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_account_confirmation_token()
        assert not user2.confirm_account(token)
        assert not user1.confirm_account('badtoken')

    def test_confirm_new_email_bad_token_or_wrong_user(self, app):
        """confirm_new_email returns false if token is bad or wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_new_email_token('foo@bar.com')
        assert not user2.confirm_new_email(token)
        assert not user1.confirm_account('badtoken')

    def test_confirm_new_email_works_with_generated_token(self, app):
        """confirm_new_mail should return True & set email w/ valid token."""
        user = User()
        user.id = 42
        user.email = 'fprefect@h2g2.com'
        new_email = 'frood@towels.com'
        token = user.generate_new_email_token(new_email)
        assert user.confirm_new_email(token)
        assert new_email == user.email

    def test_grant_permission(self, app):
        """grant_permission should set a permission and not unset it."""
        user = User()
        user.permissions = 0
        perm1 = 0b1
        perm2 = 0b10
        perm3 = 0b100
        user.grant_permission(perm1)
        assert user.permissions == 0b1
        user.grant_permission(perm3)
        assert user.permissions == 0b101
        user.grant_permission(perm2)
        assert user.permissions == 0b111
        # Already set permissions should remain unchanged.
        user.grant_permission(perm1)
        assert user.permissions == 0b111
        user.grant_permission(perm2)
        assert user.permissions == 0b111
        user.grant_permission(perm3)
        assert user.permissions == 0b111

    def test_password_attribute_raises_exception(self, app):
        """Trying to read User.password should raise an attribute error."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        with pytest.raises(AttributeError):
            dummy.password

    def test_password_hashing(self, app):
        """verify_password() should return true if given correct password."""
        dummy = User()
        password = 'enlargeyourpennies'
        dummy.set_password(password)
        assert dummy.verify_password(password)

    def test_password_reset(self, app):
        """Password should be reset if given a valid token and a new pass."""
        user = User()
        user.id = 42
        user.set_password('hunter2')
        token = user.generate_password_reset_token()
        newpass = 'hunter2000'
        assert user.reset_password(token, newpass)
        assert user.verify_password(newpass)

    def test_password_setter(self, app):
        """User.password = <pw> should set User.password_hash."""
        dummy = User()
        dummy.password = 'enlargeyourpennies'
        assert dummy.password_hash is not None

    def test_reset_password_bad_token_or_wrong_user(self, app):
        """reset_password returns false with a bad token or wrong user."""
        user1 = User()
        user1.id = 42
        user2 = User()
        user2.id = 33
        token = user1.generate_password_reset_token()
        assert not user2.reset_password(token, 'foo')
        assert not user1.reset_password('badtoken', 'foo')

    def test_reset_password_with_valid_token(self, app):
        """reset_password returns true with a valid token."""
        user = User()
        user.id = 42
        token = user.generate_password_reset_token()
        assert user.reset_password(token, 'foo')

    def test_revoke_permission(self, app):
        """revoke_permission should remove perm if set.

        It should not change anything if the permission given isn't set.
        """
        user = User()
        user.permissions = 0b111
        user.revoke_permission(0b10)
        assert user.permissions == 0b101
        user.revoke_permission(0b1)
        assert user.permissions == 0b100
        # Revoking unset permissions shouldn't change anything.
        user.revoke_permission(0b10)
        assert user.permissions == 0b100
        user.revoke_permission(0b1)
        assert user.permissions == 0b100

    def test_repr(self, app):
        """User.__repr__ should return "<User 'User.name'>"."""
        dummy = User()
        dummy.name = 'Gabbo'
        assert repr(dummy) == '<User \'Gabbo\'>'

import pytest
from wtforms import ValidationError
from app.auth.forms import (
    EditUserForm,
    RegistrationForm,
    ResendConfirmationForm,
    ResetPasswordRequestForm,
    SelectUserForm
)
from app.auth.models import User
from tests.conftest import app, db  # noqa


class TestEditUserFormWithDB:
    """Test custom methods in EditUserForm."""
    def test_validate_current_password(self, app, db):
        """validate_current_password raises exception w/ bad password."""
        user = create_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            tc.post('/auth/login', data=dict(login=user.name,
                                             password='hunter2'),
                    follow_redirects=True)
            form = EditUserForm()
            form.current_password.data = 'turtles'
            with pytest.raises(ValidationError):
                form.validate_current_password(form.current_password)


class TestRegistrationFormWithDB:
    """Test custom methods in RegistrationForm."""
    def test_validate_email_fails_if_email_exists_in_db(self, db):
        """"validate_email raises a ValidationError if email is in db."""
        user = create_dummy_user()
        db.session.add(user)
        form = RegistrationForm()
        form.email.data = user.email
        with pytest.raises(ValidationError):
            form.validate_email(form.email)

    def test_validate_username_fails_if_username_exists_in_db(self, db):
        """validate_username raises a ValidationError if username is in db."""
        user = create_dummy_user()
        db.session.add(user)
        db.session.commit()
        form = RegistrationForm()
        form.username.data = user.name
        with pytest.raises(ValidationError):
            form.validate_username(form.username)


class TestResendConfirmationFormWithDB:
    """Test custom methods in ResendConfirmationForm"""
    def test_validate_email_fails_if_no_account_registered(self, db):
        """validate_email fails if email address not in use."""
        form = ResendConfirmationForm()
        form.email.data = 'nonexistent@dev.null'
        with pytest.raises(ValidationError):
            form.validate_email(form.email)

    def test_validate_email_fails_if_account_already_confirmed(self, db):
        """validate_email fails if associated account is already confirmed."""
        user = create_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        form = ResendConfirmationForm()
        form.email.data = user.email
        with pytest.raises(ValidationError):
            form.validate_email(form.email)


class TestResetPasswordRequestFormWithDB:
    """Test custom methods in ResetPasswordRequestForm"""
    def test_validate_email(self, db):
        """validate_email raises ValidationError if address not in db."""
        user = create_dummy_user()
        db.session.add(user)
        db.session.commit()
        form = ResetPasswordRequestForm()
        form.email.data = 'notahoneypot@nsa.gov'
        with pytest.raises(ValidationError):
            form.validate_email(form.email)


class TestSelectUserForm:
    """Test custom methods in SelectUserForm."""
    def test_load_users(self, db):
        """load_users loads all users in database into select_user.choices."""
        user1 = User()
        user1.name = 'Bob'
        user1.email = 'dobbs@subgenius.org'
        user2 = User()
        user2.name = 'Eris'
        user2.email = 'kallisti@discordia.org'
        db.session.add(user1)
        db.session.add(user2)
        form = SelectUserForm()
        form.load_users()
        print(form.select_user.choices)
        assert (user1.id, user1.name) in form.select_user.choices
        assert (user2.id, user2.name) in form.select_user.choices


def create_dummy_user(
        email='gullible@bash.org',
        name='AzureDiamond',
        password='hunter2'):
    user = User()
    user.name = name
    user.set_password(password)
    user.email = email
    return user

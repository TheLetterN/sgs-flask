import unittest
from wtforms import ValidationError
from app import create_app, db
from app.auth.forms import RegistrationForm, ResendConfirmationForm
from app.auth.models import User


def create_dummy_user(
        email='gullible@bash.org',
        name='AzureDiamond',
        password='hunter2'):
    user = User()
    user.name = name
    user.set_password(password)
    user.email = email
    return user


class TestRegistrationFormWithDB(unittest.TestCase):
    """Test custom methods in RegistrationForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_email_fails_if_email_exists_in_db(self):
        """"validate_email raises a ValidationError if email is in db."""
        user = create_dummy_user()
        db.session.add(user)
        form = RegistrationForm()
        form.email.data = user.email
        with self.assertRaises(ValidationError):
            form.validate_email(form.email)

    def test_validate_username_fails_if_username_exists_in_db(self):
        """validate_username raises a ValidationError if username is in db."""
        user = create_dummy_user()
        db.session.add(user)
        db.session.commit()
        form = RegistrationForm()
        form.username.data = user.name
        with self.assertRaises(ValidationError):
            form.validate_username(form.username)


class TestResendConfirmationFormWithDB(unittest.TestCase):
    """Test custom methods in ResendConfirmationForm"""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_email_fails_if_no_account_registered(self):
        """validate_email fails if email address not in use."""
        form = ResendConfirmationForm()
        form.email.data = 'nonexistent@dev.null'
        with self.assertRaises(ValidationError):
            form.validate_email(form.email)

    def test_validate_email_fails_if_account_already_confirmed(self):
        """validate_email fails if associated account is already confirmed."""
        user = create_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        form = ResendConfirmationForm()
        form.email.data = user.email
        with self.assertRaises(ValidationError):
            form.validate_email(form.email)


if __name__ == '__main__':
    unittest.main()

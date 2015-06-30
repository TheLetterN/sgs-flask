import unittest
from wtforms import ValidationError
from app import create_app, db
from app.auth.forms import RegistrationForm
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


class TestRegistrationForm(unittest.TestCase):
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
        form = RegistrationForm()
        form.username.data = user.name
        with self.assertRaises(ValidationError):
            form.validate_username(form.username)


if __name__ == '__main__':
    unittest.main()

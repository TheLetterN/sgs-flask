import unittest
from wtforms import ValidationError
from app import create_app, db
from app.auth.forms import EditUserForm, RegistrationForm, \
    ResendConfirmationForm, ResetPasswordRequestForm, SelectUserForm
from app.auth.models import User


class TestEditUserFormWithDB(unittest.TestCase):
    """Test custom methods in EditUserForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_current_password(self):
        """validate_current_password raises exception w/ bad password."""
        user = create_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            tc.post('/auth/login', data=dict(
                login=user.name,
                password='hunter2'
                ), follow_redirects=True)
            form = EditUserForm()
            form.current_password.data = 'turtles'
            with self.assertRaises(ValidationError):
                form.validate_current_password(form.current_password)


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


class TestResetPasswordRequestFormWithDB(unittest.TestCase):
    """Test custom methods in ResetPasswordRequestForm"""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_email(self):
        """validate_email raises ValidationError if address not in db."""
        user = create_dummy_user()
        db.session.add(user)
        db.session.commit()
        form = ResetPasswordRequestForm()
        form.email.data = 'notahoneypot@nsa.gov'
        with self.assertRaises(ValidationError):
            form.validate_email(form.email)


class TestSelectUserForm(unittest.TestCase):
    """Test custom methods in SelectUserForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_load_users(self):
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
        self.assertTrue((user1.id, user1.name) in form.select_user.choices)
        self.assertTrue((user2.id, user2.name) in form.select_user.choices)


def create_dummy_user(
        email='gullible@bash.org',
        name='AzureDiamond',
        password='hunter2'):
    user = User()
    user.name = name
    user.set_password(password)
    user.email = email
    return user


if __name__ == '__main__':
    unittest.main()

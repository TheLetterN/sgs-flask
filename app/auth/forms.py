from flask.ext.login import current_user
from flask.ext.wtf import Form
from wtforms import BooleanField, PasswordField, StringField, SelectField, \
    SubmitField, ValidationError
from wtforms.validators import Email, EqualTo, InputRequired, Length, Regexp
from app.auth.models import User


class EditUserForm(Form):
    """Form for editing user's information.

    Attributes:
        email1 (StringField): Field for changing user's email address.
        email2 (StringField): Field for verifying changes to email address.
        new_password1 (PasswordField): Field for changing user's password.
        new_password2 (PasswordField): Field for verifying changes to user's
                                       password.
        current_password: Field for user's current password, which is required
                          to make changes to their account.
        submit (SubmitField): Submit button.
    """
    email1 = StringField(
        'New Email',
        validators=[Email(), Length(1, 254)])
    email2 = StringField(
        'Confirm Email',
        validators=[EqualTo('email1', message="Email addresses must match!")])
    new_password1 = PasswordField(
        'New Password',
        validators=[Length(0, 64)])
    new_password2 = PasswordField(
        'Confirm Password',
        validators=[EqualTo('new_password1', message='Passwords must match!')])
    current_password = PasswordField(
        'Current Password',
        validators=[Length(1, 64)])
    submit = SubmitField('Submit Changes')

    def validate_current_password(self, field):
        """Raise an exception if current_password isn't the user's password.

        Raises:
            ValidationError: current_password's contents must match the
                             password of the logged in user.
        """
        if not current_user.verify_password(field.data):
            raise ValidationError('Password is incorrect!')


class LoginForm(Form):
    """Form for logging in.

    Attributes:
        password (PasswordField): Field for the user's password.
        remember_me (BooleanField): Checkbox to allow user to remain logged
                                    in between visits.
        submit (SubmitField): Submit button.
        username (StringField) The user's name or nickname on the site.
    """
    password = PasswordField(
        'Password',
        validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')
    username = StringField(
        'User Name',
        validators=[InputRequired(), Length(1, 64)])


class ManageUserForm(Form):
    """Form to allow user with MANAGE_USERS permission to edit user data.

    Attributes:
        manage_permissions (BooleanField): Whether or not user is allowed to
                                           change users' permissions.
        manage_seeds (BooleanField): Whether or not the user is allowed to
                                     manage the seeds database.
        submit (SubmitField): Submit button.
    """
    # Account Information
    email1 = StringField(
        'New Email',
        validators=[Email(), Length(1, 254)])
    email2 = StringField(
        'Confirm Email',
        validators=[EqualTo('email1', message='Email addresses must match!')])
    password1 = PasswordField(
        'New Password',
        validators=[Length(0, 64)])
    password2 = PasswordField(
        'Confirm Password',
        validators=[EqualTo('password1', message='Passwords must match!')])
    username1 = StringField(
        'New Username',
        validators=[
            Length(1, 64),
            Regexp('^[A-Za-z0-9][A-Za-z0-9_. ]*$', 0,
                   'Username must begin with a letter or number,  and may only'
                   ' contain letters, numbers, spaces, dots, dashes, and'
                   ' underscores.')])
    username2 = StringField(
        'Confirm Username',
        validators=[EqualTo('username1', message='Usernames must match!')])
    # Permissions
    manage_users = BooleanField('Manage Users')
    manage_seeds = BooleanField('Manage Seeds')
    # Submit button
    submit = SubmitField('Submit Changes')


class RegistrationForm(Form):
    """Form for new users to register accounts.

    Attributes:
        email (StringField): Field for user's email address.
        email2 (StringField): Field to verify user's email address.
        password (PasswordField): Field for user's password.
        password2 (PasswordField): Field to verify user's password.
        submit (SubmitField): Submit button.
        username (StringField): User's name or nickname to use on the site.
    """
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    email2 = StringField(
        'Confirm Email',
        validators=[EqualTo('email', message='Email addresses do not match!'),
                    InputRequired()])
    password = PasswordField(
        'Password',
        validators=[InputRequired(), Length(1, 64)])
    password2 = PasswordField(
        'Confirm Password',
        validators=[EqualTo('password', message='Passwords do not match!'),
                    InputRequired()])
    submit = SubmitField('Register')
    username = StringField(
        'Username',
        validators=[
            InputRequired(),
            Length(1, 64),
            Regexp('^[A-Za-z0-9][A-Za-z0-9_. ]*$', 0,
                   'Username must begin with a letter or number,  and may only'
                   ' contain letters, numbers, spaces, dots, dashes, and'
                   ' underscores.')])

    def validate_email(self, field):
        """Raise an exception if email address is already in use.

        Raises:
            ValidationError: Email address can't already be in the database.
        """
        if User.query.filter_by(email=field.data).first() is not None:
            raise ValidationError('This email address is already in use,'
                                  ' please use a different one.')

    def validate_username(self, field):
        """Raise an exception if username is already in use.

        Raises:
            ValidationError: Username can't already be in the database.
        """
        if User.query.filter_by(name=field.data).first() is not None:
            raise ValidationError('Username already in use,'
                                  ' please choose another.')


class ResendConfirmationForm(Form):
    """Form for sending a new confirmation email.

    Attributes:
        email (StringField): User's email address.
        submit (SubmitField): Submit button.
    """
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    submit = SubmitField('Send')

    def validate_email(self, field):
        """Raise an exception if email address cannot be confirmed.

        Raises:
            ValidationError: Email address must belong to a user with an
                             unconfirmed account.
        """
        user = User.query.filter_by(email=field.data).first()
        if user is None:
            raise ValidationError('There is no account associated with this '
                                  'email address!')
        elif user.confirmed is True:
            raise ValidationError('The account associated with this email '
                                  'address has already been confirmed!')


class ResetPasswordForm(Form):
    """Form for resetting a user's password.

    Attributes:
        email (StringField): Field for the user's email address.
        password1 (PasswordField): Field for the user's password.
        password2 (PasswordField): Field to verify the user's Password.
        submit (SubmitField): Submit button.
    """
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    password1 = PasswordField(
        'New Password',
        validators=[InputRequired(), Length(1, 64)])
    password2 = PasswordField(
        'Confirm Password',
        validators=[EqualTo('password1', message='Passwords must match!')])
    submit = SubmitField('Reset Password')


class ResetPasswordRequestForm(Form):
    """Form for the user to request a password reset.

    Attributes:
        email (StringField): Field for the user's email address.
        submit (SubmitField): Submit button.
    """
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, field):
        """Raise an exception if email address is not in the database.

        Raises:
            ValidationError: A user with this email address must be in the
                             database.
        """
        user = User.query.filter_by(email=field.data).first()
        if user is None:
            raise ValidationError('There is no account associated with this '
                                  'email address!')


class SelectUserForm(Form):
    """Form for selecting a user from the database to use with other forms.

    Attributes:
        select_user (SelectField): Select field to pick a user from the
                                   database.
        submit (SubmitField): Submit button.
    """
    select_user = SelectField('Select User', coerce=int)
    submit = SubmitField('Submit')

    def load_users(self):
        """Populate select_user with users from the database."""
        self.select_user.choices = [(user.id, user.name) for user in
                                    User.query.order_by('name')]

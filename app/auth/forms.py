from flask.ext.login import current_user
from flask.ext.wtf import Form
from wtforms import BooleanField, PasswordField, StringField, SubmitField, \
    ValidationError
from wtforms.validators import Email, EqualTo, InputRequired, Length, Regexp
from app.auth.models import User


class EditUserForm(Form):
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
        if not current_user.verify_password(field.data):
            raise ValidationError('Password is incorrect!')


class LoginForm(Form):
    password = PasswordField(
        'Password',
        validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')
    username = StringField(
        'User Name',
        validators=[InputRequired(), Length(1, 64)])


class RegistrationForm(Form):
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
        if User.query.filter_by(email=field.data).first() is not None:
            raise ValidationError('This email address is already in use,'
                                  ' please use a different one.')

    def validate_username(self, field):
        if User.query.filter_by(name=field.data).first() is not None:
            raise ValidationError('Username already in use,'
                                  ' please choose another.')


class ResendConfirmationForm(Form):
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    submit = SubmitField('Send')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user is None:
            raise ValidationError('There is no account associated with this '
                                  'email address!')
        elif user.confirmed is True:
            raise ValidationError('The account associated with this email '
                                  'address has already been confirmed!')


class ResetPasswordForm(Form):
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
    email = StringField(
        'Email Address',
        validators=[Email(), InputRequired(), Length(1, 254)])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user is None:
            raise ValidationError('There is no account associated with this '
                                  'email address!')

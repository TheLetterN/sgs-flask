from flask.ext.wtf import Form
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
    ValidationError)
from wtforms.validators import Email, EqualTo, InputRequired, Length, Regexp
from app.auth.models import User


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
        'Confirm Email Address',
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

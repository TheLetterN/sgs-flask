from flask.ext.wtf import Form
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import InputRequired, Length


class LoginForm(Form):
    username = StringField(
        'User Name',
        validators=[InputRequired(), Length(1, 64)])
    password = PasswordField(
        'Password',
        validators=[InputRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

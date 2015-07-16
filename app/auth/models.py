from flask import current_app
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin
from app import db, login_manager
from app.email import send_email


class Permission(object):
    """Permission defines permissions to be used by the User class.

    A permission represents a task the user requires permission to perform,
    and each permission's value corresponds to a bit in the integer stored in
    User.permissions.

    Attributes:
        MANAGE_SEEDS (int): This bit is set if the user is allowed to manage
                            the seeds database.
    """
    MANAGE_SEEDS = 0b1


class User(UserMixin, db.Model):
    """Table representing registered users.

    Attributes:
        id (int): Unique key generated when a new User is added to the
                  database.
        confirmed (bool): Whether or not the user's account is confirmed.
        email (str): The user's email address.
        name (str): The name or nickname the user will be represented by on
                    the website.
        password_hash (str): A one-way hashed version of the user's password.
        permissions (int): An integer representing bits corresponding to
                           Permission values.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    confirmed = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(254), unique=True)
    name = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    permissions = db.Column(db.Integer)

    def confirm_account(self, token):
        """Confirm a user's account.

        Args:
            token (str): An encrypted confirmation token string created by
                         generate_account_confirmation_token

        Returns:
            bool: True if token is valid and id belongs to this user, False if
                  not.
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        return True

    def confirm_new_email(self, token):
        """Confirm a user's request to change their email address.

        If a valid token is supplied, it will also set the user's email
        address to the new address contained within the token.

        Args:
            token (str): An encrypted token string containing the user's id
                         and the new email address they would like to set.

        Returns:
            bool: True if token is valid and id belongs to this user, False if
                  not.
        """
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('id') != self.id:
            return False
        else:
            self.email = data.get('new_email')
            return True

    def generate_account_confirmation_token(self, expiration=3600):
        """Create an encrypted token for account verification.

        Args:
            expiration (int): Timespan in which the token will be valid.
                              default = 3600 seconds = 60 minutes = 1 hour

        Returns:
            str: An encrypted, time-limited token string containing the user's
                 id, to use for verifying the user's account.
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def generate_new_email_token(self, new_email, expiration=3600):
        """Create an encrypted token for setting a new email address.

        Args:
            new_email (str): The new email address the user wishes to bind
                             to their account.
            expiration (int): Timespan in which token will be valid.
                              default = 3600 seconds = 60 minutes = 1 hour

        Returns:
            str: An encrypted, time-limited token string containing the user's
                 id and the email address they wish to bind to their account.
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'id': self.id, 'new_email': new_email})

    def generate_password_reset_token(self, expiration=3600):
        """Create an encrypted token to allow user to reset their password.

        Args:
            expiration (int): Timespan in which token will be valid.
                              default = 3600 seconds = 60 minutes = 1 hour

        Returns:
            str: An encrypted, time-limited token string containing the user's
                 id, to use to restrict password reset to people with access
                 this user's email address. (Hopefully only this user!)
        """
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset_password': self.id})

    @property
    def password(self):
        """Prevent use of 'password' as a readable attribute.

        Raises:
            AttributeError: Password should not be a readable attribute, so
                            attempting to read it should raise this exception.
        """
        raise AttributeError('password is not a readable attribute!')

    @password.setter
    def password(self, password):
        """Sets password_hash."""
        self.set_password(password)

    def reset_password(self, token, password):
        """Resets password to new password if the token passed is valid."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset_password') != self.id:
            return False
        else:
            self.set_password(password)
            return True

    def send_account_confirmation_email(self):
        token = self.generate_account_confirmation_token()
        send_email(self.email, 'Confirm Your Account',
                   'auth/email/confirmation', user=self, token=token)

    def send_reset_password_email(self):
        token = self.generate_password_reset_token()
        send_email(self.email, 'Reset Your Password',
                   'auth/email/reset_password', user=self, token=token)

    def send_new_email_confirmation(self, new_email):
        token = self.generate_new_email_token(new_email)
        send_email(new_email, 'Confirm New Email Address',
                   'auth/email/confirm_new_email', user=self, token=token)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


def get_user_from_confirmation_token(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except:
        raise ValueError('Token is malformed or invalid!')
    if 'confirm' in data:
        user = User.query.filter_by(id=data['confirm']).first()
        if user.confirmed is True:
            raise ValueError('The user for this token is already confirmed!')
        else:
            return user
    else:
        raise KeyError('Confirmation token toes not contain valid data!')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

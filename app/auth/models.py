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

    Note:
        Attribute names should be in the form of an action the user can or
        cannot do, as their primary use will be via User.can(), so it makes
        the most sense semantically to have attribute names like "HERD_CATS"
        or "DANCE_THE_POLKA".

    Attributes:
        MANAGE_PERMISSIONS (int): This bit is set if the user is allowed to
                                  manage the permissions of other users.
        MANAGE_SEEDS (int): This bit is set if the user is allowed to manage
                            the seeds database.
    """
    MANAGE_PERMISSIONS = 0b1
    MANAGE_SEEDS = 0b10


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
    permissions = db.Column(db.Integer, default=0)

    def can(self, permission):
        """Verify if a user has a permission.

        Args:
            permission (Permission): A permission to check against this user's
                                     permissions.
        Returns:
            bool: True if user has the permission, False if not.
        """
        if self.permissions & permission > 0:
            return True
        else:
            return False

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

    def grant_permission(self, permission):
        """Grant a permission to this user.

        Args:
            permission (int): An integer with a single set bit (such as 0b10)
                              representing a permission. Normally this would
                              be a constant from the Permission class.
        """
        self.permissions |= permission

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
        """Set password_hash.

        Note:
            This mostly exists as a convenience. I advise against using it and
            recommend using set_password() instead, as using password = x does
            not readily convey the fact that the password is being run through
            a function before being stored.

        Args:
            password (str): The password to hash and store in password_hash.
        """
        self.set_password(password)

    def reset_password(self, token, password):
        """Set a new password if given a valid token.

        Args:
            token (str): An encrypted token containing the user's id, which
                         is used to ensure that a user attempting to reset
                         their password has access to the email account
                         associated with the user account they are trying to
                         (re)gain access to.
            password (str): A new password to set if the token proves valid.

        Returns:
            bool: True if token is valid for this user, False if not.
        """
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

    def revoke_permission(self, permission):
        """Removes a permission from this user.

        Args:
            permission (int): An integer with a single set bit representing a
            permission. Normally this would be a Permission attribute.
        """
        if self.permissions & permission > 0:
            self.permissions ^= permission

    def send_account_confirmation_email(self):
        """Send an account confirmation email to this user.

        An account confirmation token is generated and used in an email
        containing a link to the account confirmation page, which utilizes
        the token to verify that they recieved the email, and thus hopefully
        own the email address associated with their account, and that they
        are either human or at least a very well-trained swarm of bees.
        """
        token = self.generate_account_confirmation_token()
        send_email(self.email, 'Confirm Your Account',
                   'auth/email/confirmation', user=self, token=token)

    def send_reset_password_email(self):
        """Send an email with a token allowing user to reset their password.

        A password reset verification token is generated and used in an email
        containing a link to the password reset page, which utilizes the token
        to verify that they recieved the email before allowing them to reset
        their account's password.
        """
        token = self.generate_password_reset_token()
        send_email(self.email, 'Reset Your Password',
                   'auth/email/reset_password', user=self, token=token)

    def send_new_email_confirmation(self, new_email):
        """Send an email with a token allowing user to change email address.

        A token containing the user's id and the new email they would like to
        use is generated and emailed to the new email address in order to
        ensure that the new email address is valid and accessible by the user
        before binding it to their account.
        """
        token = self.generate_new_email_token(new_email)
        send_email(new_email, 'Confirm New Email Address',
                   'auth/email/confirm_new_email', user=self, token=token)

    def set_password(self, password):
        """Hash and set the user's password.

        Args:
            password (str): The password to be hashed and set to
                            password_hash.
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """Compare a password to the hashed password stored in password_hash.

        Args:
            password (str): The password to be compared to the one stored in
                            password_hash.

        Returns:
            bool: True if it's the same password, False if not.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


def get_user_from_confirmation_token(token):
    """Load a user from the database using the id stored in token.

    This is needed as part of the account confirmation process, because new
    users cannot log in until their account is confirmed.

    Args:
        token (str): Account confirmation token containing a user id.

    Returns:
        user (User): The user account to be confirmed.

    Raises:
        ValueError: If token is invalid, or user is already confirmed.
        KeyError: If token loads fine but doesn't contain the 'confirm' key.
    """
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
    """Allow Flask-Login to load a user.

    Args:
        user_id (int): A user's id number.

    Returns:
        User: The user whose id is user_id.
    """
    return User.query.get(int(user_id))

# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


from datetime import datetime, timedelta
from flask import current_app
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin
from app import db, login_manager
from app.email import send_email


class EmailRequest(db.Model):
    """Table for tracking email requests.

    The primary use of this table is to keep track of various email requests
    in order to prevent malicious use of functionalities that send emails to
    users, such as spamming confirmation or password reset requests.

    Attributes:
        id (int): Primary key for an EmailRequest object.
        sender (str): A string representing what functionality is requesting
                      to send an email, such as 'confirm account'.
        time (datetime): The datetime when this request was made.
        user_id (int): ID of the user this request belongs to.
    """
    __tablename__ = 'email_requests'
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(32))
    time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, sender, time=None):
        """Create an EmailRequest record.

        Args:
            sender (str): A string representing the functionality requesting
                          to send an email.
            time (datetime): The time in UTC at which the request was made.
        """
        if time is None:
            time = datetime.utcnow()
        self.sender = sender
        self.time = time

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.sender)


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
        MANAGE_USERS (int): This bit is set if the user is allowed to edit the
                            data/permissions of other users.
        MANAGE_SEEDS (int): This bit is set if the user is allowed to manage
                            the seeds database.
    """
    MANAGE_USERS = 0b1
    MANAGE_SEEDS = 0b10


class User(UserMixin, db.Model):
    """Table representing registered users.

    Attributes:
        id (int): Unique key generated when a new User is added to the
                  database.
        confirmed (bool): Whether or not the user's account is confirmed.
        email (str): The user's email address.
        email_requests (relationship): EmailRequest entries for this user.
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
    email_requests = db.relationship('EmailRequest', lazy='dynamic')
    name = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    permissions = db.Column(db.Integer, default=0)

    def __init__(self):
        self.permissions = 0

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

    def email_request_too_many(self, sender, days=None, maximum=None):
        """Check if too many requests have been within days.

        Args:
            sender (str): String representing the functionality trying to send
                          the email, such as 'confirm account'.
            days (int): Number of days before request in which requests count
                        towards the limit.
            maximum (int): Maximum number of requests to allow over duration
                           specified by days.

        Returns:
            bool: True if number of requests has already hit max for the given
                  duration.
            bool: False if number of requests is below max for given duration.
        """
        if days is None:
            days = current_app.config['ERFP_DAYS_TO_TRACK']
        if maximum is None:
            maximum = current_app.config['ERFP_MAX_REQUESTS']
        if self.email_requests.filter_by(sender=sender).count() <= maximum:
            return False
        else:
            self.prune_email_requests(sender=sender, days=days)
            if self.email_requests.filter_by(sender=sender).count() <= maximum:
                return False
            else:
                return True

    def email_request_too_soon(self, sender, minutes=None):
        """Check if request to send email is too soon after previous one.

        Args:
            sender (str): String representing the functionality trying to send
                          the email, such as 'confirm account'.
            minutes (int): How many minutes must pass between request.

        Returns:
            bool: True if less time has passed than specified by minutes.
            bool: False if more time has passed than specified by minutes.
        """
        if minutes is None:
            minutes = current_app.config['ERFP_MINUTES_BETWEEN_REQUESTS']
        sender_query = self.email_requests.filter_by(sender=sender)
        latest = sender_query.order_by(db.desc(EmailRequest.time)).first()
        if latest is None:
            return False
        if datetime.utcnow() - latest.time < timedelta(minutes=minutes):
            return True
        else:
            return False

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

    def log_email_request(self, sender, time=None):
        """Append a record of an email request to User.email_requests

        Args:
            sender (str): A string representing the functionality that
                          requested to send an email.
            time (datetime): The time in UTC at which the request was sent.
        """
        if time is None:
            time = datetime.utcnow()
        self.email_requests.append(EmailRequest(sender, time))

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

    def prune_email_requests(self, sender, days=None):
        """Clear out old email requests.

        Args:
            sender (str): String representing the functionality requesting to
                          send an email.
            days (int): Number of days to store logged requests.
        """
        now = datetime.utcnow()
        reqs = self.email_requests.filter_by(sender=sender).all()
        pruned = False
        for req in reqs:
            if now - req.time > timedelta(days=days):
                pruned = True
                db.session.delete(req)
        if pruned:
            db.session.commit()

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

    def send_account_confirmation_email(self):  # pragma: no cover
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

    def send_reset_password_email(self):  # pragma: no cover
        """Send an email with a token allowing user to reset their password.

        A password reset verification token is generated and used in an email
        containing a link to the password reset page, which utilizes the token
        to verify that they recieved the email before allowing them to reset
        their account's password.
        """
        token = self.generate_password_reset_token()
        send_email(self.email, 'Reset Your Password',
                   'auth/email/reset_password', user=self, token=token)

    def send_new_email_confirmation(self, new_email):  # pragma: no cover
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
        if user.confirmed:
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

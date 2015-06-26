from flask.ext.login import UserMixin
from werkzeug import generate_password_hash, check_password_hash
from app import db, login_manager


class Role(db.Model):
    """Table representing user roles.

    Database Columns:
        id -- Auto-generated ID number.
        name -- What we call the role.
    Relationships:
        users -- backrefs 'role' to User.
    """
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


class User(UserMixin, db.Model):
    """Table representing registered users.

    Database Columns:
        id -- Identification number automatically generated by database.
        email -- The user's email address.
        name -- The name/nickname the user uses on the site.
        password_hash -- Hashed user password.
        role_id -- ID number of a Role.
    Relationships:
        role -- backref from Role.
    Methods:
        password -- Saves a hashed password to password_hash.
        verify_password -- Returns True if password is correct.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True)
    name = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute!')

    @password.setter
    def password(self, password):
        """This is a convenience function so you can use User.password = x"""
        # IMO, this method of setting password_hash is too opaque.
        # User.set_password makes it more obvious that the password is being
        # acted on by a function, so I recommend that instead. -N
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
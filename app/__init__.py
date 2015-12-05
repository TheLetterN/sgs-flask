# -*- coding: utf-8 -*-


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


"""SGS Flask

This is the main application module for SGS Flask, a Flask implementation
of the website for Swallowtail Garden Seeds.
"""

from titlecase import titlecase
from flask import Flask
from flask.ext.login import AnonymousUserMixin, LoginManager
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from config import CONFIG


class Anonymous(AnonymousUserMixin):
    """Anonymous user for flask-login that mocks some attributes of User."""
    def __init__(self):
        self.name = 'Guest'

    def can(self, permission=None):
        """Anonymous users can't do squat, always return False!"""
        return False


db = SQLAlchemy()
mail = Mail()


login_manager = LoginManager()
login_manager.anonymous_user = Anonymous
login_manager.session_protection = 'basic'
login_manager.login_view = 'auth.login'


def make_breadcrumbs(*args):
    """Create a 'trail of breadcrumbs' to include in pages.

    Args:
        args (tuple): A tuple containing tuples in the format (route, title)

    Returns:
        list: A list containing
    """
    if all(isinstance(arg, tuple) and len(arg) == 2 for arg in args):
        trail = list()
        for arg in args:
            trail.append('<a href="{0}">{1}</a>'.
                         format(arg[0], arg[1]))
        return trail
    else:
        raise ValueError('Could not parse arguments. Please make sure your '
                         'arguments are tuples formatted (route, page title)!')


def dbify(string):
    """Format a string to be stored in the database.

    Args:
        string (str): The string to be converted.

    Returns:
        str: A string formatted for database usage.
    """
    return titlecase(string.lower().strip())


def create_app(config_name):
    """Create a Flask instance based on a Config subclass.

    Args:
        config_name (str): The config mode we want to load. Options for this
            are enumerated in the CONFIG dictionary in ``/config.py``.

    Returns:
        app (Flask): A Flask application instance with the config options
            specified by the Config subclass specified by
            ``CONFIG[config_name]``.
    """
    app = Flask(__name__)
    app.config.from_object(CONFIG[config_name])
    CONFIG[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from .auth import auth as auth_blueprint
    from .main import main as main_blueprint
    from .seeds import seeds as seeds_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(seeds_blueprint, url_prefix='/seeds')

    return app

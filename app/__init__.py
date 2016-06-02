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

import json
import os
import pyphen
from flask import Flask, current_app
from flask.ext.login import AnonymousUserMixin, LoginManager
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from slugify import slugify
from config import CONFIG
from .pending import Pending
from .redirects import RedirectsFile


# Initialize the hyphenator here so the cache will be global.
hyphenator = pyphen.Pyphen(lang='en_US')


def hyphenate(text):
    """Return a soft-hyphenated version of text."""
    if text:
        return hyphenator.inserted(text, hyphen='&shy;')
    else:
        return text


def get_index_nav(filename=None):
    """Return a dict of tuples used for showing links to Indexes in the nav."""
    if not filename:
        filename = os.path.join(
            current_app.config.get('JSON_FOLDER'), 'nav', 'indexes.json'
        )
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as ifile:
            d = json.loads(ifile.read())
            fixed = {int(k): d[k] for k in d}
            return fixed
    else:
        return {}


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


class Anonymous(AnonymousUserMixin):
    """Anonymous user for flask-login that mocks some attributes of User."""
    def __init__(self):
        self.name = 'Guest'
        self.permissions = 0

    def can(self, permission=None):
        """Anonymous users can't do squat, always return False!"""
        return False

db = SQLAlchemy()
mail = Mail()


login_manager = LoginManager()
login_manager.anonymous_user = Anonymous
login_manager.session_protection = 'basic'
login_manager.login_view = 'auth.login'


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

    # Add redirects
    rdf = RedirectsFile(app.config.get('REDIRECTS_FILE'))
    if rdf.exists():
        rdf.load()
        rdf.add_all_to_app(app)

    # Clear pending changes messages
    pending = Pending(app.config.get('PENDING_FILE'))
    if pending.has_content():  # pragma: no cover
        pending.clear()
        pending.save()

    # Make things available to Jinja
    app.add_template_global(slugify, 'slugify')
    app.add_template_global(Permission, 'Permission')
    app.add_template_global(hyphenate, 'hyphenate')
    app.add_template_global(get_index_nav, 'get_index_nav')

    return app

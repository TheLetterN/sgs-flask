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

import datetime
import json
from pathlib import Path


import stripe
from flask import Flask, current_app, render_template, session
from flask_login import AnonymousUserMixin, current_user, LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from inflection import pluralize
from slugify import slugify
from sqlalchemy_searchable import make_searchable

from config import CONFIG
from .pending import Pending
from .redirects import RedirectsFile


def html_fractions(s):
    """Convert fractions in string to their html equivalent."""
    return s.replace(
        '1/4', '&frac14;'
    ).replace(
        '1/2', '&frac12;'
    ).replace(
        '3/4', '&frac34;'
    ).replace(
        '1/3', '&#8531;'
    ).replace(
        '2/3', '&#8532;'
    ).replace(
        '1/5', '&#8533;'
    ).replace(
        '2/5', '&#8534;'
    ).replace(
        '3/5', '&#8535;'
    ).replace(
        '4/5', '&#8536;'
    ).replace(
        '1/6', '&#8537;'
    ).replace(
        '5/6', '&#8538;'
    ).replace(
        '1/8', '&#8539;'
    ).replace(
        '3/8', '&#8540;'
    ).replace(
        '5/8', '&#8541;'
    ).replace(
        '7/8', '&#8542;'
    )


def list_to_english(items, last_delimiter=', and '):
    """Return a string listing items with an appropriate last delimiter.

    Args:
        items: A list of strings to convert to a single string.
    """
    items = [str(i) for i in items]
    if len(items) == 2:
        return last_delimiter.replace(',', '').join(items)
    elif len(items) > 1:
        items.append(last_delimiter.join([items.pop(-2), items.pop()]))
        return ', '.join(items)
    else:
        return items.pop()


def load_nav_data(json_file=None):
    if not json_file:
        json_file = Path(
            current_app.config.get('DATA_FOLDER'), 'nav_data.json'
        )
    else:
        json_file = Path(json_file)
    try:
        with json_file.open('r', encoding='utf-8') as ifile:
            items = json.loads(ifile.read())
    except FileNotFoundError:
        items = []
    return items


def estimate_ship_date():
    today = datetime.date.today()
    wd = today.isoweekday()
    if wd < 5:
        sd = today + datetime.timedelta(days=1)
    elif wd == 5:
        sd = today + datetime.timedelta(days=3)
    else:
        sd = today + datetime.timedelta(days=2)
    return sd


def get_ship_date(filename=None):
    if not filename:
        filename ='data/ship_date.dat' 
    try:
        with open(filename, 'r', encoding='utf-8') as ifile:
            s = ifile.read().strip()
            sd = datetime.datetime.strptime(s, '%m/%d/%Y').date()
    except FileNotFoundError:
        print(
            'WARNING: No ship_date.dat found in data! Using estimated '
            'ship date instead, which may be incorrect.'
        )
        sd = estimate_ship_date()
    return sd


def format_ship_date(sd):
    """Format a ship date for display."""
    wd_month = sd.strftime('%A, %B')
    if sd.day %10 == 1 and sd.day %100 != 11:
        suffix = 'st'
    elif sd.day %10 == 2 and sd.day %100 != 12:
        suffix = 'nd'
    elif sd.day %10 == 3 and sd.day %100 != 13:
        suffix = 'rd'
    else:
        suffix = 'th'
    return '{} {}{}'.format(wd_month, sd.day, suffix)


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
make_searchable(options={'remove_symbols': '@"<>-'})
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
    from .seeds import seeds as seeds_blueprint
    from .shop import shop as shop_blueprint
    from .shop.models import Order

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(seeds_blueprint)
    app.register_blueprint(shop_blueprint, url_prefix='/shop')

    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')

    ship_date = format_ship_date(get_ship_date())

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

    def sum_cart_items():
        o = Order.load(current_user)
        try:
            return o.number_of_items
        except:
            return 0

    # Make things available to Jinja
    app.add_template_global(ship_date, 'ship_date')
    app.add_template_global(Permission, 'Permission')
    app.add_template_global(pluralize, 'pluralize')
    app.add_template_global(load_nav_data, 'load_nav_data')
    app.add_template_global(slugify, 'slugify')
    app.add_template_global(sum_cart_items, 'sum_cart_items')

    # Error pages
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    return app

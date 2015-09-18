# -*- coding: utf-8 -*-
"""SGS Flask

This is the main application module for SGS Flask, a Flask implementation
of the website for Swallowtail Garden Seeds.
"""

from flask import Flask
from flask.ext.login import LoginManager
from flask.ext.mail import Mail
from flask.ext.sqlalchemy import SQLAlchemy
from config import CONFIG


db = SQLAlchemy()
mail = Mail()


login_manager = LoginManager()
login_manager.session_protection = 'strong'
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
    app.register_blueprint(seeds_blueprint, url_prefix='/seeds')
    app.register_blueprint(main_blueprint)

    return app

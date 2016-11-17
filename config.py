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


import os
from pathlib import Path
from tempfile import gettempdir

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TEMPDIR = gettempdir()


class Config(object):
    """Base config object containing settings common to all app modes.

    Note:
        ERFP = Email Request Flood Protection variables.

    Attributes:
        ADMINISTRATORS (list): A list of email addresses of site admins.
        ALLOW_CRAWLING: Whether or not to allow pages to be crawled. This
            should be false outside of production mode.
        EMAIL_SUBJECT_PREFIX (str): A prefix to use in generated email
                                    subjects.
        ERFP_DAYS_TO_TRACK (int): How many days to keep track of email
                                  requests before deleting them.
        ERFP_MAX_REQUESTS (int): Maximum number of requests allowed within
                                 the time span dictated by ERFP_DAYS_TO_TRACK.
        ERFP_MINUTES_BETWEEN_REQUESTS (int): Number of minutes to prevent
                                             additional requests after one has
                                             already been made.
        INDEXES_JSON_FILE (str): Name of file to save/load indexes to.
        INFO_EMAIL (str): Email address to send information with.
        PENDING_FILE (str): Location of file listing changes pending restart.
        REDIRECTS_FILE (str): Location of JSON file containing redirects.
        SECRET_KEY (str): Key used by Flask and extensions for encryption.
        SQLALCHEMY_COMMIT_ON_TEARDOWN (bool): Whether or not to commit
                                              changes to database on
                                              teardown.
        SUPPORT_EMAIL (str): Email address for users to contact support.
        SHOW_CULTIVAR_PAGES (bool): Whether or not to show pages for individual
            cultivars.
    """
    try:
        ADMINISTRATORS = os.environ.get('SGS_ADMINISTRATORS').split(', ')
    except AttributeError:
        ADMINISTRATORS = []
    ALLOW_CRAWLING = os.environ.get('SGS_ALLOW_CRAWLING') or False
    ERFP_DAYS_TO_TRACK = os.environ.get('SGS_ERFP_DAYS_TO_TRACK') or 14
    ERFP_DAYS_TO_TRACK = int(ERFP_DAYS_TO_TRACK)
    ERFP_MAX_REQUESTS = os.environ.get('SGS_ERFP_MAX_REQUESTS') or 12
    ERFP_MAX_REQUESTS = int(ERFP_MAX_REQUESTS)
    ERFP_MINUTES_BETWEEN_REQUESTS = os.environ.get(
        'SGS_ERFP_MINUTES_BETWEEN_REQUESTS') or 5
    ERFP_MINUTES_BETWEEN_REQUESTS = int(ERFP_MINUTES_BETWEEN_REQUESTS)
    EMAIL_SUBJECT_PREFIX = os.environ.get('SGS_EMAIL_SUBJECT_PREFIX') or \
        'Swallowtail Garden Seeds - '
    DATA_FOLDER = os.environ.get('SGS_DATA_FOLDER') or \
        os.path.join(BASEDIR, 'data')
    JSON_FOLDER = os.environ.get('SGS_JSON_FOLDER') or \
        os.path.join(BASEDIR, 'json')
    STATIC_FOLDER = os.environ.get('SGS_STATIC_FOLDER') or \
        os.path.join(BASEDIR, 'app', 'static')
    IMAGES_FOLDER = os.environ.get('SGS_IMAGES_FOLDER') or \
        os.path.join(BASEDIR, 'app', 'static', 'images')
    PLANT_IMAGES_FOLDER = os.path.join(IMAGES_FOLDER, 'plants')
    INFO_EMAIL = os.environ.get('SGS_INFO_EMAIL') or \
        'info@swallowtailgardenseeds.com'
    PENDING_FILE = os.environ.get('SGS_PENDING_FILE') or \
        os.path.join(BASEDIR, 'pending.txt')
    REDIRECTS_FILE = os.environ.get('SGS_REDIRECTS_FILE') or \
        os.path.join(BASEDIR, 'redirects.json')
    SECRET_KEY = os.environ.get('SGS_SECRET_KEY') or \
        '\xbdc@:b\xac\xfa\xfa\xd1z[\xa3=\xd1\x9a\x0b&\xe3\x1d5\xe9\x84(\xda'
    SUPPORT_EMAIL = os.environ.get('SGS_SUPPORT_EMAIL') or \
        'support@swallowtailgardenseeds.com'
    # Snipcart stuff
    USE_SNIPCART = True
    SNIPCART_KEY = os.environ.get('SGS_SNIPCART_KEY') or (
        'NmE0NzFlNzQtMmU1Yi00NjhlLThlN2MtYzU5N'
        'jZmN2U0YjM1NjM2MDc3NjM5NTkwNTI4NTUz'
    )
    # Stripe keys
    STRIPE_SECRET_KEY = os.environ.get('SGS_STRIPE_SECRET_KEY') or \
        'sk_test_MmYmxPgaLmMMOIHRfkIhFE6c'
    STRIPE_PUB_KEY = os.environ.get('SGS_STRIPE_PUB_KEY') or \
        'pk_test_xqkd4rqJFhtRRGVoqkWL4cx0'
    # Set to suppress Flask-SQLAlchemy warning. May need to change later.
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    if os.environ.get('SGS_SQLALCHEMY_ECHO'):
        SQLALCHEMY_ECHO = True
    else:
        SQLALCHEMY_ECHO = False
    if os.environ.get('SGS_SHOW_CULTIVAR_PAGES'):
        SHOW_CULTIVAR_PAGES = True
    else:
        SHOW_CULTIVAR_PAGES = False
    NOTY_INSTALLED = Path('app/static/scripts/noty').exists()

    # Set SERVER_NAME during dev. Unset if in production!
    SERVER_NAME= os.environ.get('SGS_SERVER_NAME') or 'localhost:5000'

    @staticmethod
    def init_app(app):
        app.jinja_env.trim_blocks = True
        app.jinja_env.lstrip_blocks = True


class DevelopmentConfig(Config):
    """Contains settings for running app in development mode.

    This is the default mode we run our application in during development.
    Running the server or shell from ``manage.py`` uses this mode.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DEV_DATABASE_URI')


class TestingConfig(Config):
    """Settings for running app in testing mode.

    Our test use this mode to keep from interfering with databases/files used
    by other modes.
    """
    LOGIN_DISABLED = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    JSON_FOLDER = os.path.join(TEMPDIR, 'json')
    PENDING_FILE = os.path.join(TEMPDIR, 'pending.txt')
    REDIRECTS_FILE = os.path.join(TEMPDIR, 'redirects.json')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_TEST_DATABASE_URI')


class ProductionConfig(Config):
    """Settings for running app in production mode.

    This is the mode we will use when finally running our app on a proper
    web server via a Web Server Gateway Interface (WSGI) instead of via
    Flask's limited built-in server.
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DATABASE_URI')
    ALLOW_CRAWLING = os.environ.get('SGS_ALLOW_CRAWLING') or True
    #Do not use test keys for Stripe in production!
    STRIPE_SECRET_KEY = os.environ.get('SGS_STRIPE_SECRET_KEY')
    STRIPE_PUB_KEY = os.environ.get('SGS_STRIPE_PUB_KEY')


CONFIG = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

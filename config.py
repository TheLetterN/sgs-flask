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
from tempfile import gettempdir

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TEMPDIR = gettempdir()


class Config(object):
    """Base config object containing settings common to all app modes.

    Note:
        ERFP = Email Request Flood Protection variables.

    Attributes:
        ADMINISTRATORS (list): A list of email addresses of site admins.
        EMAIL_SUBJECT_PREFIX (str): A prefix to use in generated email
                                    subjects.
        ERFP_DAYS_TO_TRACK (int): How many days to keep track of email
                                  requests before deleting them.
        ERFP_MAX_REQUESTS (int): Maximum number of requests allowed within
                                 the time span dictated by ERFP_DAYS_TO_TRACK.
        ERFP_MINUTES_BETWEEN_REQUESTS (int): Number of minutes to prevent
                                             additional requests after one has
                                             already been made.
        INFO_EMAIL (str): Email address to send information with.
        PENDING_FILE (str): Location of file listing changes pending restart.
        REDIRECTS_FILE (str): Location of JSON file containing redirects.
        SECRET_KEY (str): Key used by Flask and extensions for encryption.
        SQLALCHEMY_COMMIT_ON_TEARDOWN (bool): Whether or not to commit
                                              changes to database on
                                              teardown.
        SUPPORT_EMAIL (str): Email address for users to contact support.
    """
    try:
        ADMINISTRATORS = os.environ.get('SGS_ADMINISTRATORS').split(', ')
    except AttributeError:
        ADMINISTRATORS = []
    ERFP_DAYS_TO_TRACK = os.environ.get('SGS_ERFP_DAYS_TO_TRACK') or 14
    ERFP_DAYS_TO_TRACK = int(ERFP_DAYS_TO_TRACK)
    ERFP_MAX_REQUESTS = os.environ.get('SGS_ERFP_MAX_REQUESTS') or 12
    ERFP_MAX_REQUESTS = int(ERFP_MAX_REQUESTS)
    ERFP_MINUTES_BETWEEN_REQUESTS = os.environ.get(
        'SGS_ERFP_MINUTES_BETWEEN_REQUESTS') or 5
    ERFP_MINUTES_BETWEEN_REQUESTS = int(ERFP_MINUTES_BETWEEN_REQUESTS)
    EMAIL_SUBJECT_PREFIX = os.environ.get('SGS_EMAIL_SUBJECT_PREFIX') or \
        'Swallowtail Garden Seeds - '
    IMAGES_FOLDER = os.path.join(BASEDIR, 'app', 'static', 'images')
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
    #Set to suppress Flask-SQLAlchemy warning. May need to change later.
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    if os.environ.get('SGS_SQLALCHEMY_ECHO'):
        SQLALCHEMY_ECHO = True
    else:
        SQLALCHEMY_ECHO = False

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
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DEV_DATABASE_URI') or \
        'sqlite:///' + os.path.join(BASEDIR, 'development.db')


class TestingConfig(Config):
    """Settings for running app in testing mode.

    Our test use this mode to keep from interfering with databases/files used
    by other modes.
    """
    LOGIN_DISABLED = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    PENDING_FILE = os.path.join(TEMPDIR, 'pending.txt')
    REDIRECTS_FILE = os.path.join(TEMPDIR, 'redirects.json')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_TEST_DATABASE_URI') or \
        'sqlite:///:memory:'


class ProductionConfig(Config):
    """Settings for running app in production mode.

    This is the mode we will use when finally running our app on a proper
    web server via a Web Server Gateway Interface (WSGI) instead of via
    Flask's limited built-in server.
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DATABASE_URI') or \
        'sqlite:///' + os.path.join(BASEDIR, 'sgs.db')


CONFIG = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

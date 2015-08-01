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
        SECRET_KEY (str): Key used by Flask and extensions for encryption.
        SQLALCHEMY_COMMIT_ON_TEARDOWN (bool): Whether or not to commit
                                              changes to database on
                                              teardown.
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
    INFO_EMAIL = os.environ.get('SGS_INFO_EMAIL') or \
        'nicholasp@localhost'   # TODO: Change this address!
    SECRET_KEY = os.environ.get('SGS_SECRET_KEY') or \
        '\xbdc@:b\xac\xfa\xfa\xd1z[\xa3=\xd1\x9a\x0b&\xe3\x1d5\xe9\x84(\xda'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

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
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_TEST_DATABASE_URI') or \
        'sqlite:///' + os.path.join(TEMPDIR, 'testing.db')


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

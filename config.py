import os
from tempfile import gettempdir

basedir = os.path.abspath(os.path.dirname(__file__))
tempdir = gettempdir()


class Config(object):
    SECRET_KEY = os.environ.get('SGS_SECRET_KEY') or \
        '\xbdc@:b\xac\xfa\xfa\xd1z[\xa3=\xd1\x9a\x0b&\xe3\x1d5\xe9\x84(\xda'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    ADMINISTRATORS = os.environ.get('SGS_ADMINISTRATORS')

    @staticmethod
    def init_app(app):
        app.jinja_env.trim_blocks = True
        app.jinja_env.lstrip_blocks = True


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DEV_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'development.db')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_TEST_DATABASE_URI') or \
        'sqlite:///' + os.path.join(tempdir, 'testing.db')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('SGS_DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'sgs.db')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

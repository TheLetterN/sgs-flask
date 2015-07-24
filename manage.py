#!/usr/bin/env python
import os
import pytest
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager, Shell
from app import create_app, db, mail

app = create_app(os.getenv('SGS_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, mail=mail)


@manager.option(
    '-g',
    '--goodbye',
    action='store_true',
    help="I heard a song like this once.")
def hello(goodbye=False):
    """Say hello to your Flask site."""
    if goodbye:
        print('I don\'t know why you say goodbye, I say hello!')
    else:
        print('Why are you talking to a python script?')


@manager.option(
    '-f',
    '--fast',
    action='store_true',
    help="Only run tests that don't access the database/other slow methods.")
@manager.option(
    '-l',
    '--load',
    help='Load and run a specific tests file.')
def test(fast=False, load=None):
    """Run tests. Default runs all tests. See --help for more options. """
    if fast:
        pytest.main('tests/fast_tests')
    elif load is not None:
        pytest.main(load)
    else:
        pytest.main('tests')

manager.add_command('db', MigrateCommand)
manager.add_command('shell', Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()

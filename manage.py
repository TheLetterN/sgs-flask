#!/usr/bin/env python


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
import pytest
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager, Shell
from app import create_app, db, mail
from app.auth.models import User, Permission

app = create_app(os.getenv('SGS_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)

def make_shell_context():
    return dict(app=app, db=db, mail=mail)


@manager.command
def create():
    """Create a new database and add an admin user.
    
    This should only be used during development, never in production!
    """
    db.create_all()
    admin = User()
    db.session.add(admin)
    admin.name = 'admin'
    admin.set_password('sgsadmin')
    admin.email = 'admin@localhost'
    admin.grant_permission(Permission.MANAGE_SEEDS)
    admin.grant_permission(Permission.MANAGE_USERS)
    admin.confirmed = True
    db.session.commit()


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
@manager.option(
    '-v',
    '--verbose',
    action='store_true',
    help='Give verbose test output.')
def test(fast=False, load=None, verbose=False):
    """Run tests. Default runs all tests. See --help for more options. """
    main_arg=''
    if verbose:
        main_arg+= '-v -s '
    if fast:
        main_arg+= 'tests/fast_tests'
    elif load is not None:
        main_arg+= load
    else:
        main_arg+= 'tests'
    pytest.main(main_arg)

manager.add_command('db', MigrateCommand)
manager.add_command('shell', Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()

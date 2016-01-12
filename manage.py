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


import os, sys
import pytest
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager, Shell
from app import create_app, db, mail
from app.auth.models import User, Permission
from app.seeds.excel import SeedsWorkbook
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Cultivar,
    Index,
    Packet,
    Series
)

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
    '-l',
    '--load',
    help='Load an excel spreadsheet with given filename.')
@manager.option(
    '-s',
    '--save',
    help='Save a database dump to an excel spreadsheet with given file name.')
def excel(load=None, save=None):
    """Interact with the excel module to utilize spreadsheets."""
    if load and save:
        raise ValueError('Cannot load and save at the same time!')
    if load:
        if os.path.exists(load):
            wb = SeedsWorkbook(load)
        else:
            raise FileNotFoundError('The file \'{0}\' does not exist!'
                                    .format(load))
        # TODO: Implement loading of files.
    if save:
        if os.path.exists(save):
            print('WARNING: The file {0} exists. Would you like to overwrite '
                  'it?'.format(save))
            wb = None
            while wb is None:
                choice = input('Y/n:  ').upper()
                if choice == 'Y' or choice == 'YES' or choice == '':
                    wb = SeedsWorkbook(save)
                elif choice == 'N' or choice == 'NO':
                    print('Save cancelled. Exiting.')
                    sys.exit(0)
                else:
                    print('Invalid input, please answer \'Y\' if you want to '
                          'overwrite the file, or \'N\' if you do not.')
        else:
            wb = SeedsWorkbook(save)
        print('Loading indexes database table into the Indexes worksheet.')
        wb.load_indexes(Index.query.all())
        print('Loading common_names database table into the CommonNames '
              'worksheet.')
        wb.load_common_names(CommonName.query.all())
        print('Loading botanical_names database table into the BotanicalNames '
              'worksheet.')
        wb.load_botanical_names(BotanicalName.query.all())
        print('Loading series database table into Series worksheet.')
        wb.load_series(Series.query.all())
        print('Loading cultivars database table into the Cultivars worksheet.')
        wb.load_cultivars(Cultivar.query.all())
        print('Loading packets database table into the Packets worksheet.')
        wb.load_packets(Packet.query.all())
        print('Saving workbook as \'{0}\'.'.format(save))
        wb.save()
        print('Worbook saved. Exiting.')
        sys.exit(0)
    print('Nothing to do here yet.')

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

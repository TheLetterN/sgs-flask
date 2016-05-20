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
from app import create_app, db, mail, Permission
from app.auth.models import User
from app.seeds.excel import SeedsWorkbook
from app.seeds.htmlgrab import Page, PageAdder, save_batch

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


@manager.command
def grab_all(index):
    if 'annual' in index.lower():
        idx = 'annual'
    elif 'perennial' in index.lower():
        idx = 'perennial'
    elif 'vegetable' in index.lower():
        idx = 'vegetable'
    elif 'vine' in index.lower():
        idx = 'vine'
    else:
        idx = 'herbs'
    directory = os.path.join('pages', idx)
    if not os.path.exists(directory):
        os.mkdir(directory)
    pages_dir = os.path.join('909', idx)
    filename = os.path.join('pages', idx + '.txt')
    with open(filename, 'r') as infile:
        lines = [l.strip() for l in infile.readlines()]
    save_batch(lines, idx, directory, pages_dir)


@manager.command
def load_all(index):
    if 'annual' in index.lower():
        idx = 'annual'
    elif 'perennial' in index.lower():
        idx = 'perennial'
    elif 'vegetable' in index.lower():
        idx = 'vegetable'
    elif 'vine' in index.lower():
        idx = 'vine'
    else:
        idx = 'herbs'
    directory = os.path.join('pages', idx)
    pages = sorted([os.path.join(directory, p) for p in os.listdir(directory)
                    if '.json' in p])
    for page in pages:
        try:
            pa = PageAdder.from_json_file(page)
            pa.save()
        except Exception as e:
            raise RuntimeError('An exception \'{}\' occurred when trying to load '
                               'page: {}'.format(e, page))


@manager.command
def grab(url, outfile, infile=None):
    """Grab a webpage and save it to a JSON file."""
    p = Page(url=url, filename=infile)
    p.save_json(outfile)
    print('Contents of \'{0}\' saved to: {1}'.format(url, outfile))


@manager.command
def load_json(filename):
    """Load a JSON file into the database."""
    pa = PageAdder.from_json_file(filename)
    pa.save()


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
    help='Load an excel spreadsheet with given filename into the database.')
@manager.option(
    '-s',
    '--save',
    help='Save a database dump to an excel spreadsheet with given filename.')
@manager.option(
    '-f',
    '--logfile',
    help='Output messages to given logfile instead of stdout.')
def excel(load=None, save=None, logfile=None):
    """Interact with the excel module to utilize spreadsheets."""
    if logfile:
        if os.path.exists(logfile):
            print('WARNING: The file specified by logfile \'{0}\' already '
                  'exists. Would you like to overwrite it?'
                  .format(logfile))
            while True:
                choice = input('Y/n: ').upper()
                if choice == 'Y' or choice == 'YES' or choice == '':
                    break
                elif choice == 'N' or choice == 'NO':
                    print('Action cancelled due to invalid logfile.')
                    sys.exit(0)
                else:
                    print('Invalid input, please answer \'Y\' if you want to '
                          'overwrite the file, or \'N\' if you do not. Would'
                          'you like to overwite the file \'{0}\'?'
                          .format(logfile))
        stream = open(logfile, 'w', encoding='utf-8')
    else:
        stream = sys.stdout
    if load and save:
        raise ValueError('Cannot load and save at the same time!')
    if load:
        if os.path.exists(load):
            swb = SeedsWorkbook()
            swb.load(load)
        else:
            raise FileNotFoundError('The file \'{0}\' does not exist!'
                                    .format(load))
        swb.save_all_sheets_to_db(stream=stream)
    if save:
        if os.path.exists(save):
            print('WARNING: The file {0} exists. Would you like to overwrite '
                  'it?'.format(save))
            while True:
                choice = input('Y/n:  ').upper()
                if choice == 'Y' or choice == 'YES' or choice == '':
                    break
                elif choice == 'N' or choice == 'NO':
                    print('Save cancelled. Exiting.')
                    sys.exit(0)
                else:
                    print('Invalid input, please answer \'Y\' if you want to '
                          'overwrite the file, or \'N\' if you do not. Would'
                          'you like to overwite the file \'{0}\'?'
                          .format(save))
        swb = SeedsWorkbook()
        print('*** BEGIN saving all data to worksheet \'{0}\'. ***'
              .format(save), file=stream)
        swb.add_all_data_to_sheets(stream=stream)
        swb.beautify_all_sheets()
        swb.save(save)
        print('*** END saving all data to worksheet \'{0}\'. ***'
              .format(save), file=stream)
    if stream is not sys.stdout:
        stream.close()

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

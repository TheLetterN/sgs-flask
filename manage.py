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


import json
import os
import sys
from getpass import getpass

import pytest
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell

from app import create_app, db, mail, Permission
from app.auth.models import User
from app.seeds.excel import SeedsWorkbook
from app.seeds.models import Cultivar
from app.seeds.htmlgrab import Page, PageAdder, save_batch, save_grows_with

app = create_app(os.getenv('SGS_MODE') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)

def make_shell_context():
    return dict(app=app, db=db, mail=mail)


@manager.command
def create():
    """Create a new database and add an admin user."""
    from pycountry import countries
    from app.auth import models as auth_models
    from app.seeds import models as seeds_models
    from app.shop import models as shop_models
    from app.shop.models import Country, State
    resp = input(
        'WARNNG: This will erase existing database and create a new one! '
        'Proceed anyway? y/N: '
    )
    if 'y' in resp.lower():
        print('Erasing existing database if present...')
        db.session.rollback()
        db.session.remove()
        if db.engine.dialect.name == 'postgresql':
            db.engine.execute('drop schema if exists public cascade')
            db.engine.execute('create schema public')
        db.drop_all()
        print('Creating new database...')
        db.create_all()
        admin = User()
        db.session.add(admin)
        print('Populating countries table...')
        db.session.add_all(
            sorted(
                Country.generate_from_alpha3s(c.alpha3 for c in countries),
                key=lambda x: x.name
            )
        )
        db.session.flush()
        print('Populating States/Provinces/etc...')
        try:
            with open('states.json',
                      'r',
                      encoding='utf-8') as ifile:
                d = json.loads(ifile.read())
                db.session.add_all(
                    State.generate_from_dict(d)
                )
                db.session.flush()
        except FileNotFoundError:
            db.session.rollback()
            raise FileNotFoundError(
                'Could not find file "states.json" in the base sgs-flask '
                'directory! If it does not exist, it should be created and '
                'contain a JSON object formatted: { "<country alpha3 code>": '
                '{ "<state abbreviation>": "<state name>", ... }, ... } e.g. '
                '{ "USA": {"AL": "Alabama", "AK": "Alaska", ... }, {"CAN": { '
                '{"AB": "Alberta", "BC": "British Columbia", ... }, ... }'
            )
        print('Creating first administrator account...')
        admin.name = input('Enter name for admin account: ')
        admin.email = input('Enter email address for admin account: ')
        while True:
            pw = getpass('Enter new password: ')
            pwc = getpass('Confirm new password: ')
            if pwc != pw:
                print('Passwords do not match! Please try again.')
            else:
                break
        admin.set_password(pw)
        admin.grant_permission(Permission.MANAGE_SEEDS)
        admin.grant_permission(Permission.MANAGE_USERS)
        admin.confirmed = True
        print('Admin account "{}" created!'.format(admin.name))
        db.session.commit()
        print('Database was successfully created!')
    else:
        print('Aborted.')


@manager.command
def make_cultivars_visible():
    """Make all cultivars visible."""
    for cv in Cultivar.query.all():
        cv.visible = True
    db.session.commit()
    print('All cultivars are now visible.')


@manager.command
def set_grows_with():
    """Save grows with relationships to database."""
    save_grows_with()


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
    elif 'herb' in index.lower():
        idx = 'herb'
    else:
        raise ValueError('\'{0}\' does not match any known index!'
                         .format(index))
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
        idx = 'herb'
    directory = os.path.join('pages', idx)
    pages = sorted(os.path.join(directory, p) for p in os.listdir(directory)
                   if '.json' in  p and p[0] != '.')
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

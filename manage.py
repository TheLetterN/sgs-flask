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
from decimal import Decimal
from getpass import getpass
from pathlib import Path

import pytest
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager, Shell
from sqlalchemy_searchable import make_searchable

from app import create_app, db, mail, Permission
from app.auth.models import User
from app.seeds.excel import SeedsWorkbook
from app.seeds.models import Cultivar
from sgsscrape import (
    add_bulk_to_database,
    add_index_to_database,
    load_all,
    load_bulk,
    save_all,
    set_related_links
)

app = create_app(os.getenv('SGS_MODE') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app, db=db, mail=mail)


@manager.command
def scrape():
    save_all()


@manager.command
def populate():
    try:
        for i in load_all():
            add_index_to_database(i)
        add_bulk_to_database(load_bulk())
        set_related_links()
    except FileNotFoundError:
        print('No scraped data found! Please run "manage.py scrape" to scrape '
              'the website, then try again.')


@manager.option(
    '-f',
    '--fast',
    action='store_true',
    help='Skip admin account creation and create default admin account.'
)
def resetdb(fast=False):
    """Erase db and/or create a new one with an admin account."""
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
        print('Configuring mappers...')
        db.configure_mappers()
        print('Creating new database...')
        db.create_all()
        db.session.commit()
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
        print('Setting safe to ship countries...')
        stsfile = Path(
            app.config['JSON_FOLDER'], 
            'safe_to_ship_countries.json'
        )
        try:
            with stsfile.open('r', encoding='utf-8') as ifile:
                sts = json.loads(ifile.read())
                for c in sts:
                    if isinstance(c, str):
                        alpha3 = c
                        thresh = None
                    else:
                        alpha3 = c[0]
                        thresh = c[1]
                    country = Country.get(alpha3=alpha3)
                    if thresh:
                        country.at_own_risk_threshold = thresh
                    country.safe_to_ship = True
                db.session.flush()
        except FileNotFoundError:
            db.session.rollback()
            raise FileNotFoundError(
                'Could not find file "{}". This file should be a JSON list '
                'containing alpha3 country codes for countries we can safely '
                'ship to, including ones that become at own risk above a '
                'certain cost total, which should be 2 value lists formatted '
                '["<alpha3", <int or decimal cost above which is at own '
                'risk>], e.g.: [... , "JPN", "NLD", ["NOR", 50], "PRI", '
                '"ESP", ...]'.format(stsfile.absolute())
            )
        print('Setting noship countries...')
        ncfile = Path(app.config['JSON_FOLDER'], 'noship_countries.json')
        try:
            with ncfile.open('r', encoding='utf-8') as ifile:
                a3s = json.loads(ifile.read())
                for alpha3 in a3s:
                    country = Country.get(alpha3=alpha3)
                    country.noship = True
                db.session.flush()
        except FileNotFoundError:
            db.session.rollback()
            raise FileNotFoundError(
                'Could not find file "{}"! This file should be a JSON list '
                'containing alpha3 country codes for countries we cannot '
                'ship to. e.g.: ["BGD", "BRA", "CHN", ... ]'
                .format(ncfile.absolute())
            )
        print('Populating States/Provinces/etc...')
        try:
            sfile = Path(app.config['JSON_FOLDER'], 'states.json')
            with sfile.open('r', encoding='utf-8') as ifile:
                d = json.loads(ifile.read())
                db.session.add_all(
                    State.generate_from_dict(d)
                )
                db.session.flush()
        except FileNotFoundError:
            db.session.rollback()
            raise FileNotFoundError(
                'Could not find file "{}"! If it does not exist, it should '
                'be created and contain a JSON object formatted: { "<country '
                'alpha3 code>": { "<state abbreviation>": "<state name>", '
                '... }, ... } e.g. {"USA": {"AL": "Alabama", "AK": '
                '"Alaska", ... }, "CAN": {"AB": "Alberta", "BC": '
                '"British Columbia", ... }, ... }'.format(sfile.absolute())
            )
        print('Setting California sales tax...')
        rfile = Path(app.config['JSON_FOLDER'], 'rates.json')
        try:
            with rfile.open('r', encoding='utf-8') as ifile:
                rates = json.loads(ifile.read())
            ca = State.get(
                country=Country.get(alpha3='USA'), abbreviation='CA'
            )
            ca.tax = Decimal(str(rates['sales tax']['USA']['CA']))
            db.session.flush()
        except FileNotFoundError:
            raise FileNotFoundError(
                'Could not find file "{}"! It should contain a JSON object '
                'including: { "sales tax": {"USA": {"CA":<tax rate>i, ... }, '
                '... }, ... }'.format(rfile.absolute())
            )
        print('Creating first administrator account...')
        if fast:
            admin.name = 'admin'
            admin.email = 'admin@localhost'
            admin.set_password('sgsadmin')  # Very secure!
        else:
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

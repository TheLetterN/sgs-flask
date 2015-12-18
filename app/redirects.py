# -*- coding: utf-8 -*-


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
from datetime import datetime
from flask import redirect


def utcnow():
    """Use this instead of datetime.utcnow for patchability in tests."""
    return datetime.utcnow()


class Redirect(object):
    """Store and operate on data to use for generating redirects.

    Attributes:
        old_path (str): The path to redirect from.
        new_path (str): The path to redirect to.
        status_code (int): The status_code to use with the redirect.
        date_created (datetime): The date and time in UTC when the redirect
            was created.
    """
    def __init__(self,
                 old_path,
                 new_path,
                 status_code,
                 date_created=None):
        self.old_path = old_path
        self.new_path = new_path
        self.status_code = status_code
        self.date_created = date_created

    def __repr__(self):
        return '<{0} from {1} to {2}, status code: {3}>'\
            .format(self.__class__.__name__,
                    self.old_path,
                    self.new_path,
                    self.status_code)

    def __eq__(self, other):
        return self._old_path == other._old_path and\
            self._new_path == other._new_path and\
            self._status_code == other._status_code and\
            self._date_created == other._date_created

    @property
    def old_path(self):
        """ str: Path to be redirected from.

        Setter raises ValueError if given data that doesn't look like a root-
            relative path.
        """
        return self._old_path

    @old_path.setter
    def old_path(self, path):
        if isinstance(path, str) and path[0] == '/':
            self._old_path = path
        else:
            raise ValueError('path must be a string representing a '
                             'root-relative path beginning with /')

    @property
    def new_path(self):
        """ str: Path to redirect to.

        Setter raises ValueError if given data that doesn't look like a root-
            relative path.
        """
        return self._new_path

    @new_path.setter
    def new_path(self, path):
        if isinstance(path, str) and path[0] == '/':
            self._new_path = path
        else:
            raise ValueError('path must be a string representing a '
                             'root-relative path beginning with /')

    @property
    def status_code(self):
        """ int: Status code for redirect.

        Setter raises TypeError if not int, ValueError if not redirect code.
        """
        return self._status_code

    @status_code.setter
    def status_code(self, code):
        if isinstance(code, int):
            if code > 300 and code < 309:
                self._status_code = code
            else:
                raise ValueError('status code must be avalid HTTP redirect '
                                 'code')
        else:
            raise TypeError('status code must be an int')

    @property
    def date_created(self):
        """ datetime: Date and time the redirect was created in UTC.

        Setter raises TypeError if not given a datetime object.
        """
        return self._date_created

    @date_created.setter
    def date_created(self, date):
        if date is None:
            self._date_created = utcnow()
        elif isinstance(date, datetime):
            self._date_created = date
        else:
            raise TypeError('date_created should either be a datetime object, '
                            'or None')

    def message(self):
        """Return a string containing a message describing this redirect."""
        return 'Redirect from {0} to {1} with status code {2}'\
            .format(self.old_path, self.new_path, self.status_code)

    def redirect_path(self):
        """Return a redirect to the new path."""
        return redirect(self.new_path, self.status_code)

    def add_to_app(self, app):
        """Add the redirect to url rules for application."""
        app.add_url_rule(self._old_path,
                         self._old_path,
                         view_func=self.redirect_path)

    @classmethod
    def from_JSON(cls, json_string):
        jm = json.loads(json_string)
        obj = cls(old_path=jm['old_path'],
                  new_path=jm['new_path'],
                  status_code=jm['status_code'],
                  date_created=datetime.strptime(jm['date_created'],
                                                 '%m/%d/%Y %H:%M:%S.%f'))
        return obj

    def to_JSON(self):
        """Return a JSON string of this redirect."""
        dc_string = self.date_created.strftime('%m/%d/%Y %H:%M:%S.%f')
        return json.dumps({'old_path': self.old_path,
                           'new_path': self.new_path,
                           'status_code': self.status_code,
                           'date_created': dc_string})


class RedirectsFile(object):
    """Handle saving and loading of redirects to/from a file.

    Attributes:
        file_name (str): File to read/write redirects from/to.
        redirects (list): List of Redirect objects to store/retrieve.

    Note:
        Redirects cannot be removed in realtime. For removed/altered redirects
        to work, sgs_flask needs to be restarted!
    """
    def __init__(self, file_name):
        self.file_name = file_name
        self.redirects = []

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.file_name)

    def add_redirect(self, rd):
        """Add a Redirect object to the file."""
        if isinstance(rd, Redirect):
            for redir in self.redirects:
                if rd.old_path == redir.old_path:
                    raise ValueError('A redirect already exists from \'{0}\'. '
                                     'If you want to replace it, please '
                                     'remove the old redirect first.'
                                     .format(rd.old_path))
                if rd.new_path == redir.old_path:
                    raise ValueError('You are trying to add a redirect to '
                                     '{0}, but a redirect from {1} to {2} '
                                     'already exists. You may wish to add a '
                                     'redirect from {3} to {2} instead.'
                                     .format(rd.new_path,
                                             redir.old_path,
                                             redir.new_path,
                                             rd.old_path))
                if rd.old_path == redir.new_path:
                    # Don't create redirect chains, edit old redirects to
                    # new destinations if applicable.
                    redir.new_path = rd.new_path
            self.redirects.append(rd)
        else:
            raise TypeError('add_redirect can only take Redirect objects!')

    def remove_redirect(self, rd):
        """Remove a redirect object from the file."""
        self.redirects.remove(rd)

    def add_all_to_app(self, app):
        for rd in self.redirects:
            rd.add_to_app(app)

    def exists(self):
        """Return True if file specified by self.file_name exists."""
        return os.path.exists(self.file_name)

    def get_redirect_with_old_path(self, path):
        """Returns the Redirect with given path if it exists."""
        for rd in self.redirects:
            if rd.old_path == path:
                return rd
        return None

    def load(self, file_name=None):
        """Load specified file, or self.file_name."""
        if file_name is None:
            file_name = self.file_name
        with open(file_name, 'r', encoding='utf-8') as ifile:
            self.load_file(ifile)

    def load_file(self, ifile):
        """Load JSON data from a file-like object."""
        json_rds = json.loads(ifile.read())
        self.redirects = [Redirect.from_JSON(rd) for rd in json_rds]

    def save(self, file_name=None):
        """Save specified file, or self.file_name.

        Raises:
            ValueError: if there are no redirects to save.
        """
        if file_name is None:
            file_name = self.file_name
        if self.redirects:
            with open(file_name, 'w', encoding='utf-8') as ofile:
                self.save_file(ofile)
        else:
            raise ValueError('There are no redirects to be saved!')

    def save_file(self, ofile):
        """Save JSON string to output file."""
        ofile.write(json.dumps([rd.to_JSON() for rd in self.redirects]))

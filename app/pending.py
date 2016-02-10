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


import os


class Pending(object):
    """Manipulate a list of changes pending restart of application."""
    def __init__(self, file_name):
        self.file_name = file_name
        self.changes = ''

    def add_message(self, change):
        if self.changes:
            self.changes += '\n'
        self.changes += change

    def clear(self):
        self.changes = ''

    def load(self, file_name=None):
        if file_name is None:
            file_name = self.file_name
        with open(file_name, 'r', encoding='utf-8') as infile:
            self.changes = infile.read()

    def save(self, file_name=None):
        if file_name is None:
            file_name = self.file_name
        with open(file_name, 'w', encoding='utf-8') as outfile:
            outfile.write(self.changes)

    def exists(self):
        return os.path.exists(self.file_name)

    def has_content(self):
        """Return True if the pending file has any content in it."""
        if self.exists():
            with open(self.file_name, 'r', encoding='utf-8') as infile:
                if infile.read():
                    return True
        return False

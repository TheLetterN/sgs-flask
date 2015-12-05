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

from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from app import db


class Redirect(db.Model):
    """Store urls to use in redirects.

    Note: Use root-relative paths, not full URLs! Redirects from different
        domains/subdomains should be handled elsewhere, likely by the HTTP
        server being run in conjunction with sgs_flask.
    
    Attributes:
        id (int): Auto-incremented ID # for primary key.
        date_created (datetime): The date and time (in UTC) the redirect was 
            created.
        _old_path (str): The original root-relative path to be redirected.
        _new_path (str): The URL to redirect to.
        status_code (int): The status code to use for the redirect.
    """
    __tablename__ = 'redirects'
    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime)
    _old_path = db.Column(db.Text, unique=True)
    _new_path = db.Column(db.Text)
    status_code = db.Column(db.Integer)

    def __init__(self, old_path, new_path, status_code, date_created=None):
        self.old_path = old_path
        self.new_path = new_path
        self.status_code = status_code
        if date_created:
            if isinstance(date_created, datetime):
                self.date_created = date_created
            else:
                raise TypeError('date_created must be a datetime.datetime '
                                'object!')
        else:
            self.date_created = datetime.utcnow()

    def __repr__(self):
        return '<{0} from \'{1}\' to \'{2}\'>'.format(self.__class__.__name__,
                                                      self.old_path,
                                                      self.new_path)

    @hybrid_property
    def old_path(self):
        """str: Path to redirect from.
        
        Setter raises an exception if path doesn't begin with a forward slash.
        """
        return self._old_path

    @old_path.setter
    def old_path(self, path):
        if path[0] == '/':
            self._old_path = path
        else:
            raise ValueError('Path must be root-relative and begin with a '
                             'forward slash. (/)')

    @hybrid_property
    def new_path(self):
        """str: Path to redirect to.

        Setter raises an exeption if path doesn't begin with a forward slash.
        """
        return self._new_path

    @new_path.setter
    def new_path(self, path):
        if path[0] == '/':
            self._new_path = path
        else:
            raise ValueError('Path must be root-relative and begin with a '
                             'forward slash. (/)')

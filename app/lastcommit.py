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
import re
import time


class LastCommit(object):
    """An object containing information on the last git commit."""
    def __init__(self, filename=None):
        if filename is None:
            filename = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    '..',
                                                    '.git',
                                                    'logs',
                                                    'HEAD'))
        with open(filename, 'r') as logfile:
            self.message = logfile.readlines()[-1]
        self.ctime = int(re.search('> (\d*) -', self.message).group(1))
        self.timestamp = time.ctime(self.ctime)

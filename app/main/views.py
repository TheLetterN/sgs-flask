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


from flask import render_template
from . import main


@main.route('/')
def index():
    """Generate the index page of the website."""
    return render_template('main/index.html')


@main.route('/test')
def test():
    """Test page, please ignore."""
    var = 'Have a link to index: url_for(\'main.index\'). Isn\'t it nice?'
    return render_template('main/test.html', var=var)

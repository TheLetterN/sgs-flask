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


from flask import abort, render_template
from jinja2 import TemplateNotFound

from . import main
from config import BASEDIR


@main.route('/')
def index():
    """Generate the index page of the website."""
    return render_template('main/index.html')

@main.route('/<page>.html')
def static_html(page):
    """Display a page generated from html files in app/static/html"""
    try:
        return render_template('static/' + page + '.html', page=page)
    except TemplateNotFound:
        abort(404)

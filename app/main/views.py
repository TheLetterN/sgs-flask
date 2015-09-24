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


from flask import current_app, redirect, render_template, url_for
from . import main
from app.auth.models import Permission
from app.seeds.models import Category


@main.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@main.context_processor
def make_categories_available():
    """Make categories available to Jinja templates.

    Returns:
        dict: A list of all Category objects loaded from the database.
    """
    if not current_app.config.get('TESTING'):  # pragma: no cover
        categories = Category.query.all()
    else:
        categories = None
    return dict(categories=categories)


@main.route('/')
def index():
    """Generate the index page of the website."""
    return render_template('main/index.html')


@main.route('/index')
@main.route('/index.html')
@main.route('/index.htm')
def index_redirect():
    """Redirect common index page names to main.index"""
    return redirect(url_for('main.index'), code=301)

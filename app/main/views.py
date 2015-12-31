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


from flask import current_app, render_template
from . import main
from app.auth.models import Permission
from app.seeds.models import Index


@main.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@main.context_processor
def make_indexes_available():
    """Make indexes available to Jinja templates.

    Returns:
        dict: A list of all Index objects loaded from the database.
    """
    if not current_app.config.get('TESTING'):  # pragma: no cover
        indexes = Index.query.all()
    else:
        indexes = None
    return dict(indexes=indexes)


@main.route('/')
def index():
    """Generate the index page of the website."""
    return render_template('main/index.html')

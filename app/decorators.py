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


from functools import wraps
from flask import abort, current_app
from flask.ext.login import current_user


def permission_required(permission):
    """Prevent user from accessing a route unless they have permission.

    Args:
        permission (int): An integer with a single set bit (such as 0b10)
                          representing a permission. Normally this would be a
                          constant from app.models.Permission.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission) and \
                    not current_app.config.get('TESTING'):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

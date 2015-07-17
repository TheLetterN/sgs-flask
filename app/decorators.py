from functools import wraps
from flask import abort
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
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

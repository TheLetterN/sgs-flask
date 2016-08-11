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


from validate_email import validate_email
from wtforms import ValidationError


class NotSpace(object):
    """Validator to ensure a field is not purely whitespace."""
    def __init__(self, message=None):
        if not message:
            message = 'Field cannot consist entirely of whitespace.'
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.isspace():
            raise ValidationError(self.message)


class Email(object):
    """Validator to ensure a valid email address is in a field.

    Rather than using wtforms.validators.Email this should be used, as
    wtforms.validators.Email is too strict and doesn't allow email addresses
    without TLDs, which makes using local email addresses not doable.
    """
    def __init__(self, message=None):
        if not message:
            message = 'Field must contain a valid email address.'
        self.message = message

    def __call__(self, form, field):
        if not validate_email(field.data):
            raise ValidationError(self.message)

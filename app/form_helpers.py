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

from flask_wtf.file import FileField
from validate_email import validate_email
from werkzeug import secure_filename
from wtforms import StringField, TextAreaField, ValidationError


# Validators
class BeginsWith(object):
    """Validator for fields that should begin with given string.

    Attributes:
        beginning: The string a field's data should begin with.
        message: An optional message to give if validation fails. You may
            include `beginning` in the message with {beginning}.
    """
    def __init__(self, beginning, message=None):
        if not message:
            message = 'Must begin with: {beginning}'
        self.beginning = beginning
        if '{beginning}' in message:
            self.message = message.format(beginning=beginning)
        else:
            self.message = message

    def __call__(self, form, field):
        if field.data[:len(self.beginning)] != self.beginning:
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


class ListItemLength(object):
    """Validator for length of items in a string list.

    Attributes:
        minimum: The minimum length of an item.
        maximum: The maximum length of an item.
        delimiter: The delimiter between list items. Default = ', '.
        message: An optional message to include. You can include minimum
            and/or maximum in the message with {minimum} and/or {maximum}.
    """
    def __init__(self,
                 minimum=None,
                 maximum=None,
                 delimiter=', ',
                 message=None):
        if minimum is None and maximum is None:
            raise ValueError('Neither minimum nor maximum are set!')
        if minimum and maximum and minimum > maximum:
            raise ValueError(
                'The minimum list item length cannot be greater than the '
                'maximum!'
            )
        if not delimiter:
            raise ValueError('Cannot parse list items without a delimiter!')
        if not message:
            if minimum is not None and maximum is not None:
                message = (
                    'Each item in the list must be between {minimum} and '
                    '{maximum} characters long!'
                )
            elif minimum is not None:
                message = (
                    'Each item in the list must be at least {minimum} '
                    'characters long!'
                )
            else:
                message = (
                    'Each item in the list must be no more than {maximum} '
                    'characters long!'
                )
        self.minimum = int(minimum) if minimum else None
        self.maximum = int(maximum) if maximum else None
        self.delimiter = delimiter
        if '{minimum}' in message and '{maximum}' in message:
            self.message = message.format(minimum=minimum, maximum=maximum)
        elif '{minimum}' in message:
            self.message = message.format(mimimum=minimum)
        elif '{maximum}' in message:
            self.message = message.format(maximum=maximum)
        else:
            self.message = message

    def __call__(self, form, field):
        if field.data:
            items = field.data.split(self.delimiter)
            if self.minimum is not None and self.maximum is not None:
                for item in items:
                    if len(item) < self.minimum or len(item) > self.maximum:
                        raise ValidationError(self.message)
            elif self.minimum is not None:
                for item in items:
                    if len(item) < self.minimum:
                        raise ValidationError(self.message)
            else:
                for item in items:
                    if len(item) > self.maximum:
                        raise ValidationError(self.message)


class ReplaceMe(object):
    """Validator for fields populated with data that needs to be edited.

    These fields can be populated with strings that need to be edited by the
    user to be valid. The parts that need to be edited are enclosed in <>.

    Warning:
        Do not use this validator in fields intended to allow XML/HTML!
    """
    def __init__(self, message=None):
        if not message:
            self.message = 'Field contains data that needs to be replaced. '\
                           'Please replace any sections surrounded by < and '\
                           '> with requested data.'
        else:
            self.message = message

    def __call__(self, form, field):
        if '<' in field.data and '>' in field.data:
            raise ValidationError(self.message)


# Custom Fields
class SecureFileField(FileField):
    """A FileField that automatically secures its filename."""
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data:
            self.data.filename = secure_filename(self.data.filename)


class StrippedStringField(StringField):
    """A `StringField` that strips trailing whitespace.

    This is primarily useful for fields we want to allow submitting without
    data, but which we don't want saving whitespace from if that's all it
    contains.
    """
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        self.data = self.data.strip()


class StrippedTextAreaField(TextAreaField):
    """A `TextAreaField` that strips trailing whitespace.

    Like `StrippedStringField` this is mostly to prevent accidentally storing
    data that's purely whitespace, but it's also handy because there's no
    reason to leave leading and trailing whitespace in data using this field.
    """
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        self.data = self.data.strip()


class SecureFilenameField(StrippedStringField):
    """A `StringField` for filenames that prevents directory traversal."""
    def __init__(self, *args, tooltip=None,  **kwargs):
        self.tooltip = tooltip
        super().__init__(*args, **kwargs)

    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        parts = os.path.split(self.data)
        self.data = os.path.join(parts[0], secure_filename(parts[1]))
        self.data = os.path.normpath('/' + self.data).lstrip('/')

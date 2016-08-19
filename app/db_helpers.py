# -*- coding: utf-8 -*-
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


"""app.db_helpers

This module contains helper classes and functions for use with database
models.
"""

import re
from decimal import Decimal, ROUND_DOWN

from titlecase import titlecase

from app import db


def dbify(string):
    """Format a string to be stored in the database.

    Args:
        string: The string to be converted.

    Returns:
        str: A string formatted for database usage.
        None: If string is None or empty.
    """
    def cb(word, **kwargs):
        """Override default behaviors in titlecase that give incorrect results.

        Hyphenated phrases should only capitalize the first letter. The default
        behavior of titlecase is to capitalize the first letter in each part.
        e.g forget-me-not > Forget-Me-Not, while we want forget-me-not >
        Forget-me-not.

        Also some 'words' should be in all-caps, such as roman numerals, and
        if a number followed by an uppercase letter occurs, it should be
        assumed it's meant to be that way, as in Texas 1015Y Onion.

        Returns:
            str: Corrected hyphenated word.
        """
        # Some things should be allcaps, such as roman numerals.
        ALLCAPS = ('I', 'II', 'III', 'IV', 'V', 'XP', 'BLBP')
        if '-' in word:
            return word[0].upper() + word[1:].lower()
        elif word.upper() in ALLCAPS:
            return word.upper()
        elif re.search(r'[0-9][A-Za-z]', word):
            return word.upper()
        elif word.lower() == 'w/':
            return 'w/'
        elif re.search(r'^[dD]\'[A-Za-z]+', word):  # d'Avignon
            parts = word.split('\'')
            parts[0] = parts[0].lower()
            parts[1] = parts[1].title()
            return '\''.join(parts)
        elif re.search(r'[oO]\'[A-Za-z]+', word):  # O'Hara
            parts = word.split('\'')
            parts[0] = parts[0].upper()
            parts[1] = parts[1].title()
            return '\''.join(parts)

    if string:
        # lower() string in addition to stripping it because titlecase()
        # leaves capital words capitalized in mixed case lines.
        # we don't want that because we want a line like:
        # 'RED FLOWER (white bee)' to become 'Red Flower (White Bee)'.
        string = string.strip().lower()
        dbified = titlecase(string, callback=cb)
        return dbified
    else:
        return None


def row_exists(col, value):
    """Check to see if a given row exists in a table.

    Args:
        col: The column to check, in the form of a db Model attribute, e.g.
            `Index.name` or `Packet.sku`.
        value: The value of the row to check for.

    Returns:
        bool: True if row exists, False if not.
    """
    return db.session.query(db.exists().where(col == value)).scalar()


class TimestampMixin(object):
    """A mixin for classes that would benefit from tracking modifications.

    Attributes:

    created_on: The date and time an instance was created.
    updated_on: The date and time an instance was last updated.
    """
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    updated_on = db.Column(db.DateTime, onupdate=db.func.now())


class OrderingListMixin(object):
    """A mixin for methods dealing with ordering_list positioning."""
    @property
    def parent_collection(self):
        raise NotImplementedError(
            'The parent_collection property for "{0}" has not been '
            'implemented yet!'.format(self.__class__.__name___)
        )

    def move(self, delta):
        """Move position of object w/ respect to its parent collection.

        Args:
            delta: The number of positions to move. Positive for forward,
                negative for backwards. No matter what delta is passed, no
                `CommonName` will be moved below the lowest index or above
                the highest index.
        """
        collection = self.parent_collection
        from_index = collection.index(self)
        to_index = from_index + delta
        last_index = len(collection) - 1
        if to_index < 0:
            to_index = 0
        if to_index > last_index:
            to_index = last_index
        if from_index != to_index:
            collection.insert(to_index, collection.pop(from_index))
            return True
        else:
            return False

    def move_after(self, other):
        """Move self to position after other.

        Args:
            other: An instance of the same model to place `self` after.
        """
        self_index = self.parent_collection.index(self)
        other_index = self.parent_collection.index(other)
        # other's index will be decremented if other comes after self and
        # self is popped, so other_index will be the index after other.
        # Therefore, we only need to increment other_index if other is before
        # self.
        if other_index < self_index:
            other_index += 1
        self.parent_collection.insert(
            other_index, self.parent_collection.pop(self_index)
        )

    def insert_after(self, other):
        """Insert at index after `other`.

        Args:
            other: An instance of the same model to place `self` after.
        """
        self.parent_collection.insert(
            self.parent_collection.index(other) + 1, self
        )


class FourPlaceDecimal(db.TypeDecorator):
    """Type for Decimal number with a max of four places.

    Attributes:

    impl: The column type the actual data is stored as.
    """
    impl = db.Integer

    def process_bind_param(self, value, dialect):
        """Convert a `Decimal` with up to 4 places into an int.

        value is converted to `str`, then `Decimal` to ensure it will take
        anything that can be converted to `Decimal`, but will not attempt to
        convert a `float` to a `Decimal`.
        """
        if value is None:
            return None
        else:
            return int(Decimal(str(value)) * 10000)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        else:
            return Decimal(value) / 10000


class USDollar(db.TypeDecorator):
    """Type for US dollar amounts to be stored in the database.

    Since we don't know for sure how the database will handle decimal numbers,
    it is safer to store our dollar amounts as integers to avoid the risk of
    floating point errors leading to incorrect data. Therfore, values will be
    stored in cents and converted back to dollars upon retrieval.

    A USDollar column will store a value of 2.99 as 299 in the database, and
    return it as 2.99 when retrieved.

    Attributes:
        impl: The type of column this decorates: `sqlalchemy.types.Integer`.
    """
    impl = db.Integer

    def process_bind_param(self, value, dialect):
        if value is None:  # pragma: no cover
            return None
        else:
            return USDollar.usd_to_cents(value)

    def process_result_value(self, value, dialect):
        if value is None:  # pragma: no cover
            return None
        else:
            return USDollar.cents_to_usd(value)

    @staticmethod
    def cents_to_usd(cents):
        """Convert a value in cents into a value in dollars.

        Args:
            cents: An integer value in cents to be converted to a decimal
                dollar value.

        Returns:
            Decimal: US cents converted to US dollars and quantized to
                always have two digits to the right of the decimal.

        Examples:
            >>> USDollar.cents_to_usd(100)
            Decimal('1.00')

            >>> USDollar.cents_to_usd(350)
            Decimal('3.50')

            >>> USDollar.cents_to_usd(2999)
            Decimal('29.99')

        """
        cents = int(cents)
        return (Decimal(cents) / 100).\
            quantize(Decimal('1.00'))

    @staticmethod
    def usd_to_decimal(usd):
        """Convert a US dollar value to a `Decimal`.

        Args:
            usd: The value to convert to `Decimal`.

        Examples:

            >>> USDollar.usd_to_decimal(3.5)
            Decimal('3.50')

            >>> USDollar.usd_to_decimal(2)
            Decimal('2.00')

            >>> USDollar.usd_to_decimal('9.99')
            Decimal('9.99')

            >>> USDollar.usd_to_decimal('$5')
            Decimal('5.00')

            >>> USDollar.usd_to_decimal('$ 4.49')
            Decimal('4.49')

            >>> USDollar.usd_to_decimal('3$')
            Decimal('3.00')
        """
        usd = str(usd).replace('$', '').strip()
        return Decimal(usd).quantize(Decimal('1.00'), rounding=ROUND_DOWN)

    @staticmethod
    def usd_to_cents(usd):
        """Convert a US dollar amount to cents.

        Args:
            usd: A US Dollar amount to convert to cents.

        Examples:

            >>> USDollar.usd_to_cents(Decimal('1.99'))
            199

            >>> USDollar.usd_to_cents(5)
            500

            >>> USDollar.usd_to_cents('$2.99')
            299

            >>> USDollar.usd_to_cents('2.5')
            250
        """
        return (int(USDollar.usd_to_decimal(usd) * 100))

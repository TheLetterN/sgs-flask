# -*- coding: utf-8 -*-
import os
import pytest
from decimal import Decimal
from flask import current_app
from fractions import Fraction
from inflection import pluralize
from slugify import slugify
from unittest import mock
from app.seeds.models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Seed,
    USDInt
)
from tests.conftest import app  # noqa


class TestUSDInt:
    """Test methods of the USDInt TypeDecorator in the seeds model."""
    def test_int_to_usd(self, app):
        """Return a Decimal USD value given an integer."""
        assert USDInt.int_to_usd(100) == Decimal('1.00')
        assert USDInt.int_to_usd(299) == Decimal('2.99')
        assert USDInt.int_to_usd(350) == Decimal('3.50')

    def test_int_to_usd_bad_type(self, app):
        """Raise a TypeError given non-int data."""
        with pytest.raises(TypeError):
            USDInt.int_to_usd(3.14)
        with pytest.raises(TypeError):
            USDInt.int_to_usd('400')
        with pytest.raises(TypeError):
            USDInt.int_to_usd(Decimal('100'))

    def test_int_to_usd_two_decimal_places(self, app):
        """Always return a Decimal with 2 decimal places."""
        assert str(USDInt.int_to_usd(100)) == '1.00'
        assert str(USDInt.int_to_usd(350)) == '3.50'
        assert str(USDInt.int_to_usd(1000)) == '10.00'

    def test_usd_to_int_bad_string(self, app):
        """Raise a ValueError given a string that can't be parsed."""
        with pytest.raises(ValueError):
            USDInt.usd_to_int('2 99')
        with pytest.raises(ValueError):
            USDInt.usd_to_int('$ 2.99 US')
        with pytest.raises(ValueError):
            USDInt.usd_to_int('tree fiddy')

    def test_usd_to_int_bad_type(self, app):
        """Raise a TypeError given a value that can't be coerced to int."""
        with pytest.raises(TypeError):
            USDInt.usd_to_int(Fraction(1, 4))
        with pytest.raises(TypeError):
            USDInt.usd_to_int(['2.99', '1.99'])
        with pytest.raises(TypeError):
            USDInt.usd_to_int({'price': '$2.99'})

    def test_usd_to_int_valid_non_strings(self, app):
        """Return an int given a valid non-string type."""
        assert USDInt.usd_to_int(1) == 100
        assert USDInt.usd_to_int(2.99) == 299
        assert USDInt.usd_to_int(3.999) == 399
        assert USDInt.usd_to_int(Decimal('1.99')) == 199
        assert USDInt.usd_to_int(3.14159265) == 314

    def test_usd_to_int_valid_string(self, app):
        """Return an int given a valid string containing a dollar amount."""
        assert USDInt.usd_to_int('$2.99') == 299
        assert USDInt.usd_to_int('3.00') == 300
        assert USDInt.usd_to_int('2.50$') == 250
        assert USDInt.usd_to_int('$ 1.99') == 199
        assert USDInt.usd_to_int('4.99 $') == 499
        assert USDInt.usd_to_int(' 3.50 ') == 350
        assert USDInt.usd_to_int('4') == 400
        assert USDInt.usd_to_int('5.3') == 530
        assert USDInt.usd_to_int('3.9999') == 399


class TestBotanicalName:
    """Test methods of BotanicalName in the seeds model."""
    def test_name_getter(self, app):
        """.name is the same as ._name."""
        bn = BotanicalName()
        bn._name = 'Asclepias incarnata'
        assert bn.name == 'Asclepias incarnata'

    def test_name_setter_valid_input(self, app):
        """set ._name if valid."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        assert bn._name == 'Asclepias incarnata'

    def test_init_invalid_botanical_name(self, app):
        with pytest.raises(ValueError):
            BotanicalName(name='Richard M. Nixon')

    def test_init_valid_botanical_name(self, app):
        """Sets the BotanicalName.botanical_name to given value."""
        bn = BotanicalName(name='Asclepias incarnata')
        assert bn.name == 'Asclepias incarnata'

    def test_repr(self, app):
        """Return a string in format <BotanicalName '<botanical_name>'>"""
        bn = BotanicalName(name='Asclepias incarnata')
        assert bn.__repr__() == '<BotanicalName \'Asclepias incarnata\'>'

    def test_validate_more_than_two_words(self, app):
        """A botanical name is still valid with more than 2 words."""
        assert BotanicalName.validate('Brassica oleracea Var.')

    def test_validate_not_a_string(self, app):
        """Return False when given non-string data."""
        assert not BotanicalName.validate(42)
        assert not BotanicalName.validate(('foo', 'bar'))
        assert not BotanicalName.validate(dict(foo='bar'))

    def test_validate_upper_in_wrong_place(self, app):
        """The only uppercase letter should be the first."""
        assert not BotanicalName.validate('AscLepias incarnata')
        assert not BotanicalName.validate('Asclepias Incarnata')
        assert not BotanicalName.validate('Asclepias incarNata')

    def test_validate_starts_with_lower(self, app):
        """The first letter of a botanical name should be uppercase."""
        assert not BotanicalName.validate('asclepias incarnata')

    def test_validate_valid_binomen(self, app):
        """Returns true if botanical_name contains a valid binomen."""
        assert BotanicalName.validate('Asclepias incarnata')
        assert BotanicalName.validate('Helianthus anuus')


class TestCategory:
    """Test methods of Category in the seeds model."""
    def test_category_getter(self, app):
        """Return ._name."""
        category = Category()
        category._name = 'Perennial Flower'
        assert category.name == 'Perennial Flower'

    def test_category_setter(self, app):
        """Set ._name and a pluralized, slugified v. to .slug."""
        category = Category()
        category.name = 'Annual Flower'
        assert category._name == 'Annual Flower'
        assert category.slug == slugify(pluralize('Annual Flower'))

    def test_header(self, app):
        """Return '<._name> Seeds'"""
        category = Category()
        category.name = 'Annual Flower'
        assert category.header == 'Annual Flower Seeds'

    def test_plural(self, app):
        """Return plural version of ._name."""
        category = Category()
        category.name = 'Annual Flower'
        assert category.plural == 'Annual Flowers'

    def test_repr(self, app):
        """Return string formatted <Category '<category>'>"""
        category = Category()
        category.name = 'vegetable'
        assert category.__repr__() == '<Category \'vegetable\'>'


class TestCommonName:
    """Test methods of CommonName in the seeds model."""
    def test_repr(self, app):
        """Return string formatted <CommonName '<name>'>"""
        cn = CommonName(name='Coleus')
        assert cn.__repr__() == '<CommonName \'Coleus\'>'

    def test_header(self, app):
        """Return '<._name> Seeds'."""
        cn = CommonName()
        cn._name = 'Foxglove'
        assert cn.header == 'Foxglove Seeds'

    def test_name_getter(self, app):
        """Return contents of ._name"""
        cn = CommonName()
        cn._name = 'Coleus'
        assert cn.name == 'Coleus'

    def test_name_setter(self, app):
        """Set ._name and .slug using passed value."""
        cn = CommonName()
        cn.name = 'Butterfly Weed'
        assert cn._name == 'Butterfly Weed'
        assert cn.slug == slugify('Butterfly Weed')


class TestImage:
    """Test methods of Image in the seeds model."""
    @mock.patch('app.seeds.models.os.remove')
    def test_delete_file(self, mock_remove, app):
        """Delete image file using os.remove."""
        image = Image()
        image.filename = 'hello.jpg'
        image.delete_file()
        mock_remove.assert_called_with(image.full_path)

    @mock.patch('app.seeds.models.os.path.exists')
    def test_exists(self, mock_exists, app):
        """Call os.path.exists for path of image file."""
        mock_exists.return_value = True
        image = Image()
        image.filename = 'hello.jpg'
        assert image.exists()
        mock_exists.assert_called_with(image.full_path)

    def test_full_path(self, app):
        """Return the absolute file path for image name."""
        image = Image()
        image.filename = 'hello.jpg'
        assert image.full_path ==\
            os.path.join(current_app.config.get('IMAGES_FOLDER'),
                         image.filename)


class TestSeed:
    """Test methods of Seed in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <Seed '<name>'>"""
        seed = Seed()
        seed.name = 'Soulmate'
        assert seed.__repr__() == '<Seed \'Soulmate\'>'

    def test_fullname_getter(self, app):
        """.fullname returns ._name, or a string with name and common name."""
        cn = CommonName()
        seed = Seed()
        cn._name = 'Foxglove'
        seed._name = 'Foxy'
        assert seed.fullname == 'Foxy'
        seed.common_name = cn
        assert seed.fullname == 'Foxy Foxglove'

    def test_name_getter(self, app):
        """Return ._name"""
        seed = Seed()
        seed._name = 'Foxy'
        assert seed.name == 'Foxy'

    def test_name_setter(self, app):
        """Set ._name and a slugified version of name to .slug"""
        seed = Seed()
        seed.name = u'Cafe Crème'
        assert seed._name == u'Cafe Crème'
        assert seed.slug == slugify(u'Cafe Crème')

    def test_name_setter_none(self, app):
        """Set ._name and slug to None if .name set to None."""
        seed = Seed()
        seed.name = None
        assert seed._name is None
        assert seed.slug is None

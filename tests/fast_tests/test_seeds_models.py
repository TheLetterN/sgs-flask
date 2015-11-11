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
    is_480th,
    is_decimal,
    is_fraction,
    is_int,
    Packet,
    Price,
    QtyDecimal,
    QtyFraction,
    QtyInteger,
    Quantity480th,
    QuantityDecimal,
    Seed,
    Unit,
    USDInt
)
from tests.conftest import app  # noqa


class TestModuleFunctions:
    """Class to test top-level functions in the seeds model."""
    def test_is_480th_bad_fraction_verify_fraction_off(self, app):
        """Carry on if given a bad fraction with verify_fraction off.

        There should never be a case where we actually want to accept a bad
        fraction, this is just to test that it runs without checking
        is_fraction() if verify_fraction = False. Realistically is_480th
        should never be run on a value that hasn't been verified by
        is_fraction(), there's just no sense in running is_fraction() again
        if we need to run is_480th() in a block that only runs after
        is_fraction() has evaluated to True.
        """
        assert is_480th('1 and 1/4', verify_fraction=False)
        assert is_480th('1/2/4', verify_fraction=False)

    def test_is_480th_bad_fraction_verify_fraction_on(self, app):
        """Return False if verify_fraction is on when given bad fraction."""
        assert not is_480th('1 and 1/4')
        assert not is_480th('1/2/4')

    def test_is_480th_bad_fraction(self, app):
        """Return False if given a Fraction with an invalid denominator."""
        assert not is_480th(Fraction(6, 7))
        assert not is_480th(Fraction(8, 9))
        assert not is_480th(Fraction(10, 11))
        assert not is_480th(Fraction(12, 13))
        assert not is_480th(Fraction(13, 14))

    def test_is_480th_bad_str(self, app):
        """Return False if str contains fraction w/ invalid denom."""
        assert not is_480th('6/7')
        assert not is_480th('1 3/9')
        assert not is_480th('9/11')
        assert not is_480th('4/13')
        assert not is_480th('81/14')

    def test_is_480th_bad_type(self, app):
        """Return False if given data that is not a Fraction or str."""
        assert not is_480th(3.10, verify_fraction=False)
        assert not is_480th(Decimal('1.25'), verify_fraction=False)
        assert not is_480th(42, verify_fraction=False)

    def test_is_480th_valid_fraction(self, app):
        """Return True if given a Fraction with a valid denominator."""
        assert is_480th(Fraction(1, 2))
        assert is_480th(Fraction(2, 3))
        assert is_480th(Fraction(3, 4))
        assert is_480th(Fraction(5, 6))
        assert is_480th(Fraction(7, 8))
        assert is_480th(Fraction(9, 10))
        assert is_480th(Fraction(11, 12))
        assert is_480th(Fraction(14, 15))
        assert is_480th(Fraction(15, 16))

    def test_is_480th_valid_str(self, app):
        """Return True if given a str containing fraction w/ valid denom."""
        assert is_480th('1/2')
        assert is_480th('1 1/3')
        assert is_480th('1/4')
        assert is_480th('43 1/6')
        assert is_480th('1/8')
        assert is_480th('41/12')
        assert is_480th('2/15')
        assert is_480th('1 3/16')

    def test_is_decimal_bad_str(self, app):
        """Return false if string contains invalid data."""
        assert not is_decimal('$2.99')
        assert not is_decimal('43.44usd')
        assert not is_decimal('3.4.5')
        assert not is_decimal('3. 4')
        assert not is_decimal('3 .4')
        assert not is_decimal('1')
        assert not is_decimal('1/3')
        assert not is_decimal('1 2/3')

    def test_is_decimal_bad_type(self, app):
        """Return false if type is not float, Decimal, or str."""
        assert not is_decimal(12)
        assert not is_decimal(Fraction(3, 4))
        assert not is_decimal([3.4, 4.5])

    def test_is_decimal_decimal_or_float(self, app):
        """Return True given a Decimal or float type."""
        assert is_decimal(3.14)
        assert is_decimal(Decimal('3.14'))

    def test_is_decimal_str_valid(self, app):
        """Return True if string contains a valid decimal number."""
        assert is_decimal('3.14')
        assert is_decimal(' 42.24 ')

    def test_is_fraction_bad_str(self, app):
        """Return False if string is not a valid fraction."""
        assert not is_fraction('1 a2/4')
        assert not is_fraction('1 3/g44')
        assert not is_fraction('a 1/2')
        assert not is_fraction('1 1 3/2')
        assert not is_fraction('x/3')
        assert not is_fraction('2/y')
        assert not is_fraction('1/2/3')
        assert not is_fraction('12')
        assert not is_fraction('3.14')

    def test_is_fraction_bad_type(self, app):
        """Return False if given data of a type other than str or Fraction."""
        assert not is_fraction(12)
        assert not is_fraction(3.14)
        assert not is_fraction(['4/3', '1/2'])

    def test_is_fraction_fraction(self, app):
        """Return True given a Fraction object."""
        assert is_fraction(Fraction(1, 3))
        assert is_fraction(Fraction(5, 2))
        assert is_fraction(Fraction(12, 131))

    def test_is_fraction_str_fraction(self, app):
        """Return True if given a string containing a valid fraction."""
        assert is_fraction('1/2')
        assert is_fraction('3/4')
        assert is_fraction('234/113')

    def test_is_fraction_str_mixed(self, app):
        """Return True if given a string containing a valid mixed number."""
        assert is_fraction('1 1/2')
        assert is_fraction('2 3/4')
        assert is_fraction('243 5/44')

    def test_is_fraction_zero_denominator(self, app):
        """Return False if string contains fraction with denom of 0."""
        assert not is_fraction('1/0')
        assert not is_fraction('1 3/0')
        assert not is_fraction('43434/0')

    def test_is_int_bad_str(self, app):
        """Return False if str does not contain a valid int."""
        assert not is_int('1/3')
        assert not is_int('1 1/4')
        assert not is_int('3.14')
        assert not is_int('1a')

    def test_is_int_bad_type(self, app):
        """Return False if given a type that isn't int or str."""
        assert not is_int(3.14)
        assert not is_int(Decimal('3.14'))
        assert not is_int(Fraction(3, 4))

    def test_is_int_int(self, app):
        """Return True if value is of type int."""
        assert is_int(12)
        assert is_int(42)

    def test_is_int_str_valid(self, app):
        """Return true if value is a str containing a valid int."""
        assert is_int('12')
        assert is_int(' 42 ')


class TestQuantity480th:
    """Test methods of the Quantity480th TypeDecorator in the seeds model."""
    def test_from_480ths_valid_ints(self, app):
        """Return a Fraction given a valid int."""
        assert Quantity480th.from_480ths(240) == Fraction(1, 2)
        assert Quantity480th.from_480ths(400) == Fraction(5, 6)
        assert Quantity480th.from_480ths(6180) == Fraction(103, 8)

    def test_from_480ths_bad_type(self, app):
        """Raise a TypeError given non-int data."""
        with pytest.raises(TypeError):
            Quantity480th.from_480ths(3.14)
        with pytest.raises(TypeError):
            Quantity480th.from_480ths(Decimal('1000.0'))
        with pytest.raises(TypeError):
            Quantity480th.from_480ths('240')
        with pytest.raises(TypeError):
            Quantity480th.from_480ths(Fraction(1, 4))

    def test_process_bind_param(self, app):
        """Return result of .to_480ths() for value, None if no value."""
        qty = Quantity480th()
        assert qty.process_bind_param('1/2', None) == 240
        assert qty.process_bind_param(None, None) is None

    def test_process_result_value(self, app):
        """Return result of .from_480ths() for value, None if no value."""
        qty = Quantity480th()
        assert qty.process_result_value(240, None) == Fraction(1, 2)
        assert qty.process_result_value(None, None) is None

    def test_to_480ths_bad_denominator(self, app):
        """Raise a ValueError if 480 not divisible by denominator."""
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/7')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/9')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/11')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/13')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/14')

    def test_to_480ths_bad_type(self, app):
        """Raise a TypeError if given data that is not a str or Fraction."""
        with pytest.raises(TypeError):
            Quantity480th.to_480ths([1, 3])
        with pytest.raises(TypeError):
            Quantity480th.to_480ths((1, 4))
        with pytest.raises(TypeError):
            Quantity480th.to_480ths({'numerator': 1, 'denominator': 4})

    def test_to_480ths_string_bad_format(self, app):
        """Raise a ValueError if string can't be parsed."""
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/2 1')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('one fourth')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1 1//2')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/2/3')
        with pytest.raises(ValueError):
            Quantity480th.to_480ths('1/n')

    def test_to_480ths_string_fraction(self, app):
        """Return an int given a string containing a valid fraction."""
        assert Quantity480th.to_480ths('1/2') == 240
        assert Quantity480th.to_480ths('5/6') == 400
        assert Quantity480th.to_480ths('15/16') == 450

    def test_to_480ths_string_with_space(self, app):
        """Return an int given a valid mixed number in a string."""
        assert Quantity480th.to_480ths('1 1/2') == 720
        assert Quantity480th.to_480ths('12 7/8') == 6180

    def test_to_480ths_valid_fractions(self, app):
        """Return an int given a valid Fraction."""
        assert Quantity480th.to_480ths(Fraction(1, 2)) == 240
        assert Quantity480th.to_480ths(Fraction(2, 3)) == 320
        assert Quantity480th.to_480ths(Fraction(3, 4)) == 360
        assert Quantity480th.to_480ths(Fraction(4, 5)) == 384
        assert Quantity480th.to_480ths(Fraction(5, 6)) == 400
        assert Quantity480th.to_480ths(Fraction(7, 8)) == 420
        assert Quantity480th.to_480ths(Fraction(9, 10)) == 432
        assert Quantity480th.to_480ths(Fraction(11, 12)) == 440
        assert Quantity480th.to_480ths(Fraction(14, 15)) == 448
        assert Quantity480th.to_480ths(Fraction(15, 16)) == 450
        assert Quantity480th.to_480ths(Fraction(3, 2)) == 720
        assert Quantity480th.to_480ths(Fraction(103, 8)) == 6180


class TestQuantityDecimal:
    """Test methods of the QuantityDecimal TypeDecorator in seeds model."""
    def test_decimal_to_int_invalid_data(self, app):
        """Raise a ValueError given data that can't be coerced to Decimal."""
        with pytest.raises(ValueError):
            QuantityDecimal.decimal_to_int('4.3.32')
        with pytest.raises(ValueError):
            QuantityDecimal.decimal_to_int('$4.32')
        with pytest.raises(ValueError):
            QuantityDecimal.decimal_to_int('4.4a')
        with pytest.raises(ValueError):
            QuantityDecimal.decimal_to_int(['4.2', '4.4'])
        with pytest.raises(ValueError):
            QuantityDecimal.decimal_to_int({'quantity': '42.4'})

    def test_decimal_to_int_valid_decimals(self, app):
        """Return an int given data that is or can be converted to Decimal."""
        assert QuantityDecimal.decimal_to_int(Decimal('1.4')) == 14000
        assert QuantityDecimal.decimal_to_int('3.14159') == 31415
        assert QuantityDecimal.decimal_to_int(234.1) == 2341000

    def test_int_to_decimal_not_int(self, app):
        """Raise a TypeError given non-int data."""
        with pytest.raises(TypeError):
            QuantityDecimal.int_to_decimal('14000')
        with pytest.raises(TypeError):
            QuantityDecimal.int_to_decimal(400.243)
        with pytest.raises(TypeError):
            QuantityDecimal.int_to_decimal(Decimal('10000'))

    def test_int_to_decimal_valid_ints(self, app):
        """Return a Decimal the db int represented."""
        assert QuantityDecimal.int_to_decimal(3) == Decimal('0.0003')
        assert QuantityDecimal.int_to_decimal(14000) == Decimal('1.4')
        assert QuantityDecimal.int_to_decimal(31415) == Decimal('3.1415')

    def test_process_bind_param(self, app):
        """Return result of .decimal_to_int() for value, None if None."""
        qty = QuantityDecimal()
        assert qty.process_bind_param(Decimal('1.4'), None) == 14000
        assert qty.process_bind_param(None, None) is None

    def test_process_result_value(self, app):
        """Return result of .int_to_decimal() for value, None if None."""
        qty = QuantityDecimal()
        assert qty.process_result_value(14000, None) == Decimal('1.4')
        assert qty.process_result_value(None, None) is None


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
        """Return ._category."""
        category = Category()
        category._category = 'Perennial Flower'
        assert category.category == 'Perennial Flower'

    def test_category_setter(self, app):
        """Set ._category and a pluralized, slugified v. to .slug."""
        category = Category()
        category.category = 'Annual Flower'
        assert category._category == 'Annual Flower'
        assert category.slug == slugify(pluralize('Annual Flower'))

    def test_header(self, app):
        """Return '<._category> Seeds'"""
        category = Category()
        category.category = 'Annual Flower'
        assert category.header == 'Annual Flower Seeds'

    def test_plural(self, app):
        """Return plural version of ._category."""
        category = Category()
        category.category = 'Annual Flower'
        assert category.plural == 'Annual Flowers'

    def test_repr(self, app):
        """Return string formatted <Category '<category>'>"""
        category = Category()
        category.category = 'vegetable'
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


class TestPacket:
    """Test methods of Packet in the seeds model."""
    def test_price_getter(self, app):
        """Return ._price."""
        pkt = Packet()
        pkt._price = Price(price=Decimal('2.99'))
        assert pkt.price == Decimal('2.99')

    def test_quantity_equals_not_480th(self, app):
        """Raise a ValueError given a denominator 480 isn't divisible by."""
        pkt = Packet()
        with pytest.raises(ValueError):
            pkt.quantity_equals(Fraction(1, 7))
        with pytest.raises(ValueError):
            pkt.quantity_equals('3/11')

    def test_quantity_getter_too_many_qty(self, app):
        """Raise a RuntimeError if more than one ._qty_x set."""
        pkt = Packet()
        pkt._qty_decimal = QtyDecimal(Decimal('3.14'))
        assert pkt.quantity == Decimal('3.14')
        pkt._qty_fraction = QtyFraction(Fraction(1, 2))
        with pytest.raises(RuntimeError):
            pkt.quantity
        pkt._qty_integer = QtyInteger(100)
        with pytest.raises(RuntimeError):
            pkt.quantity
        pkt._qty_decimal = None
        with pytest.raises(RuntimeError):
            pkt.quantity
        pkt._qty_fraction = None
        assert pkt.quantity == 100

    def test_quantity_setter_bad_data(self, app):
        """Raise a ValueError if data could not be determined to be valid."""
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = '$2.99'
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = 'tree fiddy'
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = [1, 2, 3, 4]

    def test_quantity_setter_fraction_not_480th(self, app):
        """Raise a ValueError if 480 is not divisible by denominator."""
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(3, 7)
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(5, 9)
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(9, 11)
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(10, 13)
        with pytest.raises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(11, 14)


class TestQtyDecimal:
    """Test methods of QtyDecimal in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <QtyDecimal '<value>'>."""
        qty = QtyDecimal(3.1415)
        assert qty.__repr__() == '<QtyDecimal \'3.1415\'>'


class TestQtyFraction:
    """Test methods of QtyFraction in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <QtyFraction '<value>'>."""
        qty = QtyFraction('3/4')
        assert qty.__repr__() == '<QtyFraction \'3/4\'>'


class TestQtyInteger:
    """Test methods of QtyInteger in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <QtyInteger '<value>'>."""
        qty = QtyInteger('100')
        assert qty.__repr__() == '<QtyInteger \'100\'>'


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

    def test_list_botanical_names(self, app):
        """Return a string list of botanical names associated with a seed."""
        bn1 = BotanicalName()
        bn2 = BotanicalName()
        bn3 = BotanicalName()
        seed = Seed()
        bn1.name = 'Digitalis purpurea'
        bn2.name = 'Digitalis watchus'
        bn3.name = 'Innagada davida'
        seed.name = 'Foxy'
        seed.botanical_names.append(bn1)
        seed.botanical_names.append(bn2)
        seed.botanical_names.append(bn3)
        assert seed.list_botanical_names() == 'Digitalis purpurea, Digitalis '\
            'watchus, Innagada davida'

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


class TestUnit:
    """Test methods of Unit in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <Unit '<unit>'>"""
        ut = Unit()
        ut.unit = 'frogs'
        assert ut.__repr__() == '<Unit \'frogs\'>'

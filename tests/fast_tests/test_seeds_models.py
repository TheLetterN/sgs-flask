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
    Index,
    CommonName,
    Image,
    Cultivar,
    Packet,
    Quantity,
    Series,
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

    def test_usd_to_decimal_float(self):
        """Floats should convert cleanly to Decimal."""
        assert USDInt.usd_to_decimal(3.50) == Decimal('3.50')
        assert USDInt.usd_to_decimal(3.14159) == Decimal('3.14')
        assert USDInt.usd_to_decimal(1.999) == Decimal('1.99')

    def test_usd_to_decimal_str(self):
        """Strings containing a decimal number should be convertable."""
        assert USDInt.usd_to_decimal('$3.50') == Decimal('3.50')
        assert USDInt.usd_to_decimal('3.14159') == Decimal('3.14')
        assert USDInt.usd_to_decimal('4') == Decimal('4.00')

    def test_usd_to_decimal_bad_data(self):
        """Raise ValueError given bad data."""
        with pytest.raises(ValueError):
            USDInt.usd_to_decimal(Fraction(3, 4))
        with pytest.raises(ValueError):
            USDInt.usd_to_decimal('$3.50 US')
        with pytest.raises(ValueError):
            USDInt.usd_to_decimal(['3.50'])

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

    def test_list_syn_parents_as_string(self):
        """Return a string list of BotanicalNames that have bn as synonym."""
        bn = BotanicalName(name='Digitalis purpurea')
        sp1 = BotanicalName(name='Digitalis watchus')
        sp2 = BotanicalName(name='Digitalis scalus')
        sp3 = BotanicalName(name='Digitalis über alles')
        assert bn.list_syn_parents_as_string() == ''
        bn.syn_parents = [sp1, sp2, sp3]
        assert bn.list_syn_parents_as_string() == 'Digitalis watchus, '\
                                                  'Digitalis scalus, '\
                                                  'Digitalis über alles'

    def test_list_synonyms_as_string(self):
        """Return a string list of synonyms of BotanicalName."""
        bn = BotanicalName(name='Digitalis purpurea')
        s1 = BotanicalName(name='Digitalis watchus')
        s2 = BotanicalName(name='Digitalis scalus')
        s3 = BotanicalName(name='Digitalis über alles')
        assert bn.list_synonyms_as_string() == ''
        bn.synonyms = [s1, s2, s3]
        assert bn.list_synonyms_as_string() == 'Digitalis watchus, '\
                                               'Digitalis scalus, '\
                                               'Digitalis über alles'

    def test_set_synonyms_from_string_list_empty_string(self):
        """Call self.clear_synonyms() if given a blank stringi or space."""
        with mock.patch('app.seeds.models.BotanicalName.clear_synonyms') as m:
            bn = BotanicalName(name='Digitalis purpurea')
            bn.set_synonyms_from_string_list('')
            assert m.called
            bn.set_synonyms_from_string_list(' ')
            assert m.call_count == 2

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


class TestIndex:
    """Test methods of Index in the seeds model."""
    def test_index_getter(self, app):
        """Return ._name."""
        index = Index()
        index._name = 'Perennial Flower'
        assert index.name == 'Perennial Flower'

    def test_index_setter(self, app):
        """Set ._name and a pluralized, slugified v. to .slug."""
        index = Index()
        index.name = 'Annual Flower'
        assert index._name == 'Annual Flower'
        assert index.slug == slugify(pluralize('Annual Flower'))

    def test_header(self, app):
        """Return '<._name> Seeds'"""
        index = Index()
        index.name = 'Annual Flower'
        assert index.header == 'Annual Flower Seeds'

    def test_plural(self, app):
        """Return plural version of ._name."""
        index = Index()
        index.name = 'Annual Flower'
        assert index.plural == 'Annual Flowers'

    def test_repr(self, app):
        """Return string formatted <Index '<index>'>"""
        index = Index()
        index.name = 'vegetable'
        assert index.__repr__() == '<Index \'vegetable\'>'


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

    def test_list_syn_parents_as_string(self):
        """Return string list of syn_parents, or empty string if none."""
        cn = CommonName(name='Foxglove')
        s1 = CommonName(name='Digitalis')
        s2 = CommonName(name='Fauxglove')
        s3 = CommonName(name='Fawksglove')
        assert cn.list_syn_parents_as_string() == ''
        cn.syn_parents = [s1, s2, s3]
        assert cn.list_syn_parents_as_string() == 'Digitalis, Fauxglove, '\
                                                  'Fawksglove'

    def test_list_synonyms_as_string(self):
        """Return string list of synonyms, or empty string if none."""
        cn = CommonName(name='Foxglove')
        s1 = CommonName(name='Digitalis')
        s2 = CommonName(name='Fauxglove')
        s3 = CommonName(name='Fawksglove')
        assert cn.list_synonyms_as_string() == ''
        cn.synonyms = [s1, s2, s3]
        assert cn.list_synonyms_as_string() == 'Digitalis, Fauxglove, '\
                                               'Fawksglove'

    def test_set_synonyms_from_string_list_empty_string(self):
        """Call self.clear_synonyms if given an empty string or space."""
        cn = CommonName(name='Foxglove')
        with mock.patch('app.seeds.models.CommonName.clear_synonyms') as m:
            cn.set_synonyms_from_string_list('')
            assert m.called
            cn.set_synonyms_from_string_list(' ')
            assert m.call_count == 2


class TestCultivar:
    """Test methods of Cultivar in the seeds model."""
    def test_repr(self, app):
        """Return a string formatted <Cultivar '<name>'>"""
        cultivar = Cultivar()
        cultivar.name = 'Soulmate'
        assert cultivar.__repr__() == '<Cultivar \'Soulmate\'>'

    def test_fullname_getter(self, app):
        """.fullname returns ._name, or a string with name and common name."""
        cn = CommonName()
        cultivar = Cultivar()
        cn._name = 'Foxglove'
        cultivar._name = 'Foxy'
        assert cultivar.fullname == 'Foxy'
        cultivar.common_name = cn
        assert cultivar.fullname == 'Foxy Foxglove'
        cultivar.series = Series(name='Spotty')
        assert cultivar.fullname == 'Spotty Foxy Foxglove'

    def test_name_getter(self, app):
        """Return ._name"""
        cultivar = Cultivar()
        cultivar._name = 'Foxy'
        assert cultivar.name == 'Foxy'

    def test_name_setter(self, app):
        """Set ._name and a slugified version of name to .slug"""
        cultivar = Cultivar()
        cultivar.name = u'Cafe Crème'
        assert cultivar._name == u'Cafe Crème'
        assert cultivar.slug == slugify(u'Cafe Crème')

    def test_name_setter_none(self, app):
        """Set ._name and slug to None if .name set to None."""
        cultivar = Cultivar()
        cultivar.name = None
        assert cultivar._name is None
        assert cultivar.slug is None

    def test_list_syn_parents_as_string(self):
        """List parents of a synonym as a string, blank string if none."""
        cv = Cultivar(name='Foxy')
        s1 = Cultivar(name='Fauxy')
        s2 = Cultivar(name='Fawksy')
        s3 = Cultivar(name='Focksy')
        assert cv.list_syn_parents_as_string() == ''
        cv.syn_parents = [s1, s2, s3]
        assert cv.list_syn_parents_as_string() == 'Fauxy, Fawksy, Focksy'

    def test_list_synonyms_as_string(self):
        """List synonyms as a string, blank string if none."""
        cv = Cultivar(name='Foxy')
        s1 = Cultivar(name='Fauxy')
        s2 = Cultivar(name='Fawksy')
        s3 = Cultivar(name='Focksy')
        assert cv.list_synonyms_as_string() == ''
        cv.synonyms = [s1, s2, s3]
        assert cv.list_synonyms_as_string() == 'Fauxy, Fawksy, Focksy'

    def test_set_synonyms_from_string_list_empty_string(self):
        """Call self.clear_synonyms() given an empty string or space."""
        cultivar = Cultivar(name='Foxy')
        with mock.patch('app.seeds.models.Cultivar.clear_synonyms') as m:
            cultivar.set_synonyms_from_string_list('')
            assert m.called
            cultivar.set_synonyms_from_string_list(' ')
            assert m.call_count == 2


class TestImage:
    """Test methods of Image in the seeds model."""
    def test_repr(self):
        """Return string representing Image."""
        image = Image(filename='hello.jpg')
        assert image.__repr__() == '<Image filename: \'hello.jpg\'>'

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
    def test_repr(self):
        """Return a string representing a packet."""
        pk = Packet()
        pk.sku = '8675309'
        assert pk.__repr__() == '<Packet SKU #8675309>'

    def test_info_getter(self):
        """Return a string containing onformation on the packet."""
        pk = Packet()
        pk.sku = '8675309'
        pk.price = '3.50'
        assert pk.info == 'SKU #8675309: $3.50 for None None'
        pk.quantity = Quantity(100, 'seeds')
        assert pk.info == 'SKU #8675309: $3.50 for 100 seeds'


class TestQuantity:
    """Test methods of Quantity in the seeds model."""
    def test_repr(self):
        """Return a string representing a Quantity."""
        qty = Quantity(100, 'seeds')
        assert qty.__repr__() == '<Quantity \'100 seeds\'>'

    def test_dec_check(self):
        """Dec check returns True if value looks like a decimal number."""
        assert Quantity.dec_check(3.145)
        assert Quantity.dec_check(Decimal('1.75'))
        assert Quantity.dec_check('4.55')
        assert not Quantity.dec_check(Fraction(3, 4))
        assert not Quantity.dec_check('$3.50')
        assert not Quantity.dec_check(33)
        assert not Quantity.dec_check([4.3, 35.34])

    def test_fraction_to_str(self):
        """Return fractions in a human-friendly string format.

        Raise TypeError if not given a Fraction.
        """
        assert Quantity.fraction_to_str(Fraction(3, 4)) == '3/4'
        assert Quantity.fraction_to_str(Fraction(13, 3)) == '4 1/3'
        assert Quantity.fraction_to_str(Fraction(235, 22)) == '10 15/22'
        with pytest.raises(TypeError):
            Quantity.fraction_to_str(3.1415)
        with pytest.raises(TypeError):
            Quantity.fraction_to_str(Decimal('3.253'))
        with pytest.raises(TypeError):
            Quantity.fraction_to_str(2432)
        with pytest.raises(TypeError):
            Quantity.fraction_to_str('4/3')

    def test_for_cmp(self):
        """Return appropriate type for comparing quantities."""
        assert isinstance(Quantity.for_cmp(3.145), float)
        assert isinstance(Quantity.for_cmp(Decimal('2.544')), float)
        assert isinstance(Quantity.for_cmp('5.456'), float)
        assert isinstance(Quantity.for_cmp(132), int)
        assert isinstance(Quantity.for_cmp(Fraction(3, 4)), Fraction)

    def test_str_to_fraction(self):
        """Return a Fraction given a valid string containing a fraction.

        If val not str, raise TypeError, if not parseable, raise ValueError.
        """
        assert Quantity.str_to_fraction('3/4') == Fraction(3, 4)
        assert Quantity.str_to_fraction('1 1/2') == Fraction(3, 2)
        assert Quantity.str_to_fraction('3 4/11') == Fraction(37, 11)
        assert Quantity.str_to_fraction('13/3') == Fraction(13, 3)
        with pytest.raises(ValueError):
            Quantity.str_to_fraction('3/4/3')
        with pytest.raises(ValueError):
            Quantity.str_to_fraction('3 4 3/4')
        with pytest.raises(ValueError):
            Quantity.str_to_fraction('$2.5')
        with pytest.raises(ValueError):
            Quantity.str_to_fraction('$2 3/4')
        with pytest.raises(TypeError):
            Quantity.str_to_fraction(Fraction(3, 4))
        with pytest.raises(TypeError):
            Quantity.str_to_fraction(2.5)
        with pytest.raises(TypeError):
            Quantity.str_to_fraction(100)
        with pytest.raises(TypeError):
            Quantity.str_to_fraction(Decimal('2.5'))

    def test_html_value(self):
        """Return HTML entities or special HTML for fractions.

        Return a string of self.value if it is not a fraction.
        """
        qty = Quantity()
        qty.value = Fraction(1, 4)
        assert qty.html_value == '&frac14;'
        qty.value = Fraction(1, 2)
        assert qty.html_value == '&frac12;'
        qty.value = Fraction(3, 4)
        assert qty.html_value == '&frac34;'
        qty.value = Fraction(1, 3)
        assert qty.html_value == '&#8531;'
        qty.value = Fraction(2, 3)
        assert qty.html_value == '&#8532;'
        qty.value = Fraction(1, 5)
        assert qty.html_value == '&#8533;'
        qty.value = Fraction(2, 5)
        assert qty.html_value == '&#8534;'
        qty.value = Fraction(3, 5)
        assert qty.html_value == '&#8535;'
        qty.value = Fraction(4, 5)
        assert qty.html_value == '&#8536;'
        qty.value = Fraction(1, 6)
        assert qty.html_value == '&#8537;'
        qty.value = Fraction(5, 6)
        assert qty.html_value == '&#8538;'
        qty.value = Fraction(1, 8)
        assert qty.html_value == '&#8539;'
        qty.value = Fraction(3, 8)
        assert qty.html_value == '&#8540;'
        qty.value = Fraction(5, 8)
        assert qty.html_value == '&#8541;'
        qty.value = Fraction(7, 8)
        assert qty.html_value == '&#8542;'
        qty.value = Fraction(9, 11)
        assert qty.html_value == '<span class="fraction"><sup>9</sup>&frasl;'\
                                 '<sub>11</sub></span>'
        qty.value = Decimal('3.1415')
        assert qty.html_value == '3.1415'
        qty.value = 100
        assert qty.html_value == '100'
        qty.value = '100'
        assert qty.html_value == '100'

    def test_value_getter(self):
        """Return value in appropriate format."""
        qty = Quantity()
        qty.value = '3.1415'
        assert qty.value == 3.1415
        qty.value = Decimal('5.21')
        assert qty.value == 5.21
        qty.value = 100
        assert qty.value == 100
        qty.value = '100'
        assert qty.value == 100
        qty.value = '4/3'
        assert qty.value == Fraction(4, 3)
        qty.value = Fraction(1, 2)
        assert qty.value == Fraction(1, 2)
        qty.value = None
        assert qty.value is None

    def test_value_setter(self):
        """Set value appropriately given valid data."""
        qty = Quantity()
        qty.value = 100
        assert qty._numerator == 100
        assert qty._denominator == 1
        assert not qty.is_decimal
        assert qty._float == 100.0
        qty.value = 100
        assert qty._numerator == 100
        assert qty._denominator == 1
        assert not qty.is_decimal
        assert qty._float == 100.0
        qty.value = 3.1415
        assert qty.is_decimal
        assert qty._numerator is None
        assert qty._denominator is None
        assert qty._float == 3.1415
        qty.value = '3.1415'
        assert qty.is_decimal
        assert qty._numerator is None
        assert qty._denominator is None
        assert qty._float == 3.1415
        qty.value = Decimal('3.1415')
        assert qty.is_decimal
        assert qty._numerator is None
        assert qty._denominator is None
        assert qty._float == 3.1415
        qty.value = Fraction(1, 2)
        assert not qty.is_decimal
        assert qty._numerator == 1
        assert qty._denominator == 2
        assert qty._float == 0.5
        qty.value = Fraction(5, 2)
        assert not qty.is_decimal
        assert qty._numerator == 5
        assert qty._denominator == 2
        assert qty._float == 2.5
        qty.value = '3/4'
        assert not qty.is_decimal
        assert qty._numerator == 3
        assert qty._denominator == 4
        assert qty._float == 0.75
        qty.value = '1 1/4'
        assert not qty.is_decimal
        assert qty._numerator == 5
        assert qty._denominator == 4
        assert qty._float == 1.25
        qty.value = None
        assert qty.is_decimal is None
        assert qty._numerator is None
        assert qty._denominator is None
        assert qty._float is None


class TestSeries:
    """Test methods of the Series class in seeds.models."""
    def test_fullname(self):
        """Returns name of series along with common name."""
        ser = Series()
        assert ser.fullname is None
        ser.name = 'Dalmatian'
        assert ser.fullname == 'Dalmatian'
        ser.common_name = CommonName(name='Foxglove')
        assert ser.fullname == 'Dalmatian Foxglove'

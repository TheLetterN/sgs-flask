# -*- coding: utf-8 -*-
import os
import pytest
from decimal import Decimal
from flask import current_app
from fractions import Fraction
from unittest import mock
from app.seeds.models import (
    BotanicalName,
    dbify,
    Category,
    CommonName,
    Image,
    Index,
    Cultivar,
    Packet,
    Quantity,
    Synonym,
    SynonymsMixin,
    USDollar
)


class TestModuleFunctions:
    """Test module-level functions in app.seeds.models."""
    def test_dbify(self):
        """Convert a string into a proper titlecase version."""
        assert dbify('stuff') == 'Stuff'
        assert dbify('This is a Title') == 'This Is a Title'
        assert dbify('lowercase stuff') == 'Lowercase Stuff'
        assert dbify('You will forget-me-not') == 'You Will Forget-me-not'
        assert dbify('tears for fears') == 'Tears for Fears'
        assert dbify('ashes to ashes') == 'Ashes to Ashes'
        assert dbify('CRUISE CONTROL FOR COOL') == 'Cruise Control for Cool'


class TestSynonymsMixin:
    """Test methods/properties of the SynonymsMixin class.

    Note:
        SynonymsMixin does not have a synonyms attribute, but since this is
        Python we can simulate it by adding a synonyms attribute of type list
        to an instance of SynonymsMixin.
    """
    def test_synonyms_string_getter(self):
        """Return a string listing the names of all synonyms of an object."""
        smi = SynonymsMixin()
        smi.synonyms = [Synonym(name='pigeon'),
                        Synonym(name='rock dove'),
                        Synonym(name='flying rat')]
        assert smi.synonyms_string == 'pigeon, rock dove, flying rat'

    @mock.patch('app.seeds.models.db.session.flush')
    def test_synonyms_string_setter_sets_new(self, m_f):
        """Create new synonyms if object has none."""
        smi = SynonymsMixin()
        smi.synonyms = list()
        smi.synonyms_string = 'pigeon, rock dove, flying rat'
        assert len(smi.synonyms) == 3
        assert smi.synonyms_string == 'pigeon, rock dove, flying rat'
        assert m_f.called

    @mock.patch('app.seeds.models.db.session.flush')
    def test_synonyms_string_setter_clears_old(self, m_f):
        """Remove synonyms if given a falsey value."""
        smi = SynonymsMixin()
        synonyms = [Synonym(name='pigeon'),
                    Synonym(name='rock dove'),
                    Synonym(name='flying rat')]
        smi.synonyms = synonyms
        assert len(smi.synonyms) == 3
        smi.synonyms_string = None
        assert not smi.synonyms
        assert not m_f.called
        smi.synonyms = synonyms
        smi.synonyms_string = ''
        assert not smi.synonyms

    @mock.patch('app.seeds.models.db.session.flush')
    @mock.patch('app.seeds.models.db.session.delete')
    @mock.patch('app.seeds.models.inspect')
    def test_synonyms_string_setter_deletes_old(self, m_i, m_d, m_f):
        """Delete removed synonyms that are in a persistent db state."""
        state = mock.MagicMock()
        state.persistent = True
        m_i.return_value = state
        smi = SynonymsMixin()
        synonyms = [Synonym(name='pigeon'),
                    Synonym(name='rock dove'),
                    Synonym(name='flying rat')]
        smi.synonyms = list(synonyms)
        smi.synonyms_string = None
        assert not smi.synonyms
        m_i.assert_any_call(synonyms[0])
        m_i.assert_any_call(synonyms[1])
        m_i.assert_any_call(synonyms[2])
        assert m_d.call_count == 3
        assert m_f.called

    @mock.patch('app.seeds.models.db.session.flush')
    def test_synonyms_string_setter_handles_spaces(self, m_f):
        """Do not create Synonyms from whitespace."""
        smi = SynonymsMixin()
        smi.synonyms = list()
        smi.synonyms_string = ' , \t, space, \n'
        assert len(smi.synonyms) == 1
        assert smi.synonyms_string == 'space'


class TestUSDollar:
    """Test methods of the USDollar TypeDecorator in the seeds model."""
    def test_cents_to_usd(self):
        """Return a Decimal USD value given an integer."""
        assert USDollar.cents_to_usd(100) == Decimal('1.00')
        assert USDollar.cents_to_usd(299) == Decimal('2.99')
        assert USDollar.cents_to_usd(350) == Decimal('3.50')

    def test_cents_to_usd_two_decimal_places(self):
        """Always return a Decimal with 2 decimal places."""
        assert str(USDollar.cents_to_usd(100)) == '1.00'
        assert str(USDollar.cents_to_usd(350)) == '3.50'
        assert str(USDollar.cents_to_usd(1000)) == '10.00'

    def test_usd_to_cents_valid_non_strings(self):
        """Return an int given a valid non-string type."""
        assert USDollar.usd_to_cents(1) == 100
        assert USDollar.usd_to_cents(2.99) == 299
        assert USDollar.usd_to_cents(3.999) == 399
        assert USDollar.usd_to_cents(Decimal('1.99')) == 199
        assert USDollar.usd_to_cents(3.14159265) == 314

    def test_usd_to_cents_valid_string(self):
        """Return an int given a valid string containing a dollar amount."""
        assert USDollar.usd_to_cents('$2.99') == 299
        assert USDollar.usd_to_cents('3.00') == 300
        assert USDollar.usd_to_cents('2.50$') == 250
        assert USDollar.usd_to_cents('$ 1.99') == 199
        assert USDollar.usd_to_cents('4.99 $') == 499
        assert USDollar.usd_to_cents(' 3.50 ') == 350
        assert USDollar.usd_to_cents('4') == 400
        assert USDollar.usd_to_cents('5.3') == 530
        assert USDollar.usd_to_cents('3.9999') == 399


class TestIndex:
    """Test methods of Index in the seeds model."""
    def test_repr(self):
        """Return string formatted <Index '<index>'>"""
        index = Index()
        index.name = 'vegetable'
        assert index.__repr__() == '<Index \'vegetable\'>'

    def test_header(self):
        """Return '<._name> Seeds'"""
        index = Index()
        index.name = 'Annual Flower'
        assert index.header == 'Annual Flower Seeds'

    def test_plural(self):
        """Return plural version of ._name."""
        index = Index()
        index.name = 'Annual Flower'
        assert index.plural == 'Annual Flowers'


class TestCommonName:
    """Test methods of CommonName in the seeds model."""
    def test_repr(self):
        """Return string formatted <CommonName '<name>'>"""
        cn = CommonName(name='Coleus')
        assert cn.__repr__() == '<CommonName \'Coleus\'>'

    def test_header(self):
        """Return '<._name> Seeds'."""
        cn = CommonName()
        cn.name = 'Foxglove'
        assert cn.header == 'Foxglove Seeds'

    def test_queryable_dict(self):
        """Return a dict containing the name and index of a CommonName."""
        cn = CommonName()
        assert cn.queryable_dict == {'Common Name': None, 'Index': None}
        cn.name = 'Foxglove'
        assert cn.queryable_dict == {'Common Name': 'Foxglove', 'Index': None}
        cn.index = Index(name='Perennial')
        assert cn.queryable_dict == {'Common Name': 'Foxglove',
                                     'Index': 'Perennial'}

    @mock.patch('app.seeds.models.CommonName.from_queryable_values')
    def test_from_queryable_dict(self, m_fqv):
        """Run CommonName.from_queryable_values with params from dict."""
        CommonName.from_queryable_dict(d={'Common Name': 'Foxglove',
                                          'Index': 'Perennial'})
        m_fqv.assert_called_with(name='Foxglove', index='Perennial')


class TestBotanicalName:
    """Test methods of BotanicalName in the seeds model."""
    def test_repr(self):
        """Return a string in format <BotanicalName '<botanical_name>'>"""
        bn = BotanicalName(name='Asclepias incarnata')
        assert bn.__repr__() == '<BotanicalName \'Asclepias incarnata\'>'

    def test_validate_more_than_two_words(self):
        """A botanical name is still valid with more than 2 words."""
        assert BotanicalName.validate('Brassica oleracea Var.')

    def test_validate_not_a_string(self):
        """Return False when given non-string data."""
        assert not BotanicalName.validate(42)
        assert not BotanicalName.validate(('foo', 'bar'))
        assert not BotanicalName.validate(dict(foo='bar'))

    def test_validate_upper_in_wrong_place(self):
        """The only uppercase letter in the first word should be the first."""
        assert not BotanicalName.validate('AscLepias incarnata')

    def test_validate_starts_with_lower(self):
        """The first letter of a botanical name should be uppercase."""
        assert not BotanicalName.validate('asclepias incarnata')

    def test_validate_valid_binomen(self):
        """Returns true if botanical_name contains a valid binomen."""
        assert BotanicalName.validate('Asclepias incarnata')
        assert BotanicalName.validate('Helianthus anuus')
        assert BotanicalName.validate('Hydrangea Lacecap Group')


class TestCategory:
    """Test methods of the Category class in seeds.models."""
    def test_repr(self):
        """Return formatted string with full name."""
        cat = Category(name='Polkadot',
                       common_name=CommonName(name='Foxglove'))
        assert cat.__repr__() == '<Category \'Polkadot Foxglove\'>'

    def test_fullname(self):
        """Returns name of category along with common name."""
        ser = Category()
        assert ser.fullname is None
        ser.name = 'Dalmatian'
        assert ser.fullname == 'Dalmatian'
        ser.common_name = CommonName(name='Foxglove')
        assert ser.fullname == 'Dalmatian Foxglove'


class TestCultivar:
    """Test methods of Cultivar in the seeds model."""
    @mock.patch('app.seeds.models.Cultivar.fullname',
                new_callable=mock.PropertyMock)
    def test_repr(self, m_fn):
        """Return a string formatted <Cultivar '<fullname>'>"""
        m_fn.return_value = 'Full Cultivar Name'
        cv = Cultivar()
        assert cv.__repr__() == '<Cultivar \'Full Cultivar Name\'>'

    def test_fullname_getter(self):
        """Return string with name and common_name."""
        cv = Cultivar(name='Polkadot Petra')
        cv.common_name = CommonName(name='Foxglove')
        assert cv.fullname == 'Polkadot Petra Foxglove'

    def test_queryable_dict(self):
        """Return a dict with queryable parameters for Cultivar."""
        cv = Cultivar()
        assert cv.queryable_dict == {'Cultivar Name': None,
                                     'Common Name': None,
                                     'Index': None}

    @mock.patch('app.seeds.models.Cultivar.from_queryable_values')
    def test_from_queryable_dict(self, m_fqv):
        """Call Cultivar.from_queryable_values with dict values."""
        d = {'Cultivar Name': 'Foxy',
             'Common Name': 'Foxglove',
             'Index': 'Perennial'}
        Cultivar.from_queryable_dict(d)
        m_fqv.assert_called_with(name='Foxy',
                                 common_name='Foxglove',
                                 index='Perennial')


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

    def test_to_float(self):
        """Return floats for any given integer, decimal, or fraction."""
        assert isinstance(Quantity.to_float(3.145), float)
        assert isinstance(Quantity.to_float(Decimal('2.544')), float)
        assert isinstance(Quantity.to_float('5.456'), float)
        assert isinstance(Quantity.to_float(132), float)
        assert isinstance(Quantity.to_float(Fraction(3, 4)), float)

    def test_str_to_fraction(self):
        """Return a Fraction given a valid string containing a fraction.

        If val is not parseable, raise ValueError.
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


class TestImage:
    """Test methods of Image in the seeds model."""
    def test_repr(self):
        """Return string representing Image."""
        image = Image(filename='hello.jpg')
        assert image.__repr__() == '<Image filename: \'hello.jpg\'>'

    @mock.patch('app.seeds.models.os.remove')
    def test_delete_file(self, mock_remove):
        """Delete image file using os.remove."""
        image = Image()
        image.filename = 'hello.jpg'
        image.delete_file()
        mock_remove.assert_called_with(image.full_path)

    @mock.patch('app.seeds.models.os.path.exists')
    def test_exists(self, mock_exists):
        """Call os.path.exists for path of image file."""
        mock_exists.return_value = True
        image = Image()
        image.filename = 'hello.jpg'
        assert image.exists()
        mock_exists.assert_called_with(image.full_path)

    def test_full_path(self):
        """Return the absolute file path for image name."""
        image = Image()
        image.filename = 'hello.jpg'
        assert image.full_path ==\
            os.path.join(current_app.config.get('IMAGES_FOLDER'),
                         'plants',
                         image.filename)

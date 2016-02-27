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
    Synonym,
    SynonymsMixin,
    USDInt
)


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


class TestUSDInt:
    """Test methods of the USDInt TypeDecorator in the seeds model."""
    def test_int_to_usd(self):
        """Return a Decimal USD value given an integer."""
        assert USDInt.int_to_usd(100) == Decimal('1.00')
        assert USDInt.int_to_usd(299) == Decimal('2.99')
        assert USDInt.int_to_usd(350) == Decimal('3.50')

    def test_int_to_usd_bad_type(self):
        """Raise a TypeError given non-int data."""
        with pytest.raises(TypeError):
            USDInt.int_to_usd(3.14)
        with pytest.raises(TypeError):
            USDInt.int_to_usd('400')
        with pytest.raises(TypeError):
            USDInt.int_to_usd(Decimal('100'))

    def test_int_to_usd_two_decimal_places(self):
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

    def test_usd_to_int_bad_string(self):
        """Raise a ValueError given a string that can't be parsed."""
        with pytest.raises(ValueError):
            USDInt.usd_to_int('2 99')
        with pytest.raises(ValueError):
            USDInt.usd_to_int('$ 2.99 US')
        with pytest.raises(ValueError):
            USDInt.usd_to_int('tree fiddy')

    def test_usd_to_int_bad_type(self):
        """Raise a TypeError given a value that can't be coerced to int."""
        with pytest.raises(TypeError):
            USDInt.usd_to_int(Fraction(1, 4))
        with pytest.raises(TypeError):
            USDInt.usd_to_int(['2.99', '1.99'])
        with pytest.raises(TypeError):
            USDInt.usd_to_int({'price': '$2.99'})

    def test_usd_to_int_valid_non_strings(self):
        """Return an int given a valid non-string type."""
        assert USDInt.usd_to_int(1) == 100
        assert USDInt.usd_to_int(2.99) == 299
        assert USDInt.usd_to_int(3.999) == 399
        assert USDInt.usd_to_int(Decimal('1.99')) == 199
        assert USDInt.usd_to_int(3.14159265) == 314

    def test_usd_to_int_valid_string(self):
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


class TestIndex:
    """Test methods of Index in the seeds model."""
    def test_index_getter(self):
        """Return ._name."""
        index = Index()
        index._name = 'Perennial Flower'
        assert index.name == 'Perennial Flower'

    def test_index_setter(self):
        """Set ._name and a pluralized, slugified v. to .slug."""
        index = Index()
        index.name = 'Annual Flower'
        assert index._name == 'Annual Flower'
        assert index.slug == slugify(pluralize('Annual Flower'))

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

    def test_repr(self):
        """Return string formatted <Index '<index>'>"""
        index = Index()
        index.name = 'vegetable'
        assert index.__repr__() == '<Index \'vegetable\'>'


class TestCommonName:
    """Test methods of CommonName in the seeds model."""
    def test_init_with_index(self):
        """Set self.index to passed Index."""
        idx = Index(name='Perennial')
        cn = CommonName(name='Foxglove', index=idx)
        assert cn.index is idx

    def test_init_with_index_wrong_type(self):
        """Raise a TypeError if trying to pass non-Index data via index."""
        with pytest.raises(TypeError):
            CommonName(name='Foxglove', index='Perennial')

    def test_repr(self):
        """Return string formatted <CommonName '<name>'>"""
        cn = CommonName(name='Coleus')
        assert cn.__repr__() == '<CommonName \'Coleus\'>'

    def test_header(self):
        """Return '<._name> Seeds'."""
        cn = CommonName()
        cn._name = 'Foxglove'
        assert cn.header == 'Foxglove Seeds'

    def test_name_getter(self):
        """Return contents of ._name"""
        cn = CommonName()
        cn._name = 'Coleus'
        assert cn.name == 'Coleus'

    def test_name_setter(self):
        """Set ._name and .slug using passed value."""
        cn = CommonName()
        cn.name = 'Butterfly Weed'
        assert cn._name == 'Butterfly Weed'
        assert cn.slug == slugify('Butterfly Weed')


class TestBotanicalName:
    """Test methods of BotanicalName in the seeds model."""
    def test_init_with_common_names(self):
        """Set common names for BotanicalName if passed."""
        idx = Index(name='Perennial')
        cn1 = CommonName(name='Foxglove', index=idx)
        cn2 = CommonName(name='Fauxglove', index=idx)
        bn = BotanicalName(name='Digitalis über alles',
                           common_names=[cn1, cn2])
        assert cn1 in bn.common_names
        assert cn2 in bn.common_names

    def test_init_with_common_names_wrong_type(self):
        """Raise a TypeError if common_names is not all of type CommonName."""
        idx = Index(name='Perennial')
        cn1 = CommonName(name='Foxglove', index=idx)
        cn2 = CommonName(name='Fauxglove', index=idx)
        with pytest.raises(TypeError):
            BotanicalName(name='Digitalis über alles',
                          common_names=[cn1, 'Not a CommonName', cn2])

    def test_init_with_synonyms(self):
        """Set synonyms with a string containing a list of Synonyms."""
        bn = BotanicalName(name='Digitalis purpurea',
                           synonyms='Digitalis über alles, '
                                    'Digitalis does dallas')
        assert len(bn.synonyms) == 2
        assert bn.synonyms_string == ('Digitalis über alles, '
                                      'Digitalis does dallas')

    def test_name_getter(self):
        """.name is the same as ._name."""
        bn = BotanicalName()
        bn._name = 'Asclepias incarnata'
        assert bn.name == 'Asclepias incarnata'

    def test_name_setter_valid_input(self):
        """set ._name if valid."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        assert bn._name == 'Asclepias incarnata'

    def test_name_setter_falsey_input(self):
        bn = BotanicalName()
        bn.name = ''
        assert bn._name is None
        bn.name = None
        assert bn._name is None

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


class TestSeries:
    """Test methods of the Series class in seeds.models."""
    def test_init_with_common_name(self):
        """Create a Series with a CommonName."""
        cn = CommonName(name='Foxglove')
        sr = Series(name='Polkadot', common_name=cn)
        assert sr.common_name is cn

    def test_init_with_common_name_wrong_type(self):
        """Raise a TypeError if common_name is passed non-CommonName data."""
        with pytest.raises(TypeError):
            Series(name='Polkadot', common_name='Foxglove')

    def test_init_with_default_position(self):
        """Set position to Series.BEFORE_CULTIVAR if no series passed."""
        sr = Series(name='Polkadot')
        assert sr.position == Series.BEFORE_CULTIVAR

    def test_init_with_position_before(self):
        """Set position to Series.BEFORE_CULTIVAR if it is passed."""
        sr = Series(name='Polkadot', position=Series.BEFORE_CULTIVAR)
        assert sr.position == Series.BEFORE_CULTIVAR

    def test_init_with_position_after(self):
        """Set position to Series.AFTER_CULTIVAR if it is passed."""
        sr = Series(name='Polkadot', position=Series.AFTER_CULTIVAR)
        assert sr.position == Series.AFTER_CULTIVAR

    def test_repr(self):
        """Return formatted string with full name."""
        sr = Series(name='Polkadot', common_name=CommonName(name='Foxglove'))
        assert sr.__repr__() == '<Series \'Polkadot Foxglove\'>'

    def test_fullname(self):
        """Returns name of series along with common name."""
        ser = Series()
        assert ser.fullname is None
        ser.name = 'Dalmatian'
        assert ser.fullname == 'Dalmatian'
        ser.common_name = CommonName(name='Foxglove')
        assert ser.fullname == 'Dalmatian Foxglove'


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
                         image.filename)


class TestCultivar:
    """Test methods of Cultivar in the seeds model."""
    def test_repr(self):
        """Return a string formatted <Cultivar '<name>'>"""
        cultivar = Cultivar()
        cultivar.name = 'Soulmate'
        assert cultivar.__repr__() == '<Cultivar \'Soulmate\'>'

    def test_fullname_getter(self):
        """.fullname returns ._name, or a string with name and common name."""
        cn = CommonName()
        cultivar = Cultivar()
        cn._name = 'Foxglove'
        cultivar._name = 'Foxy'
        assert cultivar.fullname == 'Foxy'
        cultivar.common_name = cn
        assert cultivar.fullname == 'Foxy Foxglove'

    def test_name_getter(self):
        """Return ._name"""
        cultivar = Cultivar()
        cultivar._name = 'Foxy'
        assert cultivar.name == 'Foxy'

    def test_name_setter(self):
        """Set ._name and a slugified version of name to .slug"""
        cultivar = Cultivar()
        cultivar.name = u'Cafe Crème'
        assert cultivar._name == u'Cafe Crème'
        assert cultivar.slug == slugify(u'Cafe Crème')

    def test_name_setter_none(self):
        """Set ._name and slug to None if .name set to None."""
        cultivar = Cultivar()
        cultivar.name = None
        assert cultivar._name is None
        assert cultivar.slug is None

    def test_lookup_dict(self):
        """Generate a dict containing information used to look up."""
        cv1 = Cultivar(name='Name Only')
        cv2 = Cultivar(name='Name & Common Name')
        cv3 = Cultivar(name='Name, Series, and Common Name')
        cn = CommonName(name='Common Name')
        cn.index = Index(name='Index')
        sr = Series(name='Series')
        cv2.common_name = cn
        cv3.common_name = cn
        cv3.series = sr
        assert cv1.lookup_dict() == {'Cultivar Name': 'Name Only',
                                     'Common Name': None,
                                     'Index': None,
                                     'Series': None}
        assert cv2.lookup_dict() == {'Cultivar Name': 'Name & Common Name',
                                     'Common Name': 'Common Name',
                                     'Index': 'Index',
                                     'Series': None}
        assert cv3.lookup_dict() == {
            'Cultivar Name': 'Name, Series, and Common Name',
            'Common Name': 'Common Name',
            'Index': 'Index',
            'Series': 'Series'
        }


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

    def test_init_with_no_args(self):
        """Create a Packet object with no data given  no args."""
        pkt = Packet()
        assert not pkt.sku
        assert not pkt.price
        assert not pkt.quantity

    def test_init_with_no_quantity(self):
        """Create a Packet with no quantity set given only sku and price."""
        pkt = Packet(sku='8675309', price=Decimal('3.50'))
        assert pkt.sku == '8675309'
        assert pkt.price == Decimal('3.50')
        assert not pkt.quantity

    def test_init_quantity_or_units(self):
        """Raise a ValueError if only one of quantity or units passed."""
        with pytest.raises(ValueError):
            Packet(sku='8675309', price=Decimal('3.50'), quantity=100)
        with pytest.raises(ValueError):
            Packet(sku='8675309', price=Decimal('3.50'), units='seeds')


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
        """Return floats for any given integer, decimal, or fraction."""
        assert isinstance(Quantity.for_cmp(3.145), float)
        assert isinstance(Quantity.for_cmp(Decimal('2.544')), float)
        assert isinstance(Quantity.for_cmp('5.456'), float)
        assert isinstance(Quantity.for_cmp(132), float)
        assert isinstance(Quantity.for_cmp(Fraction(3, 4)), float)

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

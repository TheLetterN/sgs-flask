import unittest
from decimal import Decimal
from fractions import Fraction
from slugify import slugify
from app import create_app
from app.seeds.models import BotanicalName, Category, CommonName, is_480th, \
    is_decimal, is_fraction, is_int, Packet, Price, QtyDecimal, QtyFraction, \
    QtyInteger, Quantity480th, QuantityDecimal, Seed, Unit, USDInt


class TestModuleFunctions(unittest.TestCase):
    """Class to test top-level functions in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_is_480th_bad_fraction_verify_fraction_off(self):
        """Carry on if given a bad fraction with verify_fraction off.

        There should never be a case where we actually want to accept a bad
        fraction, this is just to test that it runs without checking
        is_fraction() if verify_fraction = False. Realistically is_480th
        should never be run on a value that hasn't been verified by
        is_fraction(), there's just no sense in running is_fraction() again
        if we need to run is_480th() in a block that only runs after
        is_fraction() has evaluated to True.
        """
        self.assertTrue(is_480th('1 and 1/4', verify_fraction=False))
        self.assertTrue(is_480th('1/2/4', verify_fraction=False))

    def test_is_480th_bad_fraction_verify_fraction_on(self):
        """Return False if verify_fraction is on when given bad fraction."""
        self.assertFalse(is_480th('1 and 1/4'))
        self.assertFalse(is_480th('1/2/4'))

    def test_is_480th_bad_fraction(self):
        """Return False if given a Fraction with an invalid denominator."""
        self.assertFalse(is_480th(Fraction(6, 7)))
        self.assertFalse(is_480th(Fraction(8, 9)))
        self.assertFalse(is_480th(Fraction(10, 11)))
        self.assertFalse(is_480th(Fraction(12, 13)))
        self.assertFalse(is_480th(Fraction(13, 14)))

    def test_is_480th_bad_str(self):
        """Return False if str contains fraction w/ invalid denom."""
        self.assertFalse(is_480th('6/7'))
        self.assertFalse(is_480th('1 3/9'))
        self.assertFalse(is_480th('9/11'))
        self.assertFalse(is_480th('4/13'))
        self.assertFalse(is_480th('81/14'))

    def test_is_480th_bad_type(self):
        """Return False if given data that is not a Fraction or str."""
        self.assertFalse(is_480th(3.10, verify_fraction=False))
        self.assertFalse(is_480th(Decimal('1.25'), verify_fraction=False))
        self.assertFalse(is_480th(42, verify_fraction=False))

    def test_is_480th_valid_fraction(self):
        """Return True if given a Fraction with a valid denominator."""
        self.assertTrue(is_480th(Fraction(1, 2)))
        self.assertTrue(is_480th(Fraction(2, 3)))
        self.assertTrue(is_480th(Fraction(3, 4)))
        self.assertTrue(is_480th(Fraction(5, 6)))
        self.assertTrue(is_480th(Fraction(7, 8)))
        self.assertTrue(is_480th(Fraction(9, 10)))
        self.assertTrue(is_480th(Fraction(11, 12)))
        self.assertTrue(is_480th(Fraction(14, 15)))
        self.assertTrue(is_480th(Fraction(15, 16)))

    def test_is_480th_valid_str(self):
        """Return True if given a str containing fraction w/ valid denom."""
        self.assertTrue(is_480th('1/2'))
        self.assertTrue(is_480th('1 1/3'))
        self.assertTrue(is_480th('1/4'))
        self.assertTrue(is_480th('43 1/6'))
        self.assertTrue(is_480th('1/8'))
        self.assertTrue(is_480th('41/12'))
        self.assertTrue(is_480th('2/15'))
        self.assertTrue(is_480th('1 3/16'))

    def test_is_decimal_bad_str(self):
        """Return false if string contains invalid data."""
        self.assertFalse(is_decimal('$2.99'))
        self.assertFalse(is_decimal('43.44usd'))
        self.assertFalse(is_decimal('3.4.5'))
        self.assertFalse(is_decimal('3. 4'))
        self.assertFalse(is_decimal('3 .4'))
        self.assertFalse(is_decimal('1'))
        self.assertFalse(is_decimal('1/3'))
        self.assertFalse(is_decimal('1 2/3'))

    def test_is_decimal_bad_type(self):
        """Return false if type is not float, Decimal, or str."""
        self.assertFalse(is_decimal(12))
        self.assertFalse(is_decimal(Fraction(3, 4)))
        self.assertFalse(is_decimal([3.4, 4.5]))

    def test_is_decimal_decimal_or_float(self):
        """Return True given a Decimal or float type."""
        self.assertTrue(is_decimal(3.14))
        self.assertTrue(is_decimal(Decimal('3.14')))

    def test_is_decimal_str_valid(self):
        """Return True if string contains a valid decimal number."""
        self.assertTrue(is_decimal('3.14'))
        self.assertTrue(is_decimal(' 42.24 '))

    def test_is_fraction_bad_str(self):
        """Return False if string is not a valid fraction."""
        self.assertFalse(is_fraction('1 a2/4'))
        self.assertFalse(is_fraction('1 3/g44'))
        self.assertFalse(is_fraction('a 1/2'))
        self.assertFalse(is_fraction('1 1 3/2'))
        self.assertFalse(is_fraction('x/3'))
        self.assertFalse(is_fraction('2/y'))
        self.assertFalse(is_fraction('1/2/3'))
        self.assertFalse(is_fraction('12'))
        self.assertFalse(is_fraction('3.14'))

    def test_is_fraction_bad_type(self):
        """Return False if given data of a type other than str or Fraction."""
        self.assertFalse(is_fraction(12))
        self.assertFalse(is_fraction(3.14))
        self.assertFalse(is_fraction(['4/3', '1/2']))

    def test_is_fraction_fraction(self):
        """Return True given a Fraction object."""
        self.assertTrue(is_fraction(Fraction(1, 3)))
        self.assertTrue(is_fraction(Fraction(5, 2)))
        self.assertTrue(is_fraction(Fraction(12, 131)))

    def test_is_fraction_str_fraction(self):
        """Return True if given a string containing a valid fraction."""
        self.assertTrue(is_fraction('1/2'))
        self.assertTrue(is_fraction('3/4'))
        self.assertTrue(is_fraction('234/113'))

    def test_is_fraction_str_mixed(self):
        """Return True if given a string containing a valid mixed number."""
        self.assertTrue(is_fraction('1 1/2'))
        self.assertTrue(is_fraction('2 3/4'))
        self.assertTrue(is_fraction('243 5/44'))

    def test_is_fraction_zero_denominator(self):
        """Return False if string contains fraction with denom of 0."""
        self.assertFalse(is_fraction('1/0'))
        self.assertFalse(is_fraction('1 3/0'))
        self.assertFalse(is_fraction('43434/0'))

    def test_is_int_bad_str(self):
        """Return False if str does not contain a valid int."""
        self.assertFalse(is_int('1/3'))
        self.assertFalse(is_int('1 1/4'))
        self.assertFalse(is_int('3.14'))
        self.assertFalse(is_int('1a'))

    def test_is_int_bad_type(self):
        """Return False if given a type that isn't int or str."""
        self.assertFalse(is_int(3.14))
        self.assertFalse(is_int(Decimal('3.14')))
        self.assertFalse(is_int(Fraction(3, 4)))

    def test_is_int_int(self):
        """Return True if value is of type int."""
        self.assertTrue(is_int(12))
        self.assertTrue(is_int(42))

    def test_is_int_str_valid(self):
        """Return true if value is a str containing a valid int."""
        self.assertTrue(is_int('12'))
        self.assertTrue(is_int(' 42 '))


class TestQuantity480th(unittest.TestCase):
    """Test methods of the Quantity480th TypeDecorator in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_from_480ths_valid_ints(self):
        """Return a Fraction given a valid int."""
        self.assertEqual(Quantity480th.from_480ths(240), Fraction(1, 2))
        self.assertEqual(Quantity480th.from_480ths(400), Fraction(5, 6))
        self.assertEqual(Quantity480th.from_480ths(6180), Fraction(103, 8))

    def test_from_480ths_bad_type(self):
        """Raise a TypeError given non-int data."""
        with self.assertRaises(TypeError):
            Quantity480th.from_480ths(3.14)
        with self.assertRaises(TypeError):
            Quantity480th.from_480ths(Decimal('1000.0'))
        with self.assertRaises(TypeError):
            Quantity480th.from_480ths('240')
        with self.assertRaises(TypeError):
            Quantity480th.from_480ths(Fraction(1, 4))

    def test_process_bind_param(self):
        """Return result of .to_480ths() for value, None if no value."""
        qty = Quantity480th()
        self.assertEqual(qty.process_bind_param('1/2', None), 240)
        self.assertIs(qty.process_bind_param(None, None), None)

    def test_process_result_value(self):
        """Return result of .from_480ths() for value, None if no value."""
        qty = Quantity480th()
        self.assertEqual(qty.process_result_value(240, None), Fraction(1, 2))
        self.assertIs(qty.process_result_value(None, None), None)

    def test_to_480ths_bad_denominator(self):
        """Raise a ValueError if 480 not divisible by denominator."""
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/7')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/9')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/11')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/13')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/14')

    def test_to_480ths_bad_type(self):
        """Raise a TypeError if given data that is not a str or Fraction."""
        with self.assertRaises(TypeError):
            Quantity480th.to_480ths([1, 3])
        with self.assertRaises(TypeError):
            Quantity480th.to_480ths((1, 4))
        with self.assertRaises(TypeError):
            Quantity480th.to_480ths({'numerator': 1, 'denominator': 4})

    def test_to_480ths_string_bad_format(self):
        """Raise a ValueError if string can't be parsed."""
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/2 1')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('one fourth')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1 1//2')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/2/3')
        with self.assertRaises(ValueError):
            Quantity480th.to_480ths('1/n')

    def test_to_480ths_string_fraction(self):
        """Return an int given a string containing a valid fraction."""
        self.assertEqual(Quantity480th.to_480ths('1/2'), 240)
        self.assertEqual(Quantity480th.to_480ths('5/6'), 400)
        self.assertEqual(Quantity480th.to_480ths('15/16'), 450)

    def test_to_480ths_string_with_space(self):
        """Return an int given a valid mixed number in a string."""
        self.assertEqual(Quantity480th.to_480ths('1 1/2'), 720)
        self.assertEqual(Quantity480th.to_480ths('12 7/8'), 6180)

    def test_to_480ths_valid_fractions(self):
        """Return an int given a valid Fraction."""
        self.assertEqual(Quantity480th.to_480ths(Fraction(1, 2)), 240)
        self.assertEqual(Quantity480th.to_480ths(Fraction(2, 3)), 320)
        self.assertEqual(Quantity480th.to_480ths(Fraction(3, 4)), 360)
        self.assertEqual(Quantity480th.to_480ths(Fraction(4, 5)), 384)
        self.assertEqual(Quantity480th.to_480ths(Fraction(5, 6)), 400)
        self.assertEqual(Quantity480th.to_480ths(Fraction(7, 8)), 420)
        self.assertEqual(Quantity480th.to_480ths(Fraction(9, 10)), 432)
        self.assertEqual(Quantity480th.to_480ths(Fraction(11, 12)), 440)
        self.assertEqual(Quantity480th.to_480ths(Fraction(14, 15)), 448)
        self.assertEqual(Quantity480th.to_480ths(Fraction(15, 16)), 450)
        self.assertEqual(Quantity480th.to_480ths(Fraction(3, 2)), 720)
        self.assertEqual(Quantity480th.to_480ths(Fraction(103, 8)), 6180)


class TestQuantityDecimal(unittest.TestCase):
    """Test methods of the QuantityDecimal TypeDecorator in seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_decimal_to_int_invalid_data(self):
        """Raise a ValueError given data that can't be coerced to Decimal."""
        with self.assertRaises(ValueError):
            QuantityDecimal.decimal_to_int('4.3.32')
        with self.assertRaises(ValueError):
            QuantityDecimal.decimal_to_int('$4.32')
        with self.assertRaises(ValueError):
            QuantityDecimal.decimal_to_int('4.4a')
        with self.assertRaises(ValueError):
            QuantityDecimal.decimal_to_int(['4.2', '4.4'])
        with self.assertRaises(ValueError):
            QuantityDecimal.decimal_to_int({'quantity': '42.4'})

    def test_decimal_to_int_valid_decimals(self):
        """Return an int given data that is or can be converted to Decimal."""
        self.assertEqual(QuantityDecimal.decimal_to_int(Decimal('1.4')), 14000)
        self.assertEqual(QuantityDecimal.decimal_to_int('3.14159'), 31415)
        self.assertEqual(QuantityDecimal.decimal_to_int(234.1), 2341000)

    def test_int_to_decimal_not_int(self):
        """Raise a TypeError given non-int data."""
        with self.assertRaises(TypeError):
            QuantityDecimal.int_to_decimal('14000')
        with self.assertRaises(TypeError):
            QuantityDecimal.int_to_decimal(400.243)
        with self.assertRaises(TypeError):
            QuantityDecimal.int_to_decimal(Decimal('10000'))

    def test_int_to_decimal_valid_ints(self):
        """Return a Decimal the db int represented."""
        self.assertEqual(QuantityDecimal.int_to_decimal(3), Decimal('0.0003'))
        self.assertEqual(QuantityDecimal.int_to_decimal(14000), Decimal('1.4'))
        self.assertEqual(QuantityDecimal.int_to_decimal(31415),
                         Decimal('3.1415'))

    def test_process_bind_param(self):
        """Return result of .decimal_to_int() for value, None if None."""
        qty = QuantityDecimal()
        self.assertEqual(qty.process_bind_param(Decimal('1.4'), None), 14000)
        self.assertIs(qty.process_bind_param(None, None), None)

    def test_process_result_value(self):
        """Return result of .int_to_decimal() for value, None if None."""
        qty = QuantityDecimal()
        self.assertEqual(qty.process_result_value(14000, None), Decimal('1.4'))
        self.assertIs(qty.process_result_value(None, None), None)


class TestUSDInt(unittest.TestCase):
    """Test methods of the USDInt TypeDecorator in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_int_to_usd(self):
        """Return a Decimal USD value given an integer."""
        self.assertEqual(USDInt.int_to_usd(100), Decimal('1.00'))
        self.assertEqual(USDInt.int_to_usd(299), Decimal('2.99'))
        self.assertEqual(USDInt.int_to_usd(350), Decimal('3.50'))

    def test_int_to_usd_bad_type(self):
        """Raise a TypeError given non-int data."""
        with self.assertRaises(TypeError):
            USDInt.int_to_usd(3.14)
        with self.assertRaises(TypeError):
            USDInt.int_to_usd('400')
        with self.assertRaises(TypeError):
            USDInt.int_to_usd(Decimal('100'))

    def test_int_to_usd_two_decimal_places(self):
        """Always return a Decimal with 2 decimal places."""
        self.assertEqual(str(USDInt.int_to_usd(100)), '1.00')
        self.assertEqual(str(USDInt.int_to_usd(350)), '3.50')
        self.assertEqual(str(USDInt.int_to_usd(1000)), '10.00')

    def test_usd_to_int_bad_string(self):
        """Raise a ValueError given a string that can't be parsed."""
        with self.assertRaises(ValueError):
            USDInt.usd_to_int('2 99')
        with self.assertRaises(ValueError):
            USDInt.usd_to_int('$ 2.99 US')
        with self.assertRaises(ValueError):
            USDInt.usd_to_int('tree fiddy')

    def test_usd_to_int_bad_type(self):
        """Raise a TypeError given a value that can't be coerced to int."""
        with self.assertRaises(TypeError):
            USDInt.usd_to_int(Fraction(1, 4))
        with self.assertRaises(TypeError):
            USDInt.usd_to_int(['2.99', '1.99'])
        with self.assertRaises(TypeError):
            USDInt.usd_to_int({'price': '$2.99'})

    def test_usd_to_int_valid_non_strings(self):
        """Return an int given a valid non-string type."""
        self.assertEqual(USDInt.usd_to_int(1), 100)
        self.assertEqual(USDInt.usd_to_int(2.99), 299)
        self.assertEqual(USDInt.usd_to_int(3.999), 399)
        self.assertEqual(USDInt.usd_to_int(Decimal('1.99')), 199)
        self.assertEqual(USDInt.usd_to_int(3.14159265), 314)

    def test_usd_to_int_valid_string(self):
        """Return an int given a valid string containing a dollar amount."""
        self.assertEqual(USDInt.usd_to_int('$2.99'), 299)
        self.assertEqual(USDInt.usd_to_int('3.00'), 300)
        self.assertEqual(USDInt.usd_to_int('2.50$'), 250)
        self.assertEqual(USDInt.usd_to_int('$ 1.99'), 199)
        self.assertEqual(USDInt.usd_to_int('4.99 $'), 499)
        self.assertEqual(USDInt.usd_to_int(' 3.50 '), 350)
        self.assertEqual(USDInt.usd_to_int('4'), 400)
        self.assertEqual(USDInt.usd_to_int('5.3'), 530)
        self.assertEqual(USDInt.usd_to_int('3.9999'), 399)


class TestBotanicalName(unittest.TestCase):
    """Test methods of BotanicalName in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_name_getter(self):
        """.name is the same as ._name."""
        bn = BotanicalName()
        bn._name = 'Asclepias incarnata'
        self.assertEqual(bn.name, 'Asclepias incarnata')

    def test_name_setter_valid_input(self):
        """set ._name if valid."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        self.assertEqual(bn._name, 'Asclepias incarnata')

    def test_init_invalid_botanical_name(self):
        with self.assertRaises(ValueError):
            BotanicalName(name='Richard M. Nixon')

    def test_init_valid_botanical_name(self):
        """Sets the BotanicalName.botanical_name to given value."""
        bn = BotanicalName(name='Asclepias incarnata')
        self.assertEqual(bn.name, 'Asclepias incarnata')

    def test_repr(self):
        """Return a string in format <BotanicalName '<botanical_name>'>"""
        bn = BotanicalName(name='Asclepias incarnata')
        self.assertEqual('<BotanicalName \'Asclepias incarnata\'>',
                         bn.__repr__())

    def test_validate_more_than_two_words(self):
        """A botanical name is still valid with more than 2 words."""
        self.assertTrue(BotanicalName.validate('Brassica oleracea Var.'))

    def test_validate_not_a_string(self):
        """Return False when given non-string data."""
        self.assertFalse(BotanicalName.validate(42))
        self.assertFalse(BotanicalName.validate(('foo', 'bar')))
        self.assertFalse(BotanicalName.validate(dict(foo='bar')))

    def test_validate_upper_in_wrong_place(self):
        """The only uppercase letter should be the first."""
        self.assertFalse(BotanicalName.validate('AscLepias incarnata'))
        self.assertFalse(BotanicalName.validate('Asclepias Incarnata'))
        self.assertFalse(BotanicalName.validate('Asclepias incarNata'))

    def test_validate_starts_with_lower(self):
        """The first letter of a botanical name should be uppercase."""
        self.assertFalse(BotanicalName.validate('asclepias incarnata'))

    def test_validate_valid_binomen(self):
        """Returns true if botanical_name contains a valid binomen."""
        self.assertTrue(BotanicalName.validate('Asclepias incarnata'))
        self.assertTrue(BotanicalName.validate('Helianthus anuus'))


class TestCategory(unittest.TestCase):
    """Test methods of Category in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_category_getter(self):
        """Return ._category."""
        category = Category()
        category._category = 'Perennial Flower'
        self.assertEqual(category.category, 'Perennial Flower')

    def test_category_setter(self):
        """Set ._category and .slug."""
        category = Category()
        category.category = 'Annual Flower'
        self.assertEqual(category._category, 'Annual Flower')
        self.assertEqual(category.slug, slugify('Annual Flower'))

    def test_repr(self):
        """Return string formatted <Category '<category>'>"""
        category = Category()
        category.category = 'vegetable'
        self.assertEqual(category.__repr__(), '<Category \'vegetable\'>')


class TestCommonName(unittest.TestCase):
    """Test methods of CommonName in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return string formatted <CommonName '<name>'>"""
        cn = CommonName(name='Coleus')
        self.assertEqual(cn.__repr__(), '<CommonName \'Coleus\'>')

    def test_name_getter(self):
        """Return contents of ._name"""
        cn = CommonName()
        cn._name = 'Coleus'
        self.assertEqual(cn.name, 'Coleus')

    def test_name_setter(self):
        """Set ._name and .slug using passed value."""
        cn = CommonName()
        cn.name = 'Butterfly Weed'
        self.assertEqual(cn._name, 'Butterfly Weed')
        self.assertEqual(cn.slug, slugify('Butterfly Weed'))


class TestPacket(unittest.TestCase):
    """Test methods of Packet in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_price_getter(self):
        """Return ._price."""
        pkt = Packet()
        pkt._price = Price(price=Decimal('2.99'))
        self.assertEqual(pkt.price, Decimal('2.99'))

    def test_quantity_equals_not_480th(self):
        """Raise a ValueError given a denominator 480 isn't divisible by."""
        pkt = Packet()
        with self.assertRaises(ValueError):
            pkt.quantity_equals(Fraction(1, 7))
        with self.assertRaises(ValueError):
            pkt.quantity_equals('3/11')

    def test_quantity_getter_too_many_qty(self):
        """Raise a RuntimeError if more than one ._qty_x set."""
        pkt = Packet()
        pkt._qty_decimal = QtyDecimal(Decimal('3.14'))
        self.assertEqual(pkt.quantity, Decimal('3.14'))
        pkt._qty_fraction = QtyFraction(Fraction(1, 2))
        with self.assertRaises(RuntimeError):
            pkt.quantity
        pkt._qty_integer = QtyInteger(100)
        with self.assertRaises(RuntimeError):
            pkt.quantity
        pkt._qty_decimal = None
        with self.assertRaises(RuntimeError):
            pkt.quantity
        pkt._qty_fraction = None
        self.assertEqual(pkt.quantity, 100)

    def test_quantity_setter_bad_data(self):
        """Raise a ValueError if data could not be determined to be valid."""
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = '$2.99'
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = 'tree fiddy'
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = [1, 2, 3, 4]

    def test_quantity_setter_fraction_not_480th(self):
        """Raise a ValueError if 480 is not divisible by denominator."""
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(3, 7)
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(5, 9)
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(9, 11)
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(10, 13)
        with self.assertRaises(ValueError):
            pkt = Packet()
            pkt.quantity = Fraction(11, 14)


class TestQtyDecimal(unittest.TestCase):
    """Test methods of QtyDecimal in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return a string formatted <QtyDecimal '<value>'>."""
        qty = QtyDecimal(3.1415)
        self.assertEqual(qty.__repr__(), '<QtyDecimal \'3.1415\'>')


class TestQtyFraction(unittest.TestCase):
    """Test methods of QtyFraction in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return a string formatted <QtyFraction '<value>'>."""
        qty = QtyFraction('3/4')
        self.assertEqual(qty.__repr__(), '<QtyFraction \'3/4\'>')


class TestQtyInteger(unittest.TestCase):
    """Test methods of QtyInteger in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return a string formatted <QtyInteger '<value>'>."""
        qty = QtyInteger('100')
        self.assertEqual(qty.__repr__(), '<QtyInteger \'100\'>')


class TestSeed(unittest.TestCase):
    """Test methods of Seed in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

#    def test_add_botanical_name_already_in_botanical_name(self):
#        """Use the same instance as _botanical_name if name is the same."""
#        seed = Seed()
#        seed._botanical_name = BotanicalName(name='Asclepias incarnata')
#        seed.add_botanical_name('Asclepias incarnata')
#        self.assertIs(seed._botanical_name, seed._botanical_names[0])
#
#    def test_add_botanical_name_already_in_botanical_names(self):
#        """If botanical_names has not been comitted, don't add duplicates."""
#        seed = Seed()
#        seed._botanical_names.append(BotanicalName('Asclepias incarnata'))
#        self.assertEqual(len(seed._botanical_names), 1)
#        seed.add_botanical_name('Asclepias incarnata')
#        self.assertEqual(len(seed._botanical_names), 1)
#        seed._botanical_names.append(BotanicalName('Echinacea purpurea'))
#        self.assertEqual(len(seed._botanical_names), 2)
#        seed.add_botanical_name('Echinacea purpurea')
#        self.assertEqual(len(seed._botanical_names), 2)
#
#    def test_add_category_bad_type(self):
#        """Raise a TypeError if category is not a string."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.add_category(42)
#        with self.assertRaises(TypeError):
#            seed.add_category(['Herb', 'Vegetable'])
#
#    def test_add_category_already_in_categories(self):
#        """Do not add a category already in categories."""
#        seed = Seed()
#        seed._categories.append(Category(category='Vegetable'))
#        seed._categories.append(Category(category='Herb'))
#        self.assertEqual(len(seed._categories), 2)
#        seed.add_category('Herb')
#        self.assertEqual(len(seed._categories), 2)
#
#    def test_add_category_already_in_category(self):
#        """Set to same instance as ._category if the same category."""
#        seed = Seed()
#        seed._category = Category(category='Vegetable')
#        seed.add_category('Vegetable')
#        self.assertIs(seed._category, seed._categories[0])
#
#    def test_add_common_name_already_in_common_name(self):
#        """Set to same instance as ._common_name if the same name."""
#        seed = Seed()
#        seed._common_name = CommonName(name='Coleus')
#        seed.add_common_name('Coleus')
#        self.assertIs(seed._common_name, seed._common_names[0])
#
#    def test_add_common_name_already_in_common_names(self):
#        """Don't add a common name if it's already in ._common_names."""
#        seed = Seed()
#        seed._common_names.append(CommonName('Coleus'))
#        self.assertEqual(len(seed._common_names), 1)
#        seed.add_common_name('Coleus')
#        self.assertEqual(len(seed._common_names), 1)
#        seed._common_names.append(CommonName('Tomato'))
#        self.assertEqual(len(seed._common_names), 2)
#        seed.add_common_name('Tomato')
#        self.assertEqual(len(seed._common_names), 2)
#
#    def test_add_common_name_bad_type(self):
#        """Raise a TypeError given non-string data."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.add_common_name(42)
#        with self.assertRaises(TypeError):
#            seed.add_common_name(['Coleus', 'Tomato'])
#
#    def test_botanical_name_getter(self):
#        """Return a string containing the botanical name for the seed."""
#        seed = Seed()
#        seed._botanical_name = BotanicalName('Asclepias incarnata')
#        self.assertEqual(seed.botanical_name, 'Asclepias incarnata')
#
#    def test_botanical_name_setter_bad_type(self):
#        """Raise a TypeError given non-string data."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.botanical_name = 42
#        with self.assertRaises(TypeError):
#            seed.botanical_name = ['Asclepias incarnata', 'Echinacea purpurea']
#
#    def test_botanical_names_getter(self):
#        """Returns a list of strings from BotanicalName.botanical_name."""
#        seed = Seed()
#        seed._botanical_names.append(BotanicalName('Asclepias incarnata'))
#        seed._botanical_names.append(BotanicalName('Echinacea purpurea'))
#        seed._botanical_names.append(BotanicalName('Canis lupus'))
#        self.assertEqual(seed.botanical_names.sort(),
#                         ['Asclepias incarnata',
#                          'Echinacea purpurea',
#                          'Canis lupus'].sort())
#
#    def test_botanical_names_setter_bad_type(self):
#        """Raise a TypeError given data that is not a string or an iterable.
#
#        If it is an iterable, it must contain only strings.
#        """
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.botanical_names = 42
#        with self.assertRaises(TypeError):
#            seed.botanical_names = ('Asclepias incarnata', 42)
#
#    def test_categories_getter(self):
#        """Return a list of ._categories.category strings."""
#        seed = Seed()
#        seed._categories.append(Category('Annual Flower'))
#        seed._categories.append(Category('Vegetable'))
#        seed._categories.append(Category('Herb'))
#        self.assertEqual(seed.categories.sort(),
#                         ['Annual Flower', 'Vegetable', 'Herb'].sort())
#
#    def test_categories_setter_bad_type(self):
#        """Raise a TypeError if given data that is not a string or iterable.
#
#        If it is an iterable, it must contain only strings.
#        """
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.categories = 42
#        with self.assertRaises(TypeError):
#            seed.categories = ['Herb', 42]
#
#    def test_category_getter(self):
#        """Return ._category.category."""
#        seed = Seed()
#        seed._category = Category(category='Annual Flower')
#        self.assertEqual(seed.category, 'Annual Flower')
#
#    def test_category_setter_bad_type(self):
#        """Raise a TypeError given non-string data."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.category = 42
#        with self.assertRaises(TypeError):
#            seed.category = ['Herb', 'Perennial Flower']
#
#    def test_common_name_getter(self):
#        """Return ._common_name.name."""
#        seed = Seed()
#        seed._common_name = CommonName(name='Coleus')
#        self.assertEqual(seed.common_name, 'Coleus')
#
#    def test_common_name_setter_bad_type(self):
#        """Raise a TypeError given non-string data."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.common_name = 42
#        with self.assertRaises(TypeError):
#            seed.common_name = ['Tomato', 'Coleus']
#        with self.assertRaises(TypeError):
#            seed.common_name = CommonName('Coleus')
#
#    def test_common_names_setter_iterable_containing_non_strings(self):
#        """Raise a TypeError if iterable contains any non-string data."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.common_names = ['Coleus', 'Tomato', 42]
#        with self.assertRaises(TypeError):
#            seed.common_names = ('Coleus', 'Tomato', 41)

    def test_repr(self):
        """Return a string formatted <Seed '<name>'>"""
        seed = Seed()
        seed.name = 'Soulmate'
        self.assertEqual(seed.__repr__(), '<Seed \'Soulmate\'>')

#    def test_common_names_setter_not_iterable_or_string(self):
#        """Raise a TypeError given data that is not str or iterable."""
#        seed = Seed()
#        with self.assertRaises(TypeError):
#            seed.common_names = 42
#        with self.assertRaises(TypeError):
#            seed.common_names = CommonName('Coleus')


class TestUnit(unittest.TestCase):
    """Test methods of Unit in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return a string formatted <Unit '<unit>'>"""
        ut = Unit()
        ut.unit = 'frogs'
        self.assertEqual(ut.__repr__(), '<Unit \'frogs\'>')


if __name__ == '__main__':
    unittest.main()

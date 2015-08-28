import unittest
from app import create_app
from app.seeds.models import BotanicalName, Category, CommonName, Packet, \
    Seed, UnitType


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


class TestPacket(unittest.TestCase):
    """Test methods of Packet in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_price_getter_and_setter(self):
        """The setter stores price as an int, getter returns a str."""
        pkt = Packet()
        pkt.price = '2.99'
        self.assertEqual(pkt._price, 299)
        self.assertEqual(pkt.price, '2.99')

    def test_price_int_from_str_bad_string_with_dot(self):
        """Raise a ValueError if given data is not decimal number."""
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('$4.99')
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('4.99USD')

    def test_price_int_from_str_correctly_formats_data(self):
        """Convert numbers to integers w fractional parts as lowest digits."""
        self.assertEqual(Packet.price_int_from_str('2.99'), 299)
        self.assertEqual(Packet.price_int_from_str('4.5'), 450)
        self.assertEqual(Packet.price_int_from_str('42'), 4200)

    def test_price_int_from_str_not_a_number(self):
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('a brazilian dollars')

    def test_price_int_from_str_not_a_string(self):
        """Raise a TypeError if given data not of the string type."""
        with self.assertRaises(TypeError):
            Packet.price_int_from_str(4.99)
        with self.assertRaises(TypeError):
            Packet.price_int_from_str(5)

    def test_price_int_from_str_too_many_decimal_places(self):
        """Raise a ValueError if more than 2 digits exist to right of dot."""
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('4.225')
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('342.5555')

    def test_price_int_from_str_too_many_dots(self):
        """Raise a ValueError if there are too many dots in price."""
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('4.3.2')
        with self.assertRaises(ValueError):
            Packet.price_int_from_str('127.0.0.1')

    def test_price_str_from_int_returns_decimal_string(self):
        """Convert an int price to a string containing a decimal."""
        self.assertEqual(Packet.price_str_from_int(299), '2.99')
        self.assertEqual(Packet.price_str_from_int(450), '4.50')
        self.assertEqual(Packet.price_str_from_int(4200), '42.00')

    def test_quantity_getter(self):
        """Gets _quantity and returns it in readable format."""
        packet = Packet()
        packet._quantity = -141
        self.assertEqual(packet.quantity, '1/4')
        packet2 = Packet()
        packet2._quantity = -531
        self.assertEqual(packet2.quantity, '1 2/3')
        packet3 = Packet()
        packet3._quantity = 12342
        self.assertEqual(packet3.quantity, '12.34')
        packet4 = Packet()
        packet4._quantity = 12340
        self.assertEqual(packet4.quantity, '1234')

    def test_quantity_setter(self):
        """Sets _quantity from a string format quantity translated to int."""
        packet = Packet()
        packet.quantity = '1/4'
        self.assertEqual(packet._quantity, -141)
        packet2 = Packet()
        packet2.quantity = '5/3'
        self.assertEqual(packet2._quantity, -531)
        packet3 = Packet()
        packet3.quantity = '12.34'
        self.assertEqual(packet3._quantity, 12342)
        packet4 = Packet()
        packet4.quantity = '1234'
        self.assertEqual(packet4._quantity, 12340)

    def test_quantity_int_from_str_decimal_contains_invalid_chars(self):
        """Raise a valueError if non-numeric characters are in decimal."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('e3.32')
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('4.25oz')

    def test_quantity_int_from_str_fraction_contains_invalid_chars(self):
        """Raise a ValueError if non-numeric characters are in fraction."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('1/4oz')
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('e3/4')

    def test_quantity_int_from_str_integer_contains_invalid_chars(self):
        """Raise a ValueError if non-numeric characters are in integer."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('f47b47')
            Packet.quantity_int_from_str('14oz')
            Packet.quantity_int_from_str('f12')

    def test_quantity_int_from_str_dot_and_slash(self):
        """Raise a ValueError if quantity contains both . and /."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('4.9/3')

    def test_quantity_int_from_str_not_string(self):
        """Raise a TypeError if argument passed is not a string."""
        with self.assertRaises(TypeError):
            Packet.quantity_int_from_str(4.99)
        with self.assertRaises(TypeError):
            Packet.quantity_int_from_str(5)

    def test_quantity_int_from_str_removes_spaces(self):
        """Spaces should automatically be removed."""
        self.assertEqual(Packet.quantity_int_from_str('1 / 4'), -141)
        self.assertEqual(Packet.quantity_int_from_str(' 10.5 '), 1051)

    def test_quantity_int_from_str_too_many_decimal_digits(self):
        """Raise a ValueError if more than 9 digits to right of decimal."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('3.1415926535')

    def test_quantity_int_from_str_too_many_denominator_digits(self):
        """Raise a ValueError if fraction has more than 9 digits in denom."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('1/1234567890')

    def test_quantity_int_from_str_too_many_dots(self):
        """Raise a ValueError if quantity has more than one . in it."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('2.3.4')
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('127.0.0.1')

    def test_quantity_int_from_str_too_many_slashes(self):
        """Raise a ValueError if too many forward slashes in quantity."""
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('7/8/9')
        with self.assertRaises(ValueError):
            Packet.quantity_int_from_str('4//9')

    def test_quantity_int_from_str_valid_decimal(self):
        """Return an integer in correct format if given a valid decimal."""
        self.assertEqual(Packet.quantity_int_from_str('4.99'), 4992)
        self.assertEqual(Packet.quantity_int_from_str('1.255'), 12553)
        self.assertEqual(Packet.quantity_int_from_str('1.123456789'),
                         11234567899)

    def test_quantity_int_from_str_valid_fraction(self):
        """Return an integer in correct format given a valid fraction."""
        self.assertEqual(Packet.quantity_int_from_str('1/4'), -141)
        self.assertEqual(Packet.quantity_int_from_str('3/16'), -3162)
        self.assertEqual(Packet.quantity_int_from_str('249/5'), -24951)
        self.assertEqual(Packet.quantity_int_from_str('1/123456789'),
                         -11234567899)

    def test_quantity_int_from_str_valid_integer(self):
        """Return an integer in correct format given a valid integer."""
        self.assertEqual(Packet.quantity_int_from_str('100'), 1000)
        self.assertEqual(Packet.quantity_int_from_str('4'), 40)
        self.assertEqual(Packet.quantity_int_from_str('1234567890'),
                         12345678900)

    def test_quantity_str_from_int_fraction_has_no_denominator(self):
        """Raise a ValueError if given a negative number ending in 0."""
        with self.assertRaises(ValueError):
            Packet.quantity_str_from_int(-1230)

    def test_quantity_str_from_int_decimal(self):
        """Return a str of a decimal if given int is positive and ends > 0."""
        self.assertEqual(Packet.quantity_str_from_int(4992), '4.99')
        self.assertEqual(Packet.quantity_str_from_int(12553), '1.255')
        self.assertEqual(Packet.quantity_str_from_int(11234567899),
                         '1.123456789')

    def test_quantity_str_from_int_fraction_big_numerator(self):
        """Return a str of fraction in parts if given int is - and n > d."""
        self.assertEqual(Packet.quantity_str_from_int(-24951), '49 4/5')
        self.assertEqual(Packet.quantity_str_from_int(-34112), '3 1/11')
        self.assertEqual(Packet.quantity_str_from_int(-2501013), '2 48/101')

    def test_quantity_str_from_int_fraction_small_numerator(self):
        """Return a str of a fraction if given int is - and num < denom."""
        self.assertEqual(Packet.quantity_str_from_int(-141), '1/4')
        self.assertEqual(Packet.quantity_str_from_int(-3162), '3/16')
        self.assertEqual(Packet.quantity_str_from_int(-11234567899),
                         '1/123456789')

    def test_quantity_str_from_int_no_decimal_or_fraction(self):
        """Return a string containing an integer if given + int ends w/ 0."""
        self.assertEqual(Packet.quantity_str_from_int(1000), '100')
        self.assertEqual(Packet.quantity_str_from_int(40), '4')
        self.assertEqual(Packet.quantity_str_from_int(12345678900),
                         '1234567890')

    def test_quantity_str_from_int_not_integer(self):
        """Raise a TypeError if given non-int data."""
        with self.assertRaises(TypeError):
            Packet.quantity_str_from_int('1231')
        with self.assertRaises(TypeError):
            Packet.quantity_str_from_int(3.1415)


class TestSeed(unittest.TestCase):
    """Test methods of Seed in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_add_botanical_name_already_in_botanical_name(self):
        """Use the same instance as _botanical_name if name is the same."""
        seed = Seed()
        seed._botanical_name = BotanicalName(name='Asclepias incarnata')
        seed.add_botanical_name('Asclepias incarnata')
        self.assertIs(seed._botanical_name, seed._botanical_names[0])

    def test_add_botanical_name_already_in_botanical_names(self):
        """If botanical_names has not been comitted, don't add duplicates."""
        seed = Seed()
        seed._botanical_names.append(BotanicalName('Asclepias incarnata'))
        self.assertEqual(len(seed._botanical_names), 1)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertEqual(len(seed._botanical_names), 1)
        seed._botanical_names.append(BotanicalName('Echinacea purpurea'))
        self.assertEqual(len(seed._botanical_names), 2)
        seed.add_botanical_name('Echinacea purpurea')
        self.assertEqual(len(seed._botanical_names), 2)

    def test_add_category_bad_type(self):
        """Raise a TypeError if category is not a string."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.add_category(42)
        with self.assertRaises(TypeError):
            seed.add_category(['Herb', 'Vegetable'])

    def test_add_category_already_in_categories(self):
        """Do not add a category already in categories."""
        seed = Seed()
        seed._categories.append(Category(category='Vegetable'))
        seed._categories.append(Category(category='Herb'))
        self.assertEqual(len(seed._categories), 2)
        seed.add_category('Herb')
        self.assertEqual(len(seed._categories), 2)

    def test_add_category_already_in_category(self):
        """Set to same instance as ._category if the same category."""
        seed = Seed()
        seed._category = Category(category='Vegetable')
        seed.add_category('Vegetable')
        self.assertIs(seed._category, seed._categories[0])

    def test_add_common_name_already_in_common_name(self):
        """Set to same instance as ._common_name if the same name."""
        seed = Seed()
        seed._common_name = CommonName(name='Coleus')
        seed.add_common_name('Coleus')
        self.assertIs(seed._common_name, seed._common_names[0])

    def test_add_common_name_already_in_common_names(self):
        """Don't add a common name if it's already in ._common_names."""
        seed = Seed()
        seed._common_names.append(CommonName('Coleus'))
        self.assertEqual(len(seed._common_names), 1)
        seed.add_common_name('Coleus')
        self.assertEqual(len(seed._common_names), 1)
        seed._common_names.append(CommonName('Tomato'))
        self.assertEqual(len(seed._common_names), 2)
        seed.add_common_name('Tomato')
        self.assertEqual(len(seed._common_names), 2)

    def test_add_common_name_bad_type(self):
        """Raise a TypeError given non-string data."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.add_common_name(42)
        with self.assertRaises(TypeError):
            seed.add_common_name(['Coleus', 'Tomato'])

    def test_botanical_name_getter(self):
        """Return a string containing the botanical name for the seed."""
        seed = Seed()
        seed._botanical_name = BotanicalName('Asclepias incarnata')
        self.assertEqual(seed.botanical_name, 'Asclepias incarnata')

    def test_botanical_name_setter_bad_type(self):
        """Raise a TypeError given non-string data."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.botanical_name = 42
        with self.assertRaises(TypeError):
            seed.botanical_name = ['Asclepias incarnata', 'Echinacea purpurea']

    def test_botanical_names_getter(self):
        """Returns a list of strings from BotanicalName.botanical_name."""
        seed = Seed()
        seed._botanical_names.append(BotanicalName('Asclepias incarnata'))
        seed._botanical_names.append(BotanicalName('Echinacea purpurea'))
        seed._botanical_names.append(BotanicalName('Canis lupus'))
        self.assertEqual(seed.botanical_names.sort(),
                         ['Asclepias incarnata',
                          'Echinacea purpurea',
                          'Canis lupus'].sort())

    def test_botanical_names_setter_bad_type(self):
        """Raise a TypeError given data that is not a string or an iterable.

        If it is an iterable, it must contain only strings.
        """
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.botanical_names = 42
        with self.assertRaises(TypeError):
            seed.botanical_names = ('Asclepias incarnata', 42)

    def test_categories_getter(self):
        """Return a list of ._categories.category strings."""
        seed = Seed()
        seed._categories.append(Category('Annual Flower'))
        seed._categories.append(Category('Vegetable'))
        seed._categories.append(Category('Herb'))
        self.assertEqual(seed.categories.sort(),
                         ['Annual Flower', 'Vegetable', 'Herb'].sort())

    def test_categories_setter_bad_type(self):
        """Raise a TypeError if given data that is not a string or iterable.

        If it is an iterable, it must contain only strings.
        """
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.categories = 42
        with self.assertRaises(TypeError):
            seed.categories = ['Herb', 42]

    def test_category_getter(self):
        """Return ._category.category."""
        seed = Seed()
        seed._category = Category(category='Annual Flower')
        self.assertEqual(seed.category, 'Annual Flower')

    def test_category_setter_bad_type(self):
        """Raise a TypeError given non-string data."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.category = 42
        with self.assertRaises(TypeError):
            seed.category = ['Herb', 'Perennial Flower']

    def test_common_name_getter(self):
        """Return ._common_name.name."""
        seed = Seed()
        seed._common_name = CommonName(name='Coleus')
        self.assertEqual(seed.common_name, 'Coleus')

    def test_common_name_setter_bad_type(self):
        """Raise a TypeError given non-string data."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.common_name = 42
        with self.assertRaises(TypeError):
            seed.common_name = ['Tomato', 'Coleus']
        with self.assertRaises(TypeError):
            seed.common_name = CommonName('Coleus')

    def test_common_names_setter_iterable_containing_non_strings(self):
        """Raise a TypeError if iterable contains any non-string data."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.common_names = ['Coleus', 'Tomato', 42]
        with self.assertRaises(TypeError):
            seed.common_names = ('Coleus', 'Tomato', 41)

    def test_repr(self):
        """Return a string formatted <Seed '<name>'>"""
        seed = Seed()
        seed.name = 'Soulmate'
        self.assertEqual(seed.__repr__(), '<Seed \'Soulmate\'>')

    def test_common_names_setter_not_iterable_or_string(self):
        """Raise a TypeError given data that is not str or iterable."""
        seed = Seed()
        with self.assertRaises(TypeError):
            seed.common_names = 42
        with self.assertRaises(TypeError):
            seed.common_names = CommonName('Coleus')


class TestUnitType(unittest.TestCase):
    """Test methods of UnitType in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_repr(self):
        """Return a string formatted <UnitType '<unit_type>'>"""
        ut = UnitType()
        ut.unit_type = 'frogs'
        self.assertEqual(ut.__repr__(), '<UnitType \'frogs\'>')


if __name__ == '__main__':
    unittest.main()

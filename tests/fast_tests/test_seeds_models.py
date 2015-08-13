import unittest
from app import create_app
from app.seeds.models import BotanicalName, Packet


class TestBotanicalName(unittest.TestCase):
    """Test methods of BotanicalName in the seeds model."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_botanical_name_getter(self):
        """BotanicalName.botanical_name is the same as _botanical_name."""
        bn = BotanicalName()
        bn._botanical_name = 'Asclepias incarnata'
        self.assertEqual(bn.botanical_name, 'Asclepias incarnata')

    def test_botanical_name_setter_valid_input(self):
        """set BotanicalName._botanical_name if valid."""
        bn = BotanicalName()
        bn.botanical_name = 'Asclepias incarnata'
        self.assertEqual(bn._botanical_name, 'Asclepias incarnata')

    def test_init_invalid_botanical_name(self):
        with self.assertRaises(ValueError):
            BotanicalName('Richard M. Nixon')

    def test_init_valid_botanical_name(self):
        """Sets the BotanicalName.botanical_name to given value."""
        bn = BotanicalName('Asclepias incarnata')
        self.assertEqual(bn.botanical_name, 'Asclepias incarnata')

    def test_validate_more_than_two_words(self):
        """A botanical name is still valid with more than 2 words."""
        self.assertTrue(BotanicalName.validate('Brassica oleracea Var.'))

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
        pkt = Packet()
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('$4.99')
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('4.99USD')

    def test_price_int_from_str_correctly_formats_data(self):
        """Convert numbers to integers w fractional parts as lowest digits."""
        pkt = Packet()
        self.assertEqual(pkt.price_int_from_str('2.99'), 299)
        self.assertEqual(pkt.price_int_from_str('4.5'), 450)
        self.assertEqual(pkt.price_int_from_str('42'), 4200)

    def test_price_int_from_str_not_a_string(self):
        """Raise a TypeError if given data not of the string type."""
        pkt = Packet()
        with self.assertRaises(TypeError):
            pkt.price_int_from_str(4.99)
        with self.assertRaises(TypeError):
            pkt.price_int_from_str(5)

    def test_price_int_from_str_too_many_decimal_places(self):
        """Raise a ValueError if more than 2 digits exist to right of dot."""
        pkt = Packet()
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('4.225')
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('342.5555')

    def test_price_int_from_str_too_many_dots(self):
        """Raise a ValueError if there are too many dots in price."""
        pkt = Packet()
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('4.3.2')
        with self.assertRaises(ValueError):
            pkt.price_int_from_str('127.0.0.1')

    def test_price_str_from_int_returns_decimal_string(self):
        """Convert an int price to a string containing a decimal."""
        pkt = Packet()
        self.assertEqual(pkt.price_str_from_int(299), '2.99')
        self.assertEqual(pkt.price_str_from_int(450), '4.50')
        self.assertEqual(pkt.price_str_from_int(4200), '42.00')


if __name__ == '__main__':
    unittest.main()

import unittest
from decimal import Decimal
from fractions import Fraction
from app import create_app, db
from app.seeds.models import BotanicalName, Category, CommonName, Packet, \
    Price, QtyDecimal, QtyFraction, QtyInteger, Seed, Unit


class TestBotanicalNameWithDB(unittest.TestCase):
    """Test BotanicalName model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_name_is_queryable(self):
        """.name should be usable in queries."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        self.assertIs(BotanicalName.query.
                      filter_by(name='Asclepias incarnata').first(), bn)


class TestCategoryWithDB(unittest.TestCase):
    """Test Category model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_category_expression(self):
        """.category should be usable in filters."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.category = 'Annual Flower'
        cat2.category = 'Perennial Flower'
        cat3.category = 'Rock'
        db.session.commit()
        self.assertIs(Category.query.filter_by(category='Annual Flower').
                      first(), cat1)
        self.assertIs(Category.query.filter_by(category='Perennial Flower').
                      first(), cat2)
        self.assertIs(Category.query.filter_by(category='Rock').
                      first(), cat3)


class TestPacketWithDB(unittest.TestCase):
    """Test Packet model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_clear_quantity(self):
        """Clear all entries from the ._qty_x attributes."""
        pkt = Packet()
        db.session.add(pkt)
        pkt._qty_decimal = QtyDecimal(Decimal('3.14'))
        db.session.commit()
        self.assertEqual(QtyDecimal.query.count(), 1)
        self.assertEqual(pkt.clear_quantity(), 1)
        db.session.commit()
        self.assertIsNone(pkt._qty_decimal)
        self.assertEqual(QtyDecimal.query.count(), 1)
        pkt._qty_fraction = QtyFraction(Fraction(1, 4))
        db.session.commit()
        self.assertEqual(QtyFraction.query.count(), 1)
        self.assertEqual(pkt.clear_quantity(), 1)
        db.session.commit()
        self.assertIsNone(pkt._qty_fraction)
        self.assertEqual(QtyFraction.query.count(), 1)
        pkt._qty_integer = QtyInteger(100)
        db.session.commit()
        self.assertEqual(QtyInteger.query.count(), 1)
        self.assertEqual(pkt.clear_quantity(), 1)
        db.session.commit()
        self.assertIsNone(pkt._qty_integer)
        self.assertEqual(QtyInteger.query.count(), 1)
        pkt._qty_decimal = QtyDecimal.query.first()
        pkt._qty_fraction = QtyFraction.query.first()
        pkt._qty_integer = QtyInteger.query.first()
        self.assertEqual(pkt._qty_decimal.value, Decimal('3.14'))
        self.assertEqual(pkt._qty_fraction.value, Fraction(1, 4))
        self.assertEqual(pkt._qty_integer.value, 100)
        self.assertEqual(pkt.clear_quantity(), 3)
        self.assertIsNone(pkt._qty_decimal)
        self.assertIsNone(pkt._qty_fraction)
        self.assertIsNone(pkt._qty_integer)
        self.assertEqual(QtyDecimal.query.count(), 1)
        self.assertEqual(QtyFraction.query.count(), 1)
        self.assertEqual(QtyInteger.query.count(), 1)

    def test_price_comparator_eq(self):
        """Packet can be queried using price in == filter or filter_by."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.price = '2.99'
        self.assertIs(Packet.query.filter_by(price='2.99').first(), pkt)
        self.assertIs(Packet.query.filter_by(price=2.99).first(), pkt)
        self.assertIs(Packet.query.filter(Packet.price == '2.99').first(), pkt)

    def test_price_setter_truncates(self):
        """._price only stores decimals with a scale of 2.

        No rounding should occur, it should simply chop off the excess.
        """
        packet = Packet()
        db.session.add(packet)
        packet.price = '3.14159'
        db.session.commit()
        self.assertEqual(Packet.query.first().price, Decimal('3.14'))
        packet.price = '2.999'
        db.session.commit()
        self.assertEqual(Packet.query.first().price, Decimal('2.99'))

    def test_price_setter_uses_db(self):
        """Set ._price with price from db if it already exists."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('2.99')
        db.session.commit()
        packet = Packet()
        db.session.add(packet)
        packet.price = '2.99'
        self.assertIs(packet._price, price)

    def test_quantity_getter_success(self):
        """Return quantity if only one type of quantity is set."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1._qty_decimal = QtyDecimal(1.025)
        pkt2._qty_fraction = QtyFraction('1 1/4')
        pkt3._qty_integer = QtyInteger(100)
        db.session.commit()
        self.assertEqual(pkt1.quantity, Decimal('1.025'))
        self.assertEqual(pkt2.quantity, Fraction(5, 4))
        self.assertEqual(pkt3.quantity, 100)

    def test_quantity_setter_decimal_existing(self):
        """Set ._qty_decimal to existing DB entry if value is same."""
        qty1 = QtyDecimal(Decimal('1.23'))
        qty2 = QtyDecimal(Decimal('2.345'))
        qty3 = QtyDecimal(Decimal('3.4567'))
        db.session.add_all([qty1, qty2, qty3])
        db.session.commit()
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Decimal('1.23')
        pkt2.quantity = '2.345'
        pkt3.quantity = 3.4567
        db.session.commit()
        self.assertIs(pkt1._qty_decimal, qty1)
        self.assertIs(pkt2._qty_decimal, qty2)
        self.assertIs(pkt3._qty_decimal, qty3)

    def test_quantity_setter_decimal_new(self):
        """Set ._qty_decimal given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Decimal('3.14')
        pkt2.quantity = '1.25'
        pkt3.quantity = 2.125
        db.session.commit()
        self.assertEqual(pkt1._qty_decimal.value, Decimal('3.14'))
        self.assertEqual(pkt2._qty_decimal.value, Decimal('1.25'))
        self.assertEqual(pkt3._qty_decimal.value, Decimal('2.125'))

    def test_quantity_setter_fraction_existing(self):
        """Set ._qty_fraction to existing DB entry if value the same."""
        qty1 = QtyFraction(Fraction(1, 4))
        qty2 = QtyFraction(Fraction(3, 2))
        qty3 = QtyFraction(Fraction(11, 8))
        db.session.add_all([qty1, qty2, qty3])
        db.session.commit()
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Fraction(1, 4)
        pkt2.quantity = '3/2'
        pkt3.quantity = '1 3/8'
        db.session.commit()
        self.assertIs(pkt1._qty_fraction, qty1)
        self.assertIs(pkt2._qty_fraction, qty2)
        self.assertIs(pkt3._qty_fraction, qty3)

    def test_quantity_setter_fraction_new(self):
        """Set ._qty_fraction given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Fraction(1, 4)
        pkt2.quantity = '3/2'
        pkt3.quantity = '1 3/8'
        db.session.commit()
        self.assertEqual(pkt1._qty_fraction.value, Fraction(1, 4))
        self.assertEqual(pkt2._qty_fraction.value, Fraction(3, 2))
        self.assertEqual(pkt3._qty_fraction.value, Fraction(11, 8))

    def test_quantity_setter_int_existing(self):
        """Set ._qty_integer to existing DB entry if value the same."""
        qty1 = QtyInteger(100)
        qty2 = QtyInteger(42)
        qty3 = QtyInteger(9001)
        db.session.add_all([qty1, qty2, qty3])
        db.session.commit()
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = 100
        pkt2.quantity = '42'
        pkt3.quantity = ' 9001 '
        db.session.commit()
        self.assertIs(pkt1._qty_integer, qty1)
        self.assertIs(pkt2._qty_integer, qty2)
        self.assertIs(pkt3._qty_integer, qty3)

    def test_quantity_setter_int_new(self):
        """Set ._qty_integer given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = 100
        pkt2.quantity = '42'
        pkt3.quantity = ' 9001 '
        db.session.commit()
        self.assertEqual(pkt1._qty_integer.value, 100)
        self.assertEqual(pkt2._qty_integer.value, 42)
        self.assertEqual(pkt3._qty_integer.value, 9001)

    def test_quantity_equals(self):
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Decimal('3.14')
        pkt2.quantity = Fraction(1, 4)
        pkt3.quantity = 100
        db.session.commit()
        qty_dec_query = Packet.quantity_equals(Decimal('3.14'))
        self.assertIs(pkt1, qty_dec_query.first())
        self.assertEqual(qty_dec_query.count(), 1)
        qty_frac_query = Packet.quantity_equals(Fraction(1, 4))
        self.assertIs(pkt2, qty_frac_query.first())
        self.assertEqual(qty_frac_query.count(), 1)
        qty_int_query = Packet.quantity_equals(100)
        self.assertIs(pkt3, qty_int_query.first())
        self.assertEqual(qty_int_query.count(), 1)

        # TODO: get comparator for quantity working if possible.

#    def test_quantity_comparator_eq(self):
#        """Packet can be queried using .quantity in a filter or filter_by."""
#        pkt1 = Packet()
#        pkt2 = Packet()
#        pkt3 = Packet()
#        db.session.add_all([pkt1, pkt2, pkt3])
#        pkt1.quantity = 100
#        pkt2.quantity = '1/4'
#        pkt3.quantity = 5.4
#        db.session.commit()
#        self.assertIs(Packet.query.filter_by(quantity=100).first(), pkt1)
#        self.assertIs(Packet.query.filter_by(quantity='1/4').first(), pkt2)
#        self.assertIs(Packet.query.filter_by(quantity=5.4).first(), pkt3)
#        self.assertIs(Packet.query.filter(Packet.quantity == 100).first(),
#                      pkt1)
#
#    def test_quantity_comparator_lt(self):
#        """Packet can be queried using .quantity in < filter."""
#        pkt1 = Packet()
#        pkt2 = Packet()
#        pkt3 = Packet()
#        db.session.add_all([pkt1, pkt2, pkt3])
#        pkt1.quantity = '1/4'
#        self.assertIn(pkt1,
#                      Packet.query.filter(Packet.quantity < '2/3').all())

    def test_unit_expression(self):
        """unit should be usable in queries."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'frogs'
        self.assertIs(Packet.query.filter_by(unit='frogs').first(), pkt)

    def test_unit_getter(self):
        """.unit returns ._unit.unit"""
        pkt = Packet()
        db.session.add(pkt)
        pkt._unit = Unit('seeds')
        self.assertEqual(pkt.unit, 'seeds')

    def test_unit_setter_new_type(self):
        """create a new Unit in the database if not already there."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'seeds'
        db.session.commit()
        self.assertEqual(Unit.query.filter_by(unit='seeds').count(),
                         1)

    def test_unit_setter_existing_type(self):
        """Set the packet's unit to type from database if it exists."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'seeds'
        pkt2 = Packet()
        db.session.add(pkt2)
        pkt2.unit = 'seeds'
        self.assertIsNot(pkt, pkt2)
        self.assertIs(pkt.unit, pkt2.unit)
        pkt3 = Packet()
        db.session.add(pkt3)
        pkt3.unit = ('oz')
        self.assertIsNot(pkt.unit, pkt3.unit)


class TestSeedWithDB(unittest.TestCase):
    """Test Seed model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


if __name__ == '__main__':
    unittest.main()

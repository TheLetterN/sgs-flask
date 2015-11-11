from decimal import Decimal
from fractions import Fraction
from app.seeds.models import (
    BotanicalName,
    Category,
    Image,
    Packet,
    Price,
    QtyDecimal,
    QtyFraction,
    QtyInteger,
    Seed,
    Unit
)
from tests.conftest import db  # noqa


class TestBotanicalNameWithDB:
    """Test BotanicalName model methods that require database access."""
    def test_name_is_queryable(self, db):
        """.name should be usable in queries."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        assert BotanicalName.query\
            .filter_by(name='Asclepias incarnata').first() is bn


class TestCategoryWithDB:
    """Test Category model methods that require database access."""
    def test_category_expression(self, db):
        """.category should be usable in filters."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.category = 'Annual Flower'
        cat2.category = 'Perennial Flower'
        cat3.category = 'Rock'
        db.session.commit()
        assert Category.query.filter_by(category='Annual Flower')\
            .first() is cat1
        assert Category.query.filter_by(category='Perennial Flower')\
            .first() is cat2
        assert Category.query.filter_by(category='Rock').first() is cat3


class TestPacketWithDB:
    """Test Packet model methods that require database access."""
    def test_clear_quantity(self, db):
        """Clear all entries from the ._qty_x attributes."""
        pkt = Packet()
        db.session.add(pkt)
        pkt._qty_decimal = QtyDecimal(Decimal('3.14'))
        db.session.commit()
        assert QtyDecimal.query.count() == 1
        assert pkt.clear_quantity() == 1
        db.session.commit()
        assert pkt._qty_decimal is None
        assert QtyDecimal.query.count() == 1
        pkt._qty_fraction = QtyFraction(Fraction(1, 4))
        db.session.commit()
        assert QtyFraction.query.count() == 1
        assert pkt.clear_quantity() == 1
        db.session.commit()
        assert pkt._qty_fraction is None
        assert QtyFraction.query.count() == 1
        pkt._qty_integer = QtyInteger(100)
        db.session.commit()
        assert QtyInteger.query.count() == 1
        assert pkt.clear_quantity() == 1
        db.session.commit()
        assert pkt._qty_integer is None
        assert QtyInteger.query.count() == 1
        pkt._qty_decimal = QtyDecimal.query.first()
        pkt._qty_fraction = QtyFraction.query.first()
        pkt._qty_integer = QtyInteger.query.first()
        assert pkt._qty_decimal.value == Decimal('3.14')
        assert pkt._qty_fraction.value == Fraction(1, 4)
        assert pkt._qty_integer.value == 100
        assert pkt.clear_quantity() == 3
        assert pkt._qty_decimal is None
        assert pkt._qty_fraction is None
        assert pkt._qty_integer is None
        assert QtyDecimal.query.count() == 1
        assert QtyFraction.query.count() == 1
        assert QtyInteger.query.count() == 1

    def test_price_comparator_eq(self, db):
        """Packet can be queried using price in == filter or filter_by."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.price = '2.99'
        assert Packet.query.filter_by(price='2.99').first() is pkt
        assert Packet.query.filter_by(price=2.99).first() is pkt
        assert Packet.query.filter(Packet.price == '2.99').first() is pkt

    def test_price_setter_truncates(self, db):
        """._price only stores decimals with a scale of 2.

        No rounding should occur, it should simply chop off the excess.
        """
        packet = Packet()
        db.session.add(packet)
        packet.price = '3.14159'
        db.session.commit()
        assert Packet.query.first().price == Decimal('3.14')
        packet.price = '2.999'
        db.session.commit()
        assert Packet.query.first().price == Decimal('2.99')

    def test_price_setter_uses_db(self, db):
        """Set ._price with price from db if it already exists."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('2.99')
        db.session.commit()
        packet = Packet()
        db.session.add(packet)
        packet.price = '2.99'
        assert packet._price is price

    def test_quantity_getter_success(self, db):
        """Return quantity if only one type of quantity is set."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1._qty_decimal = QtyDecimal(1.025)
        pkt2._qty_fraction = QtyFraction('1 1/4')
        pkt3._qty_integer = QtyInteger(100)
        db.session.commit()
        assert pkt1.quantity == Decimal('1.025')
        assert pkt2.quantity == Fraction(5, 4)
        assert pkt3.quantity == 100

    def test_quantity_setter_decimal_existing(self, db):
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
        assert pkt1._qty_decimal is qty1
        assert pkt2._qty_decimal is qty2
        assert pkt3._qty_decimal is qty3

    def test_quantity_setter_decimal_new(self, db):
        """Set ._qty_decimal given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Decimal('3.14')
        pkt2.quantity = '1.25'
        pkt3.quantity = 2.125
        db.session.commit()
        assert pkt1._qty_decimal.value == Decimal('3.14')
        assert pkt2._qty_decimal.value == Decimal('1.25')
        assert pkt3._qty_decimal.value == Decimal('2.125')

    def test_quantity_setter_fraction_existing(self, db):
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
        assert pkt1._qty_fraction == qty1
        assert pkt2._qty_fraction == qty2
        assert pkt3._qty_fraction == qty3

    def test_quantity_setter_fraction_new(self, db):
        """Set ._qty_fraction given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Fraction(1, 4)
        pkt2.quantity = '3/2'
        pkt3.quantity = '1 3/8'
        db.session.commit()
        assert pkt1._qty_fraction.value == Fraction(1, 4)
        assert pkt2._qty_fraction.value == Fraction(3, 2)
        assert pkt3._qty_fraction.value == Fraction(11, 8)

    def test_quantity_setter_int_existing(self, db):
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
        assert pkt1._qty_integer is qty1
        assert pkt2._qty_integer is qty2
        assert pkt3._qty_integer is qty3

    def test_quantity_setter_int_new(self, db):
        """Set ._qty_integer given a value that fits there."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = 100
        pkt2.quantity = '42'
        pkt3.quantity = ' 9001 '
        db.session.commit()
        assert pkt1._qty_integer.value == 100
        assert pkt2._qty_integer.value == 42
        assert pkt3._qty_integer.value == 9001

    def test_quantity_equals(self, db):
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        db.session.add_all([pkt1, pkt2, pkt3])
        pkt1.quantity = Decimal('3.14')
        pkt2.quantity = Fraction(1, 4)
        pkt3.quantity = 100
        db.session.commit()
        qty_dec_query = Packet.quantity_equals(Decimal('3.14'))
        assert pkt1 is qty_dec_query.first()
        assert qty_dec_query.count() == 1
        qty_frac_query = Packet.quantity_equals(Fraction(1, 4))
        assert pkt2 is qty_frac_query.first()
        assert qty_frac_query.count() == 1
        qty_int_query = Packet.quantity_equals(100)
        assert pkt3 is qty_int_query.first()
        assert qty_int_query.count() == 1

    def test_unit_expression(self, db):
        """unit should be usable in queries."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'frogs'
        assert Packet.query.filter_by(unit='frogs').first() is pkt

    def test_unit_getter(self, db):
        """.unit returns ._unit.unit"""
        pkt = Packet()
        db.session.add(pkt)
        pkt._unit = Unit('seeds')
        assert pkt.unit == 'seeds'

    def test_unit_setter_new_type(self, db):
        """create a new Unit in the database if not already there."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'seeds'
        db.session.commit()
        assert Unit.query.filter_by(unit='seeds').count() == 1

    def test_unit_setter_existing_type(self, db):
        """Set the packet's unit to type from database if it exists."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit = 'seeds'
        pkt2 = Packet()
        db.session.add(pkt2)
        pkt2.unit = 'seeds'
        assert pkt is not pkt2
        assert pkt.unit is pkt2.unit
        pkt3 = Packet()
        db.session.add(pkt3)
        pkt3.unit = ('oz')
        assert pkt.unit is not pkt3.unit


class TestSeedWithDB:
    """Test Seed model methods that require database access."""
    def test_thumbnail_path_with_thumbnail(self, db):
        """Return path to thumbnail if it exists."""
        seed = Seed()
        thumb = Image()
        db.session.add_all([seed, thumb])
        seed.name = 'Foxy'
        thumb.filename = 'hello.jpg'
        seed.thumbnail = thumb
        db.session.commit()
        assert seed.thumbnail_path == 'images/hello.jpg'

    def test_thumbnail_path_no_thumbnail(self, db):
        """Return path to defaulth thumbnail if seed has none."""
        seed = Seed()
        db.session.add(seed)
        seed.name = 'Foxy'
        db.session.commit()
        assert seed.thumbnail_path == 'images/default_thumb.jpg'

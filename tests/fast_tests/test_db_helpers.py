from decimal import Decimal
from unittest import mock

from app.db_helpers import dbify, OrderingListMixin, USDollar


class TestDbify:
    """Class for testing the dbify function."""
    def test_dbify(self):
        """Convert a string into a proper titlecase version."""
        assert dbify('stuff') == 'Stuff'
        assert dbify('This is a Title') == 'This Is a Title'
        assert dbify('lowercase stuff') == 'Lowercase Stuff'
        assert dbify('You will forget-me-not') == 'You Will Forget-me-not'
        assert dbify('tears for fears') == 'Tears for Fears'
        assert dbify('ashes to ashes') == 'Ashes to Ashes'
        assert dbify('CRUISE CONTROL FOR COOL') == 'Cruise Control for Cool'

    def test_dbify_cb(self):
        """Test special cases handled by the callback function cb in dbify."""
        assert dbify('I II III IV V XP BLBP') == 'I II III IV V XP BLBP'
        assert dbify('THIRTY-THREE') == 'Thirty-three'
        assert dbify('FORM 1040EZ') == 'Form 1040EZ'
        assert dbify('ROYALE W/ CHEESE') == 'Royale w/ Cheese'
        assert dbify('D\'AVIGNON RADISH') == 'd\'Avignon Radish'
        assert dbify('BIRD\'S EYE') == 'Bird\'s Eye'
        assert dbify('O\'HARA') == 'O\'Hara'

    def test_dbify_null(self):
        """Return None if given None or an empty string."""
        assert dbify(None) is None
        assert dbify('') is None

    def test_dbify_mixed_case(self):
        """Don't let titlecase leave mixed-case strings alone."""
        assert dbify(
            'BENARY\'S GIANT FORMULA MIX (Blue Point)'
        ) == 'Benary\'s Giant Formula Mix (Blue Point)'
        assert dbify('ONE TWO THREE (four)') == 'One Two Three (Four)'


class TestOrderingListMixin:
    """Test methods of OrderingListMixin."""
    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_forward(self, m_pc):
        """Move an object forward in its parent collection."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move(1)
        assert l == [o2, o1, o3]
        o2.move(2)
        assert l == [o1, o3, o2]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_past_last(self, m_pc):
        """Move object to end position if it would otherwise go past."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move(3)
        assert l == [o2, o3, o1]
        o2.move(42)
        assert l == [o3, o1, o2]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_last_forward(self, m_pc):
        """Don't move last object if attempting to move forward."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o3.move(1)
        assert l == [o1, o2, o3]
        o3.move(42)
        assert l == [o1, o2, o3]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_backward(self, m_pc):
        """Move an object backward if delta is negative."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o3.move(-1)
        assert l == [o1, o3, o2]
        o2.move(-2)
        assert l == [o2, o1, o3]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_before_beginning(self, m_pc):
        """Move object to first position if delta would put it before."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o3.move(-3)
        assert l == [o3, o1, o2]
        o2.move(-42)
        assert l == [o2, o3, o1]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_first_backward(self, m_pc):
        """Don't move object backward if it's first."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move(-1)
        assert l == [o1, o2, o3]
        o1.move(-42)
        assert l == [o1, o2, o3]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_after_forwards(self, m_pc):
        """Move obj to position after other if other is after obj."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move_after(o2)
        assert l == [o2, o1, o3]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_after_backwards(self, m_pc):
        """Move obj to position after other if other is before obj."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o3.move_after(o1)
        assert l == [o1, o3, o2]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_after_last(self, m_pc):
        """Move obj to last position if other is last."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move_after(o3)
        assert l == [o2, o3, o1]

    @mock.patch('app.db_helpers.OrderingListMixin.parent_collection',
                new_callable=mock.PropertyMock)
    def test_move_after_self(self, m_pc):
        """Keep order the same if for some reason other is self."""
        o1 = OrderingListMixin()
        o2 = OrderingListMixin()
        o3 = OrderingListMixin()
        l = [o1, o2, o3]
        m_pc.return_value = l
        o1.move_after(o1)
        assert l == [o1, o2, o3]
        o2.move_after(o2)
        assert l == [o1, o2, o3]
        o3.move_after(o3)
        assert l == [o1, o2, o3]


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

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
    Section,
    CommonName,
    Image,
    Index,
    Cultivar,
    OrderingListMixin,
    Packet,
    PositionableMixin,
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

    def test_dbify_cb(self):
        """Test special cases handled by the callback function cb in dbify."""
        assert dbify('I II III IV V XP BLBP') == 'I II III IV V XP BLBP'
        assert dbify('THIRTY-THREE') == 'Thirty-three'
        assert dbify('FORM 1040EZ') == 'Form 1040EZ'
        assert dbify('ROYALE W/ CHEESE') == 'Royale w/ Cheese'
        assert dbify('D\'AVIGNON RADISH') == 'd\'Avignon Radish'
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


class TestPositionableMixin:
    """Test methods of the PositionableMixin class."""
    @mock.patch('app.seeds.models.db')
    def test_positionable_instances(self, m_db):
        """Get all instances from db and db.session.new."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        PositionableMixin.query = mock.MagicMock()
        PositionableMixin.query.all.return_value = [p1, p2, p3]
        p4 = PositionableMixin()
        p5 = PositionableMixin()
        p6 = PositionableMixin()
        m_db.session.new = [p4, p5, p6]
        assert p1.positionable_instances == [
            p1, p2, p3, p4, p5, p6
        ]

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances')
    def test_auto_position_first(self, m_gai):
        """Set position to 1 if no other instances exist."""
        m_gai.return_value = []
        p1 = PositionableMixin()
        # Since PositionableMixin is not a declarative model, but a mixin that
        # adds a column to models, p1.position needs to be set to None before
        # using auto_position to prevent a TypeError from being raised due to
        # attempting to interpret an unbound column as a boolean.
        p1.position = None
        p1.auto_position()
        assert p1.position == 1

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_auto_position_with_others(self, m_gai):
        p1 = PositionableMixin()
        p1.position = 1
        p2 = PositionableMixin()
        p2.position = 2
        p3 = PositionableMixin()
        p3.position = 3
        m_gai.return_value = [p1, p2, p3]
        p4 = PositionableMixin()
        p4.position = None
        p4.auto_position()
        assert p4.position == 4

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_set_position_inserts(self, m_pi):
        """Setting a position btwn first and last should insert there."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        ptest = PositionableMixin()
        ptest.position = None
        ptest.set_position(2)
        assert p1.position == 1
        assert ptest.position == 2
        assert p2.position == 3
        assert p3.position == 4

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_set_position_insert_first(self, m_pi):
        """Bump others up when inserting to start position."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        ptest = PositionableMixin()
        ptest.position = None
        ptest.set_position(1)
        assert ptest.position == 1
        assert p1.position == 2
        assert p2.position == 3
        assert p3.position == 4

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_set_position_insert_before_first(self, m_pi):
        """Insert at first position if given number below 1."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        ptest = PositionableMixin()
        ptest.position = None
        ptest.set_position(0)
        assert ptest.position == 1
        assert p1.position == 2
        assert p2.position == 3
        assert p3.position == 4
        m_pi.return_value = [p1, p2, p3, ptest]
        ptest2 = PositionableMixin()
        ptest2.position = None
        ptest2.set_position(-1)
        assert ptest2.position == 1
        assert ptest.position == 2
        assert p1.position == 3
        assert p2.position == 4
        assert p3.position == 5

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_set_position_insert_last(self, m_pi):
        """Insert after last position if given last position + 1."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        ptest = PositionableMixin()
        ptest.position = None
        ptest.set_position(4)
        assert p1.position == 1
        assert p2.position == 2
        assert p3.position == 3
        assert ptest.position == 4

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_set_position_insert_after_last(self, m_pi):
        """Insert after last position if given arbitrarily larger position."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        ptest = PositionableMixin()
        ptest.position = None
        ptest.set_position(42)
        assert p1.position == 1
        assert p2.position == 2
        assert p3.position == 3
        assert ptest.position == 4

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    @mock.patch('app.seeds.models.PositionableMixin.auto_position')
    def test_set_position_empty_rows(self, m_ap, m_pi):
        """Auto-position if no other positioned objects exist."""
        m_pi.return_value = []
        ptest = PositionableMixin()
        ptest.set_position(42)
        assert m_ap.called

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_clean_positions_removes_gaps(self, m_pi):
        """Remove gaps in position when cleaning."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 5
        p3.position = 9
        m_pi.return_value = [p1, p2, p3]
        p1.clean_positions()
        assert p1.position == 1
        assert p2.position == 2
        assert p3.position == 3

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_clean_positions_removes_self(self, m_pi):
        """Remove self from positioning if specified."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 5
        p3.position = 9
        m_pi.return_value = [p1, p2, p3]
        p1.clean_positions(remove_self=True)
        assert p2.position == 1
        assert p3.position == 2

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_clean_positions_sets_nulls(self, m_pi):
        """Set positions for objects with no position set."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p4 = PositionableMixin()
        p1.position = 1
        p2.position = None
        p3.position = 2
        p4.position = None
        m_pi.return_value = [p1, p2, p3, p4]
        p1.clean_positions()
        assert p1.position == 1
        assert p3.position == 2
        assert p2.position == 3
        assert p4.position == 4

    @mock.patch('app.seeds.models.PositionableMixin._step')
    def test_previous(self, m_s):
        """_step backwards."""
        p1 = PositionableMixin()
        p1.previous
        m_s.assert_called_with(forward=False)

    @mock.patch('app.seeds.models.PositionableMixin._step')
    def test_next(self, m_s):
        """_step forwards."""
        p1 = PositionableMixin()
        p1.next
        m_s.assert_called_with(forward=True)

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_first(self, m_pi):
        """Return the lowest positioned instance."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        p = PositionableMixin()
        assert p.first is p1

    @mock.patch('app.seeds.models.PositionableMixin.positionable_instances',
                new_callable=mock.PropertyMock)
    def test_last(self, m_pi):
        """Return the highest positioned instance."""
        p1 = PositionableMixin()
        p2 = PositionableMixin()
        p3 = PositionableMixin()
        p1.position = 1
        p2.position = 2
        p3.position = 3
        m_pi.return_value = [p1, p2, p3]
        p = PositionableMixin()
        assert p.last is p3


class TestOrderingListMixin:
    """Test methods of OrderingListMixin."""
    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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

    @mock.patch('app.seeds.models.OrderingListMixin.parent_collection',
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
    def test__repr__(self):
        """Return string formatted <Index '<index>'>"""
        index = Index()
        index.name = 'vegetable'
        assert index.__repr__() == '<Index \'vegetable\'>'

    def test__eq__(self):
        """Return True if all columns are the same value."""
        idx1 = Index()
        idx2 = Index()
        idx1.id = 42
        assert idx1 != idx2
        idx2.id = 42
        assert idx1 == idx2
        idx1.position = 3
        idx1.name = 'Annual'
        idx1.slug = 'annual'
        idx1.description = 'Not built to last.'
        assert idx1 != idx2
        idx2.position = 3
        idx2.name = 'Annual'
        idx2.slug = 'annual'
        idx2.description = 'Not built to last.'
        assert idx1 == idx2

    @mock.patch('app.seeds.models.Index.query')
    def test_dict__to_from_dict__(self, m_q):
        """An Index.dict_ fed to Index.from_dict_ creates identical Index."""
        m_q.get.return_value = None
        idx1 = Index()
        idx1.id = 42
        idx1.position = 3
        idx1.name = 'Annual'
        idx1.slug = 'annual'
        idx1.description = 'Not built to last.'
        d = idx1.dict_
        assert Index.from_dict_(d) == idx1

    @mock.patch('app.seeds.models.Index.query')
    def test_from_dict__index_exists(self, m_q):
        """Do not allow from_dict_ to create an Index w/ id already in use."""
        old_idx = Index()
        old_idx.id = 42
        m_q.get.return_value = old_idx
        idx = Index()
        idx.id = 42
        idx.position = 3
        idx.name = 'Annual'
        idx.slug = 'annual'
        idx.description = 'Not built to last.'
        d = idx.dict_
        with pytest.raises(ValueError):
            Index.from_dict_(d)

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

    def test_generate_slug_with_name(self):
        """Return a slugified version of the plural of name if name exists."""
        idx = Index(name='Finger')
        assert idx.generate_slug() == 'fingers'

    def test_generate_slug_no_name(self):
        """Return None if Index has no name."""
        idx = Index()
        assert idx.generate_slug() is None

    # TODO: Test save_to_json_file


class TestCommonName:
    """Test methods of CommonName in the seeds model."""
    def test__repr__(self):
        """Return string formatted <CommonName '<name>'>"""
        cn = CommonName(name='Coleus')
        assert cn.__repr__() == '<CommonName \'Coleus\'>'

    def test__eq__(self):
        """A `CommonName` is equal to another if relevant columns match."""
        cn1 = CommonName()
        cn2 = CommonName()
        idx = Index()
        idx.id = 1
        x = CommonName()
        y = CommonName()
        z = CommonName()
        x.id = 24
        y.id = 25
        z.id = 26
        cn1.id = 42
        cn1.index = idx
        cn1.name = 'Annual'
        cn1.slug = 'annual'
        cn1.description = 'Not built to last.'
        cn1.instructions = 'Plant them.'
        cn1.grows_with = [x, y, z]
        cn1.visible = True
        assert cn1 != cn2
        cn2.id = 42
        cn2.index = idx
        cn2.name = 'Annual'
        cn2.slug = 'annual'
        cn2.description = 'Not built to last.'
        cn2.instructions = 'Plant them.'
        cn2.grows_with = [x, y, z]
        cn2.visible = True
        assert cn1 == cn2

    @mock.patch('app.seeds.models.CommonName.query')
    @mock.patch('app.seeds.models.Index.query')
    def test_dict__to_from_dict_(self, m_iq, m_cq):
        """Create new CommonName equal to CN.dict_

        Note:

        grows_with is excluded because that must be handled by a different
        function.
        """
        m_cq.get.return_value = None
        cn = CommonName()
        idx = Index()
        m_iq.get.return_value = idx
        idx.id = 1
        cn.id = 42
        cn.index = idx
        cn.name = 'Annual'
        cn.slug = 'annual'
        cn.description = 'Not built to last.'
        cn.instructions = 'Plant them.'
        cn.visible = True
        d = cn.dict_
        assert CommonName.from_dict_(d)

    @mock.patch('app.seeds.models.CommonName.query')
    def test_dict__to_from_dict_existing_cn(self, m_q):
        """Do not create `CommonName` if id already exists in db."""
        old_cn = CommonName()
        old_cn.id = 42
        m_q.get.return_value = old_cn
        cn = CommonName()
        idx = Index()
        idx.id = 1
        cn.id = 42
        cn.index = idx
        cn.name = 'Annual'
        cn.slug = 'annual'
        cn.description = 'Not built to last.'
        cn.instructions = 'Plant them.'
        cn.visible = True
        d = cn.dict_
        with pytest.raises(ValueError):
            CommonName.from_dict_(d)

    @mock.patch('app.seeds.models.CommonName.from_queryable_values')
    def test_from_queryable_dict(self, m_fqv):
        """Run CommonName.from_queryable_values with params from dict."""
        CommonName.from_queryable_dict(d={'Common Name': 'Foxglove',
                                          'Index': 'Perennial'})
        m_fqv.assert_called_with(name='Foxglove', index='Perennial')

    def test_queryable_dict(self):
        """Return a dict containing the name and index of a CommonName."""
        cn = CommonName()
        assert cn.queryable_dict == {'Common Name': None, 'Index': None}
        cn.name = 'Foxglove'
        assert cn.queryable_dict == {'Common Name': 'Foxglove', 'Index': None}
        cn.index = Index(name='Perennial')
        assert cn.queryable_dict == {'Common Name': 'Foxglove',
                                     'Index': 'Perennial'}

    def test_arranged_name_with_comma(self):
        """Re-arrange name if a comma is in it."""
        cn1 = CommonName(name='Nelson, Extremely Full')
        assert cn1.arranged_name == 'Extremely Full Nelson'
        cn2 = CommonName(name='Dead Dove, Do Not Eat')
        assert cn2.arranged_name == 'Do Not Eat Dead Dove'

    def test_arranged_name_no_comma(self):
        """Return normal name if no comma is in it."""
        cn = CommonName(name='John Smith')
        assert cn.arranged_name == 'John Smith'

    def test_arranged_name_multiple_commas(self):
        """Don't mess with it if it's got more than one comma."""
        cn = CommonName(name='Lies, Damned Lies, and Statistics')
        assert cn.arranged_name == 'Lies, Damned Lies, and Statistics'

    def test_arranged_name_no_name(self):
        """Return None if self.name is None."""
        cn = CommonName()
        assert cn.arranged_name is None

    def test_header(self):
        """Return '<arranged_name> Seeds'."""
        cn = CommonName()
        cn.name = 'Foxglove'
        assert cn.header == 'Foxglove Seeds'

    def test_header_no_name(self):
        """Return an empty string if no name set."""
        cn = CommonName()
        assert cn.header == ''

    def test_select_field_title(self):
        """Return '<name> (<index name>)'"""
        cn = CommonName(name='Foxglove', index=Index(name='Perennial'))
        assert cn.select_field_title == 'Foxglove (Perennial)'

    def test_html_botanical_names_no_bns(self):
        """Return an empty string if CN has no BNs."""
        cn = CommonName(name='Foxglove')
        assert cn.html_botanical_names == ''

    def test_html_botanical_names_with_bns(self):
        """Return a list of botanical names formatted for use on webpage."""
        cn = CommonName(name='Foxglove')
        cn.botanical_names = [BotanicalName(name='Digitalis purpurea'),
                              BotanicalName(name='Digitalis über alles'),
                              BotanicalName(name='Digitalis does dallas')]
        assert cn.html_botanical_names == (
            'Digitalis purpurea, '
            '<abbr title="Digitalis">D.</abbr> über alles, '
            '<abbr title="Digitalis">D.</abbr> does dallas'
        )

    def test_has_public_cultivars(self):
        """Return True if at least one Cultivar is public, False if not."""
        cn = CommonName()
        cv1 = mock.MagicMock()
        cv1.public = False
        cn.cultivars.append(cv1)
        assert not cn.has_public_cultivars
        cv2 = mock.MagicMock()
        cv2.public = False
        cn.cultivars.append(cv2)
        assert not cn.has_public_cultivars
        cv3 = mock.MagicMock()
        cv3.public = True
        cn.cultivars.append(cv3)
        assert cn.has_public_cultivars


class TestBotanicalName:
    """Test methods of BotanicalName in the seeds model."""
    def test_init_with_common_names(self):
        """Set common_names if given."""
        cns = [CommonName('One'), CommonName('Two')]
        bn = BotanicalName(name='Digitalis über alles',
                           common_names=cns)
        assert bn.common_names == cns

    def test_init_without_common_names(self):
        """Don't do anything to common_names if none given."""
        bn = BotanicalName(name='Digitalis über alles')
        assert bn.common_names == []

    def test_repr(self):
        """Return a string in format <BotanicalName '<botanical_name>'>"""
        bn = BotanicalName(name='Asclepias incarnata')
        assert bn.__repr__() == '<BotanicalName \'Asclepias incarnata\'>'

    def test_genus(self):
        """Return the first word in the BotanicalName."""
        bn = BotanicalName(name='Digitalis über alles')
        assert bn.genus == 'Digitalis'

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


class TestSection:
    """Test methods of the Section class in seeds.models."""
    def test_repr(self):
        """Return formatted string with full name."""
        sec = Section(name='Polkadot',
                      common_name=CommonName(name='Foxglove'))
        assert sec.__repr__() == '<Section \'Polkadot Foxglove\'>'

    def test_fullname(self):
        """Returns name of section along with common name."""
        ser = Section()
        assert ser.fullname is None
        ser.name = 'Dalmatian'
        assert ser.fullname == 'Dalmatian'
        ser.common_name = CommonName(name='Foxglove')
        assert ser.fullname == 'Dalmatian Foxglove'
#
#    def test_set_common_name_new(self):
#        """Set common_name and parent_common_name."""
#        cn = CommonName()
#        sec = Section()
#        sec.set_common_name(cn)
#        assert sec.common_name is cn
#        assert sec.parent_common_name is cn
#
#    def test_set_common_name_default_insert_at(self):
#        """insert at the last position if not explicitly set."""
#        cn = CommonName()
#        s1 = Section()
#        s1.set_common_name(cn)
#        s2 = Section()
#        s2.set_common_name(cn)
#        assert cn.child_sections == [s1, s2]
#        s3 = Section()
#        s3.set_common_name(cn)
#        assert cn.child_sections == [s1, s2, s3]
#
#    def test_set_common_name_too_high_insert_at(self):
#        """If given insert_at greater than last index, insert at last index."""
#        cn = CommonName()
#        s1 = Section()
#        s1.set_common_name(cn)
#        s2 = Section()
#        s2.set_common_name(cn, insert_at=42)
#        assert cn.child_sections == [s1, s2]
#
#    def test_set_common_name_none(self):
#        """Set common_name and parent_common_name to None if cn=None."""
#        cn = CommonName()
#        sec = Section()
#        sec.common_name = cn
#        sec.parent_common_name = cn
#        sec.set_common_name(None)
#        assert sec.common_name is None
#        assert sec.parent_common_name is None
#
#    def test_set_common_name_clears_parent_new_cn(self):
#        """If cn is new, clear parent."""
#        cn1 = CommonName()
#        cn2 = CommonName()
#        sec = Section()
#        psec = Section()
#        sec.set_common_name(cn1)
#        sec.parent = psec
#        sec.set_common_name(cn2)
#        assert sec.parent is None
#
#    def test_set_common_name_same_cn(self):
#        """Remove parent and set parent_common_name anyway if given same cn."""
#        cn = CommonName()
#        sec = Section()
#        sec.common_name = cn
#        psec = Section()
#        sec.parent = psec
#        sec.set_common_name(cn)
#        assert sec.common_name is cn
#        assert sec.parent_common_name is cn
#        assert sec.parent is None
#
#    def test_set_common_name_same_cn_new_position(self):
#        """If cn is the same but insert_at is given, change its position."""
#        cn = CommonName()
#        s1 = Section()
#        s2 = Section()
#        s3 = Section()
#        s1.set_common_name(cn)
#        s2.set_common_name(cn)
#        s3.set_common_name(cn)
#        assert cn.child_sections == [s1, s2, s3]
#        s3.set_common_name(cn, insert_at=0)
#        assert cn.child_sections == [s3, s1, s2]
#        s3.set_common_name(cn, insert_at=1)
#        assert cn.child_sections == [s1, s3, s2]
#
#    def test_set_parent_same_as_self(self):
#        """Raise a ValueError if trying to set a Section as its own parent."""
#        sec = Section()
#        with pytest.raises(ValueError):
#            sec.set_parent(sec)
#
#    def test_set_parent_all_new(self):
#        """Set parent to other."""
#        sec = Section()
#        psec = Section()
#        sec.set_parent(psec)
#        assert sec.parent is psec
#
#    def test_set_parent_with_cn(self):
#        """Clear parent_common_name if setting parent."""
#        cn = CommonName()
#        sec = Section()
#        psec = Section()
#        sec.common_name = cn
#        sec.parent_common_name = cn
#        sec.set_parent(psec)
#        assert sec.common_name is cn
#        assert sec.parent_common_name is None
#        assert sec.parent is psec
#
#    def test_set_parent_default_insert_at(self):
#        """Insert at end of parent.children."""
#        s1 = Section()
#        s2 = Section()
#        s3 = Section()
#        psec = Section()
#        s1.set_parent(psec)
#        assert psec.children == [s1]
#        s2.set_parent(psec)
#        assert psec.children == [s1, s2]
#        s3.set_parent(psec)
#        assert psec.children == [s1, s2, s3]
#
#    def test_set_parent_too_high_insert_at(self):
#        """Insert at end given insert_at beyond end."""
#        s1 = Section()
#        s2 = Section()
#        psec = Section()
#        s1.set_parent(psec)
#        s2.set_parent(psec, insert_at=42)
#        assert psec.children == [s1, s2]
#
#    def test_set_parent_same_parent_new_position(self):
#        """Change position of section if setting to same parent."""
#        s1 = Section()
#        s2 = Section()
#        s3 = Section()
#        psec = Section()
#        psec.children = [s1, s2, s3]
#        s3.set_parent(psec, insert_at=0)
#        assert psec.children == [s3, s1, s2]
#        s2.set_parent(psec, insert_at=1)
#        assert psec.children == [s3, s2, s1]


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

from decimal import Decimal
from unittest import mock
import pytest
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Index,
    Cultivar,
    Packet,
    Quantity,
    Series
)


class TestIndexRelatedEventHandlers:
    """Test event listener functions that involve Index instances."""
    # before_index_insert_or_update
    @mock.patch('app.seeds.models.Index.generate_slug')
    def test_before_index_insert_or_update_flush(self, m_gs, db):
        """Set the slug of an instance of Index before flushing to db."""
        m_gs.return_value = 'new-index'
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.flush()
        assert m_gs.called
        assert idx.slug == 'new-index'

    # save_indexes_to_json_before_commit
    @mock.patch('app.seeds.models.save_indexes_to_json_file')
    def test_save_indexes_json_before_commit_new_index(self, m_sitjf, db):
        """Run save_indexes_to_json_file if any new Indexes in session."""
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.commit()
        assert m_sitjf.call_count == 1

    @mock.patch('app.seeds.models.save_indexes_to_json_file')
    def test_save_indexes_to_json_before_commit_edited_index(self,
                                                             m_sitjf,
                                                             db):
        """Run if any edited Indexes are in the session."""
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.commit()
        db.session.expunge(idx)
        assert idx not in db.session
        idxq = Index.query.filter(Index.name == 'New Index').one_or_none()
        idxq.name = 'Edited Index'
        db.session.commit()
        assert m_sitjf.call_count == 2

    @mock.patch('app.seeds.models.save_indexes_to_json_file')
    def test_save_indexes_to_json_before_commit_deleted_index(self,
                                                              m_sitjf,
                                                              db):
        """Run if any deleted Indexes are in the session."""
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.commit()
        db.session.expunge(idx)
        idxq = Index.query.filter(Index.name == 'New Index').one_or_none()
        db.session.delete(idxq)
        db.session.commit()
        assert m_sitjf.call_count == 2

    @mock.patch('app.seeds.models.save_indexes_to_json_file')
    def test_save_indexes_to_json_before_commit_no_indexes(self, m_sitjf, db):
        """Do not run if there are no Indexes in the session."""
        cn = CommonName(name='John')
        db.session.add(cn)
        db.session.commit()
        assert not m_sitjf.called


class TestCommonNameRelatedEventHandlers:
    """Test event listener functions that involve CommonName instances."""
    @mock.patch('app.seeds.models.CommonName.generate_slug')
    def test_before_common_name_insert_or_update_flush(self, m_gs, db):
        """Set the slug for a CommonName instance before flush."""
        m_gs.return_value = 'new-common-name'
        cn = CommonName(name='New Common Name')
        db.session.add(cn)
        db.session.flush()
        assert m_gs.called
        assert cn.slug == 'new-common-name'


class TestBotanicalNameWithDB:
    """Test BotanicalName model methods that require database access."""
    def test_name_is_queryable(self, db):
        """.name should be usable in queries."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        assert BotanicalName.query\
            .filter_by(name='Asclepias incarnata').first() is bn


class TestBotanicalNameRelatedEventHandlers:
    """Test event listener functions that involve BotanicalName instances."""
    @mock.patch('app.seeds.models.BotanicalName.validate')
    def test_before_botanical_name_insert_or_update_flush(self, m_v, db):
        """Raise a ValueError if trying to flush an invalid BotanicalName."""
        m_v.return_value = False
        bn = BotanicalName(name='CAPSLOCK IS CRUISE CONTROL FOR COOL')
        db.session.add(bn)
        with pytest.raises(ValueError):
            db.session.flush()


class TestCultivarWithDB:
    """Test Cultivar model methods that require database access."""
    def test_from_lookup_dict(self, db):
        """Load a cultivar given a dict with name, series, and common_name.

        It should only load a Cultivar that exactly matches the data in the
        dict.
        """
        cv1 = Cultivar(name='Name')
        cv2 = Cultivar(name='Name')
        cv3 = Cultivar(name='Name')
        cv4 = Cultivar(name='Name')
        cv5 = Cultivar(name='Name')
        cv6 = Cultivar(name='Name')
        cv7 = Cultivar(name='Like, Other Name')
        cn = CommonName(name='Common Name')
        cn.index = Index(name='Index')
        cn2 = CommonName(name='Other Common Name')
        cn2.index = Index(name='Other Index')
        sr = Series(name='Series')
        sr2 = Series(name='Other Series')
        cv2.common_name = cn
        cv3.common_name = cn
        cv4.common_name = cn2
        cv5.common_name = cn2
        cv6.common_name = cn
        cv7.common_name = cn
        cv3.series = sr
        cv5.series = sr
        cv6.series = sr2
        cv7.series = sr

        db.session.add_all([cv1,
                            cv2,
                            cv3,
                            cv4,
                            cv5,
                            cv6,
                            cv7,
                            cn,
                            cn2,
                            sr,
                            sr2])
        db.session.commit()
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': None,
             'Index': None,
             'Series': None}
        ) is cv1
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Index': 'Index',
             'Series': None}
        ) is cv2
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Index': 'Index',
             'Series': 'Series'}
        ) is cv3
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Other Common Name',
             'Index': 'Other Index',
             'Series': None}
        ) is cv4
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Other Common Name',
             'Index': 'Other Index',
             'Series': 'Series'}
        ) is cv5
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Index': 'Index',
             'Series': 'Other Series'}
        ) is cv6
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Like, Other Name',
             'Common Name': 'Common Name',
             'Index': 'Index',
             'Series': 'Series'}
        ) is cv7


class TestCultivarRelatedEventHandlers:
    """Test event listener functions that involve Cultivar instances."""
    @mock.patch('app.seeds.models.Cultivar.generate_slug')
    def test_before_cultivar_insert_or_update_flush(self, m_gs, db):
        """Generate a slug for Cultivar before flushing to db."""
        m_gs.return_value = 'new-cultivar'
        cv = Cultivar(name='New Cultivar')
        db.session.add(cv)
        db.session.flush()
        assert m_gs.called
        assert cv.slug == 'new-cultivar'


class TestPacketWithDB:
    """Test methods for Packet that require db access."""
    def test_init_with_existing_quantity(self, db):
        """Set Packet.quantity to existing quantity if appropriate."""
        qty = Quantity(value='100', units='seeds')
        db.session.add(qty)
        db.session.commit()
        pkt = Packet(sku='8675309',
                     price=Decimal('3.50'),
                     quantity=100,
                     units='seeds')
        assert pkt.quantity is qty

    def test_init_with_new_quantity(self, db):
        """Create a new quantity if no existing quantity w/ given values."""
        pkt = Packet(sku='8675309',
                     price=Decimal('3.50'),
                     quantity=100,
                     units='seeds')
        db.session.add(pkt)
        db.session.commit()
        assert pkt.quantity is Quantity.query.first()

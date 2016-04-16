from unittest import mock
import pytest
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Cultivar,
    Index,
    Packet,
    Quantity,
    row_exists
)


class TestModuleLevelFunctionsWithDB:
    """Test module-level functions."""
    def test_row_exists(self, db):
        """True if row exists in db, False if not."""
        idx = Index(name='Finger')
        db.session.add(idx)
        db.session.commit()
        assert row_exists(Index.name, 'Finger')
        assert not row_exists(Index.name, 'Toe')


class TestIndexRelatedEventHandlers:
    """Test event listener functions that involve Index instances."""
    # before_index_insert_or_update
    @mock.patch('app.seeds.models.Index.generate_slug')
    def test_before_index_insert_or_update_slug(self, m_gs, db):
        """Set the slug of an instance of Index before flushing to db."""
        m_gs.return_value = 'new-index'
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.flush()
        assert m_gs.called
        assert idx.slug == 'new-index'

    @mock.patch('app.seeds.models.dbify')
    def test_before_index_insert_or_update_dbify(self, m_d, db):
        """dbify `Index.name` before flushing."""
        m_d.return_value = 'dbified-index'
        idx = Index(name='dirty-index')
        db.session.add(idx)
        db.session.flush()
        assert m_d.called_with('dirty-index')
        assert idx.name == 'dbified-index'

    # save_indexes_to_json_before_commit
    @mock.patch('app.seeds.models.Index.save_to_json_file')
    def test_save_indexes_json_before_commit_new_index(self, m_stjf, db):
        """Run Index.save_to_json_file() if any new Indexes in session."""
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.commit()
        assert m_stjf.call_count == 1

    @mock.patch('app.seeds.models.Index.save_to_json_file')
    def test_save_indexes_to_json_before_commit_edited_index(self,
                                                             m_stjf,
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
        assert m_stjf.call_count == 2

    @mock.patch('app.seeds.models.Index.save_to_json_file')
    def test_save_indexes_to_json_before_commit_deleted_index(self,
                                                              m_stjf,
                                                              db):
        """Run if any deleted Indexes are in the session."""
        idx = Index(name='New Index')
        db.session.add(idx)
        db.session.commit()
        db.session.expunge(idx)
        idxq = Index.query.filter(Index.name == 'New Index').one_or_none()
        db.session.delete(idxq)
        db.session.commit()
        assert m_stjf.call_count == 2

    @mock.patch('app.seeds.models.Index.save_to_json_file')
    def test_save_indexes_to_json_before_commit_no_indexes(self, m_stjf, db):
        """Do not run if there are no Indexes in the session."""
        cn = CommonName(name='John')
        db.session.add(cn)
        db.session.commit()
        assert not m_stjf.called


class TestIndexWithDB:
    """Test methods of `Index` which use the db."""
    def test_get_or_create_get(self, db):
        """Load Index if it exists."""
        idx = Index(name='Finger')
        db.session.add(idx)
        db.session.commit()
        assert Index.get_or_create(name='Finger') is idx
        assert not idx.created

    def test_get_or_create_create(self, db):
        """Create Index if it does not exist."""
        idx = Index.get_or_create(name='Finger')
        assert not row_exists(Index.name, 'Finger')
        assert idx.created


class TestCommonNameWithDB:
    """Test methods of CommonName which use the database."""
    def test_from_queryable_values(self, db):
        cn = CommonName(name='Butterfly Weed', index=Index(name='Annual'))
        db.session.add(cn)
        db.session.commit()
        assert CommonName.from_queryable_values(name='Butterfly Weed',
                                                index='Annual') is cn

    def test_get_or_create_get(self, db):
        cn = CommonName(name='Foxglove', index=Index(name='Perennial'))
        db.session.add(cn)
        db.session.commit()
        assert CommonName.get_or_create(name='Foxglove',
                                        index='Perennial') is cn
        assert not cn.created

    def test_get_or_create_create_with_existing_index(self, db):
        idx = Index(name='Perennial')
        db.session.add(idx)
        db.session.commit()
        cn = CommonName.get_or_create(name='Foxglove', index='Perennial')
        assert cn.created
        assert cn.index is idx
        assert not idx.created

    def test_get_or_create_create_all(self, db):
        cn = CommonName.get_or_create(name='Foxglove', index='Perennial')
        assert cn.created
        assert cn.index.created


class TestCommonNameRelatedEventHandlers:
    """Test event listener functions that involve CommonName instances."""
    @mock.patch('app.seeds.models.CommonName.generate_slug')
    def test_before_common_name_insert_or_update_slug(self, m_gs, db):
        """Set the slug for a CommonName instance before flush."""
        m_gs.return_value = 'new-common-name'
        cn = CommonName(name='New Common Name')
        db.session.add(cn)
        db.session.flush()
        assert m_gs.called
        assert cn.slug == 'new-common-name'

    @mock.patch('app.seeds.models.dbify')
    def test_before_common_name_insert_or_update_dbify(self, m_d, db):
        """dbify CommonName.name before flush."""
        m_d.return_value = 'dbified-name'
        cn = CommonName(name='dirty name')
        db.session.add(cn)
        db.session.flush()
        m_d.assert_called_with('dirty name')
        assert cn.name == 'dbified-name'


class TestBotanicalNameRelatedEventHandlers:
    """Test event listener functions that involve BotanicalName instances."""
    @mock.patch('app.seeds.models.BotanicalName.validate')
    def test_before_botanical_name_insert_or_update_validates(self, m_v, db):
        """Raise a ValueError if trying to flush an invalid BotanicalName."""
        m_v.return_value = False
        bn = BotanicalName(name='CAPSLOCK IS CRUISE CONTROL FOR COOL')
        db.session.add(bn)
        with pytest.raises(ValueError):
            db.session.flush()


class TestCultivarWithDB:
    """Test Cultivar model methods that require database access."""
    def test_from_queryable_values(self, db):
        """Return the correct Cultivar based on values given."""
        cn = CommonName(name='Foxglove', index=Index(name='Perennial'))
        cv = Cultivar(name='Polkadot Petra', common_name=cn)
        db.session.add(cv)
        db.session.commit()
        assert Cultivar.from_queryable_values(name='Polkadot Petra',
                                              common_name='Foxglove',
                                              index='Perennial') is cv


class TestCultivarRelatedEventHandlers:
    """Test event listener functions that involve Cultivar instances."""
    @mock.patch('app.seeds.models.Cultivar.generate_slug')
    def test_before_cultivar_insert_or_update_slug(self, m_gs, db):
        """Generate a slug for Cultivar before flushing to db."""
        m_gs.return_value = 'new-cultivar'
        cv = Cultivar(name='New Cultivar')
        db.session.add(cv)
        db.session.flush()
        assert m_gs.called
        assert cv.slug == 'new-cultivar'

    @mock.patch('app.seeds.models.dbify')
    def test_before_cultivar_insert_or_update_dbify(self, m_d, db):
        """dbify Cultivar.name before flush."""
        m_d.return_value = 'dbified-name'
        cv = Cultivar(name='dirty name')
        db.session.add(cv)
        db.session.flush()
        m_d.assert_called_with('dirty name')
        assert cv.name == 'dbified-name'


class TestPacketRelatedEventHandlers:
    """Test event handlers that operate on Packet data."""
    def test_delete_orphaned_quantity(self, db):
        """If a quantity has no packets, delete it."""
        qty1 = Quantity(value=100, units='seeds')
        qty2 = Quantity(value=50, units='seeds')
        pkt1 = Packet(sku='8675309', quantity=qty1)
        pkt2 = Packet(sku='202024', quantity=qty2)
        pkt3 = Packet(sku='5318008', quantity=qty2)
        db.session.add_all([pkt1, pkt2, pkt3])
        db.session.flush()
        pkt1.quantity = Quantity('99', 'luftballons')
        db.session.flush()
        assert qty1 not in Quantity.query.all()
        pkt2.quantity = Quantity('10000', 'maniacs')
        db.session.flush()
        assert qty2 in Quantity.query.all()
        pkt3.quantity = Quantity('500', 'miles')
        db.session.flush()
        assert qty2 not in Quantity.query.all()


class TestQuantityWithDB:
    """Test methods of Quantity that use the db."""
    def test_from_queryable_values(self, db):
        """Return a Quantity with the given value and units."""
        qty1 = Quantity(value='1/4', units='gram')
        qty2 = Quantity(value=0.25, units='gram')
        db.session.add_all([qty1, qty2])
        assert Quantity.from_queryable_values(value='1/4',
                                              units='gram') is qty1
        assert Quantity.from_queryable_values(value=0.25,
                                              units='gram') is qty2

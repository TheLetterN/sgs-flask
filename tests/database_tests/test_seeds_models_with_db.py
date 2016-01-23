from decimal import Decimal
from app.seeds.models import (
    BotanicalName,
    CommonName,
    Image,
    Cultivar,
    Packet,
    Quantity,
    Series
)
from tests.conftest import app, db  # noqa


class TestBotanicalNameWithDB:
    """Test BotanicalName model methods that require database access."""
    def test_name_is_queryable(self, db):
        """.name should be usable in queries."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        assert BotanicalName.query\
            .filter_by(name='Asclepias incarnata').first() is bn


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
        cn2 = CommonName(name='Other Common Name')
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
             'Series': None}
        ) is cv1
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Series': None}
        ) is cv2
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Series': 'Series'}
        ) is cv3
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Other Common Name',
             'Series': None}
        ) is cv4
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Other Common Name',
             'Series': 'Series'}
        ) is cv5
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Name',
             'Common Name': 'Common Name',
             'Series': 'Other Series'}
        ) is cv6
        assert Cultivar.from_lookup_dict(
            {'Cultivar Name': 'Like, Other Name',
             'Common Name': 'Common Name',
             'Series': 'Series'}
        ) is cv7

    def test_thumbnail_path_with_thumbnail(self, db):
        """Return path to thumbnail if it exists."""
        cultivar = Cultivar()
        thumb = Image()
        db.session.add_all([cultivar, thumb])
        cultivar.name = 'Foxy'
        thumb.filename = 'hello.jpg'
        cultivar.thumbnail = thumb
        db.session.commit()
        assert cultivar.thumbnail_path == 'images/hello.jpg'

    def test_thumbnail_path_no_thumbnail(self, db):
        """Return path to defaulth thumbnail if cultivar has none."""
        cultivar = Cultivar()
        db.session.add(cultivar)
        cultivar.name = 'Foxy'
        db.session.commit()
        assert cultivar.thumbnail_path == 'images/default_thumb.jpg'


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

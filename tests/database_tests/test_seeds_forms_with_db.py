import pytest
from decimal import Decimal
from unittest import mock
from werkzeug import FileStorage, secure_filename
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddIndexForm,
    AddCommonNameForm,
    AddPacketForm,
    AddCultivarForm,
    AddSeriesForm,
    botanical_name_select_list,
    index_select_list,
    common_name_select_list,
    EditBotanicalNameForm,
    EditIndexForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditPacketForm,
    EditSeriesForm,
    packet_select_list,
    cultivar_select_list,
    SelectBotanicalNameForm,
    SelectIndexForm,
    SelectCommonNameForm,
    SelectCultivarForm,
    SelectPacketForm,
    SelectSeriesForm
)
from app.seeds.models import (
    BotanicalName,
    Index,
    CommonName,
    Image,
    Packet,
    Quantity,
    Cultivar,
    Series
)


class TestFunctionsWithDB:
    """Test module-level methods with the database."""
    def test_botanical_name_select_list_no_obj(self, db):
        """Generate correct list of tuples from botanical names in db."""
        bn1 = BotanicalName()
        bn2 = BotanicalName()
        bn3 = BotanicalName()
        db.session.add_all([bn1, bn2, bn3])
        bn1.name = 'Asclepias incarnata'
        bn2.name = 'Echinacea purpurea'
        bn3.name = 'Innagada davida'
        db.session.commit()
        bnlist = botanical_name_select_list()
        assert (bn1.id, bn1.name) in bnlist
        assert (bn2.id, bn2.name) in bnlist
        assert (bn3.id, bn3.name) in bnlist

    def test_botanical_name_select_list_with_obj(self, db):
        """Generate list with indexes belonging to object."""
        bn1 = BotanicalName(name='Digitalis über alles')
        bn2 = BotanicalName(name='Innagada davida')
        bn3 = BotanicalName(name='Biggus dickus')
        db.session.add_all([bn1, bn2, bn3])
        obj = mock.MagicMock()
        obj.botanical_names = [bn1, bn2]
        db.session.commit()
        bnlist = botanical_name_select_list(obj)
        assert len(bnlist) == len(obj.botanical_names)
        assert (bn1.id, bn1.name) in bnlist
        assert (bn2.id, bn2.name) in bnlist
        assert (bn3.id, bn3.name) not in bnlist

    def test_index_select_list_no_obj(self, db):
        """Generate correct list of tuples from indexes in db."""
        idx1 = Index()
        idx2 = Index()
        idx3 = Index()
        db.session.add_all([idx1, idx2, idx3])
        idx1.name = 'Annual Flower'.title()
        idx2.name = 'Perennial Flower'.title()
        idx3.name = 'Vegetable'.title()
        db.session.commit()
        idxlist = index_select_list()
        assert (idx1.id, idx1.name) in idxlist
        assert (idx2.id, idx2.name) in idxlist
        assert (idx3.id, idx3.name) in idxlist

    def test_index_select_list_with_obj(self, db):
        """Generate list from indexes in obj."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        idx3 = Index(name='Herb')
        db.session.add_all([idx1, idx2, idx3])
        obj = mock.MagicMock()
        obj.indexes = [idx1, idx2]
        idxlist = index_select_list(obj)
        assert len(idxlist) == len(obj.indexes)
        assert (idx1.id, idx1.name) in idxlist
        assert (idx2.id, idx2.name) in idxlist
        assert (idx3.id, idx3.name) not in idxlist

    def test_common_name_select_list(self, db):
        """Generate correct list of tuples from common names in db."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        cnlist = common_name_select_list()
        assert (cn1.id, cn1.name) in cnlist
        assert (cn2.id, cn2.name) in cnlist
        assert (cn3.id, cn3.name) in cnlist

    def test_packet_select_list(self, db):
        """Generate list of tuples from packets in database."""
        pkt1 = Packet()
        pkt2 = Packet()
        pkt3 = Packet()
        cv1 = Cultivar()
        cv2 = Cultivar()
        cv3 = Cultivar()
        cn1 = CommonName()
        cn2 = CommonName()
        db.session.add_all([pkt1, pkt2, pkt3, cv1, cv2, cv3, cn1, cn2])
        pkt1.price = Decimal('1.99')
        pkt2.price = Decimal('2.99')
        pkt3.price = Decimal('3.99')
        pkt1.quantity = Quantity(value=100, units='seeds')
        pkt2.quantity = Quantity(value=200, units='seeds')
        pkt3.quantity = Quantity(value=50, units='seeds')
        pkt1.sku = 'F41'
        pkt2.sku = 'F42'
        pkt3.sku = 'B13'
        cv1.name = 'Foxy'
        cv2.name = 'Snow Thimble'
        cv3.name = 'Soulmate'
        cn1.name = 'Foxglove'
        cn2.name = 'Butterfly Weed'
        cv1.common_name = cn1
        cv2.common_name = cn1
        cv3.common_name = cn2
        cv1.packets.append(pkt1)
        cv2.packets.append(pkt2)
        cv3.packets.append(pkt3)
        db.session.commit()
        pktlst = packet_select_list()
        expected = [(pkt3.id,
                     'Butterfly Weed, Soulmate: SKU #B13: $3.99 for 50 seeds'),
                    (pkt1.id,
                     'Foxglove, Foxy: SKU #F41: $1.99 for 100 seeds'),
                    (pkt2.id,
                     'Foxglove, Snow Thimble: SKU #F42: $2.99 for 200 seeds')]
        assert pktlst == expected

    def test_cultivar_select_list(self, db):
        """Generate correct list of tuples from cultivars in db."""
        idx = Index(name='Perennial')
        cv1 = Cultivar(name='Foxy')
        cv1.common_name = CommonName(name='Foxglove')
        cv1.common_name.index = idx
        cv2 = Cultivar(name='Soulmate')
        cv2.common_name = CommonName(name='Butterfly Weed')
        cv2.common_name.index = idx
        cv3 = Cultivar(name='New York')
        cv3.common_name = CommonName(name='Aster')
        cv3.common_name.index = idx
        db.session.add_all([idx, cv1, cv2, cv3])
        db.session.commit()
        cultivarlist = cultivar_select_list()
        assert (cv1.id, cv1.fullname) in cultivarlist
        assert (cv2.id, cv2.fullname) in cultivarlist
        assert (cv3.id, cv3.fullname) in cultivarlist


class TestAddBotanicalNameFormWithDB:
    """Test custom methods of AddBotanicalNameForm."""
    def test_validate_name(self, db):
        """Raise error if name in DB or invalid botanical name."""
        bn = BotanicalName()
        bn2 = BotanicalName()
        cn = CommonName()
        db.session.add_all([bn, bn2, cn])
        cn.name = 'Butterfly Weed'
        bn.name = 'Asclepias incarnata'
        bn2.name = 'Canis lupus familiaris'
        bn.common_names.append(cn)
        bn2.common_names.append(cn)
        db.session.commit()
        form = AddBotanicalNameForm()
        form.cn = cn
        form.name.data = 'Innagada davida'
        form.validate_name(form.name)
        form.name.data = 'Title Case is not a binomen'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Asclepias incarnata'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddIndexFormWithDB:
    """Test custom methods of AddIndexForm."""
    def test_validate_index(self, db):
        """Raise a ValidationError if index already in db."""
        index = Index()
        db.session.add(index)
        index.name = 'Annual Flowers'
        db.session.commit()
        form = AddIndexForm()
        form.index.data = 'Perennial Flowers'
        form.validate_index(form.index)
        form.index.data = 'annual flowers'
        with pytest.raises(ValidationError):
            form.validate_index(form.index)


class TestAddCommonNameFormWithDB:
    """Test custom methods of AddCommonNameForm."""
    def test_set_selects(self, db):
        """Set .indexes.choices with Categories from the db."""
        idx = Index()
        cn1 = CommonName()
        cn2 = CommonName()
        cv1 = Cultivar()
        cv2 = Cultivar()
        db.session.add_all([idx, cn1, cn2, cv1, cv2])
        idx.name = 'Perennial Flower'.title()
        cn1.name = 'Foxglove'
        cn1.index = idx
        cn2.name = 'Butterfly Weed'
        cn2.index = idx
        cv1.name = 'Foxy'
        cv1.common_name = cn1
        cv2.name = 'Soulmate'
        cv2.common_name = cn2
        db.session.commit()
        form = AddCommonNameForm()
        form.set_selects()
        assert (cn1.id, 'Foxglove (Perennial Flower)') in\
            form.gw_common_names.choices
        assert (cn2.id, 'Butterfly Weed (Perennial Flower)') in\
            form.gw_common_names.choices
        assert (cv1.id, cv1.fullname) in form.gw_cultivars.choices
        assert (cv2.id, cv2.fullname) in form.gw_cultivars.choices

    def test_validate_name(self, db):
        """Raise a Validation error if CommonName & Index combo in db."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        db.session.add(cn)
        db.session.commit()
        form = AddCommonNameForm()
        form.name.data = 'Foxglove'
        form.idx_id = cn.index.id
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddPacketFormWithDB:
    """Test custom methods of AddPacketForm."""
    def test_validate_sku(self, db):
        """Raise ValidationError if SKU already exists in db."""
        packet = Packet()
        cultivar = Cultivar()
        db.session.add_all([packet, cultivar])
        packet.sku = '8675309'
        cultivar.name = 'Jenny'
        packet.cultivar = cultivar
        db.session.commit()
        form = AddPacketForm()
        form.sku.data = '8675309'
        with pytest.raises(ValidationError):
            form.validate_sku(form.sku)


class TestAddCultivarFormWithDB:
    """Test custom methods of AddCultivarForm."""
    def test_set_selects(self, db):
        """Selects should be set from database."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        form = AddCultivarForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_name.choices

    def test_validate_name(self, db):
        """Raise error if cultivar already exists.

        Cultivars are constrained to have a unique combination of name, common
            name, and series.
        """
        cv1 = Cultivar(name='Petra')
        cv1.common_name = CommonName(name='Foxglove')
        cv1.common_name.index = Index(name='Perennial')
        cv1.series = Series(name='Polkadot')
        cv2 = Cultivar(name='Silky Gold')
        cv2.common_name = CommonName(name='Butterfly Weed')
        cv2.common_name.index = Index(name='Annual')
        cv3 = Cultivar(name='Tumbling Tom')
        db.session.add_all([cv1, cv2, cv3])
        db.session.commit()
        form1 = AddCultivarForm()
        form1.cn_id = cv1.common_name.id
        form1.name.data = 'Petra'
        form1.validate_name(form1.name)
        form1.series.data = cv1.series.id
        with pytest.raises(ValidationError):
            form1.validate_name(form1.name)
        form2 = AddCultivarForm()
        form2.cn_id = cv2.common_name.id
        form2.name.data = 'Silky Gold'
        with pytest.raises(ValidationError):
            form2.validate_name(form2.name)
        form3 = AddCultivarForm()
        form3.name.data = 'Tumbling Tom'
        with pytest.raises(ValidationError):
            form3.validate_name(form3.name)

    def test_validate_thumbnail(self, db):
        "Raise ValidationError if image already exists with same filename."""
        image = Image()
        db.session.add(image)
        image.filename = secure_filename('frogfacts.png')
        db.session.commit()
        form = AddCultivarForm()
        form.thumbnail.data = FileStorage()
        form.thumbnail.data.filename = 'frogfacts.png'
        with pytest.raises(ValidationError):
            form.validate_thumbnail(form.thumbnail)


class TestAddSeriesForm:
    """Test custom methods of AddSeriesForm."""
    def test_validate_name(self, db):
        series = Series()
        cn = CommonName(name='Foxglove')
        series.common_name = cn
        series.name = 'Polkadot'
        db.session.add(series, cn)
        db.session.commit()
        form = AddSeriesForm()
        form.cn = cn
        form.name.data = 'Dalmatian'
        form.validate_name(form.name)
        form.name.data = 'Polkadot'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestEditBotanicalNameFormWithDB:
    """Test custom methods of EditBotanicalNameForm."""
    def test_set_common_names(self, db):
        """Set common_names.choices with CommonNames from db."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        form = EditBotanicalNameForm()
        form.set_common_names()
        assert (cn1.id, cn1.name) in form.common_names.choices
        assert (cn2.id, cn2.name) in form.common_names.choices
        assert (cn3.id, cn3.name) in form.common_names.choices


class TestEditCommonNameFormWithDB:
    """Test custom methods of EditCommonNameForm."""
    def test_set_selects(self, db):
        """Set selects with data from the db."""
        idx1 = Index()
        idx2 = Index()
        cn1 = CommonName()
        cn2 = CommonName()
        cv1 = Cultivar()
        cv2 = Cultivar()
        db.session.add_all([idx1, idx2, cn1, cn2, cv1, cv2])
        idx1.name = 'Annual Flower'
        idx2.name = 'Perennial Flower'
        cn1.name = 'Foxglove'
        cn1.index = idx2
        cn2.name = 'Butterfly Weed'
        cn2.index = idx1
        cv1.name = 'Foxy'
        cv1.common_name = cn1
        cv2.name = 'Soulmate'
        cv2.common_name = cn2
        db.session.commit()
        form = EditCommonNameForm()
        form.set_selects()
        assert (cn1.id, 'Foxglove (Perennial Flower)') in\
            form.gw_common_names.choices
        assert (cn2.id, 'Butterfly Weed (Annual Flower)') in\
            form.gw_common_names.choices
        assert (cv1.id, cv1.fullname) in form.gw_cultivars.choices
        assert (cv2.id, cv2.fullname) in form.gw_cultivars.choices
        assert (cn1.id, 'Foxglove (Perennial Flower)') in\
            form.parent_cn.choices
        assert (cn2.id, 'Butterfly Weed (Annual Flower)') in\
            form.parent_cn.choices


class TestEditIndexFormWithDB:
    """Test custom methods of EditIndexForm."""
    def test_populate(self, db):
        """Populate form from a Index object."""
        index = Index()
        db.session.add(index)
        index.name = 'Annual Flowers'
        index.description = 'Not really built to last.'
        db.session.commit()
        form = EditIndexForm()
        form.populate(index)
        assert form.name.data == index.name
        assert form.description.data == index.description


class TestEditCultivarFormWithDB:
    """Test custom methods of EditCultivarForm."""
    def test_set_selects(self, db):
        """Set selects with values loaded from database."""
        bn = BotanicalName()
        cn = CommonName()
        idx = Index()
        db.session.add_all([bn, cn, idx])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Foxy'
        db.session.commit()
        form = EditCultivarForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_name.choices
        assert (cn.id, cn.name) in form.common_name.choices


class TestEditPacketFormWithDB:
    """Test custom methods of EditPacketForm."""
    def test_populate(self, db):
        """Populate form with info from database."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.price = Decimal('2.99')
        pkt.quantity = Quantity(value=100, units='seeds')
        pkt.sku = '8675309'
        db.session.commit()
        form = EditPacketForm()
        form.populate(pkt)
        assert form.price.data == pkt.price
        assert form.units.data == pkt.quantity.units
        assert form.quantity.data == pkt.quantity.value
        assert form.sku.data == pkt.sku

    def test_validate_quantity(self, db):
        """Raise a ValidationError if field.data can't be used as quantity."""
        form = EditPacketForm()
        form.quantity.data = 'Forty-two'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)


class TestEditSeriesFormWithDB:
    """Test custom methods of EditSeriesForm."""
    def test_set_common_name(self, db):
        """Populate common_name select with ids from database."""
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Butterfly Weed')
        cn3 = CommonName(name='Tomato')
        db.session.add_all([cn1, cn2, cn3])
        db.session.commit()
        form = EditSeriesForm()
        form.set_common_name()
        assert (cn1.id, cn1.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices
        assert (cn3.id, cn3.name) in form.common_name.choices


class TestSelectBotanicalFormWithDB:
    """Test custom methods of SelectBotanicalNameForm."""
    def test_set_names(self, db):
        """Set .names.choices with BotanicalNames from db."""
        bn1 = BotanicalName()
        bn2 = BotanicalName()
        bn3 = BotanicalName()
        db.session.add_all([bn1, bn2, bn3])
        bn1.name = 'Asclepias incarnata'
        bn2.name = 'Echinacea purpurea'
        bn3.name = 'Innagada davida'
        db.session.commit()
        form = SelectBotanicalNameForm()
        form.set_botanical_name()
        assert (bn1.id, bn1.name) in form.botanical_name.choices
        assert (bn2.id, bn2.name) in form.botanical_name.choices
        assert (bn3.id, bn3.name) in form.botanical_name.choices


class TestSelectIndexFormWithDB:
    """Test custom methods of SelectIndexForm."""
    def test_set_indexes(self, db):
        """Load all indexes from database into select field."""
        idx1 = Index()
        idx2 = Index()
        idx3 = Index()
        db.session.add_all([idx1, idx2, idx3])
        idx1.name = 'Perennial Flowers'
        idx2.name = 'Annual Flowers'
        idx3.name = 'Vegetables'
        db.session.commit()
        form = SelectIndexForm()
        form.set_index()
        assert (idx1.id, idx1.name) in form.index.choices
        assert (idx2.id, idx2.name) in form.index.choices
        assert (idx3.id, idx3.name) in form.index.choices


class TestSelectCommonNameFormWithDB:
    """Test custom methods of SelectCommonNameForm."""
    def test_set_names(self, db):
        """Load all common names from database into select field."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Zinnia'
        cn3.name = 'Sunflower'
        db.session.commit()
        form = SelectCommonNameForm()
        form.set_common_name()
        assert (cn1.id, cn1.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices
        assert (cn3.id, cn3.name) in form.common_name.choices


class TestSelectCultivarFormWithDB:
    """Test custom methods of SelectCultivarForm."""
    def test_set_cultivar(self, db):
        """Set select with cultivars loaded from database.
        """
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Vegetable')
        cv1 = Cultivar()
        cv2 = Cultivar()
        cv3 = Cultivar()
        db.session.add_all([cv1, cv2, cv3])
        cv1.name = 'Soulmate'
        cv1.common_name = CommonName(name='Butterfly Weed')
        cv1.common_name.index = idx1
        cv2.name = 'Tumbling Tom'
        cv2.common_name = CommonName(name='Tomato')
        cv2.common_name.index = idx2
        cv3.name = 'Foxy'
        cv3.common_name = CommonName(name='Foxglove')
        cv3.common_name.idnex = idx1
        db.session.commit()
        form = SelectCultivarForm()
        form.set_cultivar()
        assert (cv1.id, cv1.fullname) in form.cultivar.choices
        assert (cv2.id, cv2.fullname) in form.cultivar.choices
        assert (cv3.id, cv3.fullname) in form.cultivar.choices


class TestSelectPacketFormWithDB:
    """Test custom methods of SelectPacketForm."""
    def test_set_packet(self, db):
        """Set select with packets loaded from database."""
        cultivar = Cultivar()
        cn = CommonName()
        packet = Packet()
        db.session.add_all([cultivar, cn, packet])
        cultivar.name = 'Foxy'
        cn.name = 'Foxglove'
        packet.price = Decimal('2.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        cultivar.common_name = cn
        cultivar.packets.append(packet)
        db.session.commit()
        form = SelectPacketForm()
        form.set_packet()
        assert (packet.id,
                'Foxglove, Foxy: SKU #8675309: $2.99 for 100 seeds') in\
            form.packet.choices


class TestSelectSeriesFormWithDB:
    """Test custom methods of SelectSeriesForm."""
    def test_set_series(self, db):
        """Populate series with choices from database."""
        s1 = Series(name='Dalmatian')
        s1.common_name = CommonName(name='Dog')
        s2 = Series(name='Polkadot')
        s2.common_name = CommonName(name='Underpants')
        s3 = Series(name='World')
        s3.common_name = CommonName(name='Wayne\'s')
        db.session.add_all([s1, s2, s3])
        form = SelectSeriesForm()
        form.set_series()
        assert s1.id, 'Dog, Dalmatian' in form.series.choices
        assert s2.id, 'Underpants, Polkadot' in form.series.choices
        assert s3.id, 'Wayne\'s, World' in form.series.choices

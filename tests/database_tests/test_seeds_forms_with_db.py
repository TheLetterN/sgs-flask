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
    EditBotanicalNameForm,
    EditIndexForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditPacketForm,
    EditSeriesForm,
    select_field_choices,
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
    def test_select_field_choices_with_model_by_id(self, db):
        """Generate tuple list from queried items ordered by id."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        idx3 = Index(name='Rock')
        idx1.id = 1
        idx2.id = 2
        idx3.id = 3
        db.session.add_all([idx1, idx2, idx3])
        db.session.flush()
        stls = select_field_choices(model=Index,
                                    title_attribute='name',
                                    order_by='id')
        assert stls == [(1, 'Perennial'), (2, 'Annual'), (3, 'Rock')]

    def test_select_field_choices_with_model_by_name(self, db):
        """Generate tuple list from queried items ordered by name."""
        idx1 = Index(name='Perennial')
        idx2 = Index(name='Annual')
        idx3 = Index(name='Rock')
        idx1.id = 1
        idx2.id = 2
        idx3.id = 3
        db.session.add_all([idx1, idx2, idx3])
        db.session.flush()
        stls = select_field_choices(model=Index,
                                    title_attribute='name',
                                    order_by='name')
        assert stls == [(2, 'Annual'), (1, 'Perennial'), (3, 'Rock')]


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
        form.name.data = 'McDuck is not a valid genus'
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

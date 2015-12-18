import pytest
from decimal import Decimal
from werkzeug import FileStorage, secure_filename
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddCategoryForm,
    AddCommonNameForm,
    AddPacketForm,
    AddCultivarForm,
    AddSeriesForm,
    botanical_name_select_list,
    category_select_list,
    common_name_select_list,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditPacketForm,
    EditSeriesForm,
    packet_select_list,
    cultivar_select_list,
    syn_parents_links,
    SelectBotanicalNameForm,
    SelectCategoryForm,
    SelectCommonNameForm,
    SelectCultivarForm,
    SelectPacketForm,
    SelectSeriesForm
)
from app.seeds.models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Packet,
    Quantity,
    Cultivar,
    Series
)
from tests.conftest import app, db  # noqa


class TestFunctionsWithDB:
    """Test module-level methods with the database."""
    def test_botanical_name_select_list(self, db):
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

    def test_category_select_list(self, db):
        """Generate correct list of tuples from categories in db."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.name = 'Annual Flower'.title()
        cat2.name = 'Perennial Flower'.title()
        cat3.name = 'Vegetable'.title()
        db.session.commit()
        catlist = category_select_list()
        assert (cat1.id, cat1.name) in catlist
        assert (cat2.id, cat2.name) in catlist
        assert (cat3.id, cat3.name) in catlist

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
        cv1 = Cultivar()
        cv2 = Cultivar()
        cv3 = Cultivar()
        db.session.add_all([cv1, cv2, cv3])
        cv1.name = 'Soulmate'
        cv2.name = 'Superfine Rainbow'
        cv3.name = 'Tumbling Tom'
        db.session.commit()
        cultivarlist = cultivar_select_list()
        assert (cv1.id, cv1.name) in cultivarlist
        assert (cv2.id, cv2.name) in cultivarlist
        assert (cv3.id, cv3.name) in cultivarlist

    def test_syn_parents_links(self, db):
        """Generate list of links to parents of synonyms."""
        bn1 = BotanicalName()
        bn2 = BotanicalName()
        bn3 = BotanicalName()
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        cv1 = Cultivar()
        cv2 = Cultivar()
        cv3 = Cultivar()
        db.session.add_all([bn1, bn2, bn3, cn1, cn2, cn3, cv1, cv2, cv3])
        bn1.name = 'Digitalis purpurea'
        bn2.name = 'Asclepias incarnata'
        bn3.name = 'Innagada davida'
        cn1.name = 'Foxglove'
        cn2.name = 'Butterfly Weed'
        cn3.name = 'Smith'
        cv1.name = 'Foxy'
        cv1.common_name = cn1
        cv2.name = 'Soulmate'
        cv2.common_name = cn2
        cv3.name = 'John'
        cv3.common_name = cn3
        bn1.syn_parents.append(bn2)
        bn1.syn_parents.append(bn3)
        cn1.syn_parents.append(cn2)
        cn1.syn_parents.append(cn3)
        cv1.syn_parents.append(cv2)
        cv1.syn_parents.append(cv3)
        db.session.commit()
        rv = syn_parents_links(bn1)
        assert bn2.name in rv
        assert bn3.name in rv
        rv = syn_parents_links(cn1)
        assert cn2.name in rv
        assert cn3.name in rv
        rv = syn_parents_links(cv1)
        assert cv2.name in rv
        assert cv3.name in rv
        foo = 'woof'
        rv = syn_parents_links(foo)
        assert rv == ''


class TestAddBotanicalNameFormWithDB:
    """Test custom methods of AddBotanicalNameForm."""
    def test_set_common_name(self, db):
        """Set .common_name.choices with all common names from db."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        form = AddBotanicalNameForm()
        form.set_common_name()
        assert (cn1.id, cn1.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices

    def test_validate_name(self, db):
        """Raise error if name in DB or invalid botanical name."""
        bn = BotanicalName()
        bn2 = BotanicalName()
        bn3 = BotanicalName()
        cn = CommonName()
        db.session.add_all([bn, bn2, bn3, cn])
        cn.name = 'Butterfly Weed'
        bn.name = 'Asclepias incarnata'
        bn2.name = 'Canis lupus familiaris'
        bn3.name = 'Canis familiaris'
        bn3.syn_only = True
        bn2.synonyms.append(bn3)
        bn.common_name = cn
        bn2.common_name = cn
        db.session.commit()
        form = AddBotanicalNameForm()
        form.name.data = 'Innagada davida'
        form.validate_name(form.name)
        form.name.data = 'Title Case is not a binomen'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Asclepias incarnata'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Canis familiaris'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddCategoryFormWithDB:
    """Test custom methods of AddCategoryForm."""
    def test_validate_category(self, db):
        """Raise a ValidationError if category already in db."""
        category = Category()
        db.session.add(category)
        category.name = 'Annual Flowers'
        db.session.commit()
        form = AddCategoryForm()
        form.category.data = 'Perennial Flowers'
        form.validate_category(form.category)
        form.category.data = 'annual flowers'
        with pytest.raises(ValidationError):
            form.validate_category(form.category)


class TestAddCommonNameFormWithDB:
    """Test custom methods of AddCommonNameForm."""
    def test_set_selects(self, db):
        """Set .categories.choices with Categories from the db."""
        cat1 = Category()
        cat2 = Category()
        cn1 = CommonName()
        cn2 = CommonName()
        cv1 = Cultivar()
        cv2 = Cultivar()
        db.session.add_all([cat1, cat2, cn1, cn2, cv1, cv2])
        cat1.name = 'Annual Flower'.title()
        cat2.name = 'Perennial Flower'.title()
        cn1.name = 'Foxglove'
        cn2.name = 'Butterfly Weed'
        cv1.name = 'Foxy'
        cv2.name = 'Soulmate'
        db.session.commit()
        form = AddCommonNameForm()
        form.set_selects()
        assert (cat1.id, cat1.name) in form.categories.choices
        assert (cat2.id, cat2.name) in form.categories.choices
        assert (cn1.id, cn1.name) in form.gw_common_names.choices
        assert (cn2.id, cn2.name) in form.gw_common_names.choices
        assert (cv1.id, cv1.name) in form.gw_cultivars.choices
        assert (cv2.id, cv2.name) in form.gw_cultivars.choices

    def test_validate_name(self, db):
        """Raise a Validation error if common name already in db."""
        cn = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn, cn2, cn3])
        cn.name = 'Coleus'
        cn2.name = 'Foxglove'
        cn3.name = 'Digitalis'
        cn3.syn_only = True
        cn2.synonyms.append(cn3)
        db.session.commit()
        form = AddCommonNameForm()
        form.name.data = 'Sunflower'
        form.validate_name(form.name)
        form.name.data = 'Coleus'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Digitalis'
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
        cat = Category()
        cn = CommonName()
        db.session.add_all([bn, cat, cn])
        bn.name = 'Asclepias incarnata'
        cat.name = 'Perennial Flower'
        cn.name = 'Butterfly Weed'
        db.session.commit()
        form = AddCultivarForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_name.choices
        assert (cat.id, cat.name) in form.categories.choices
        assert (cn.id, cn.name) in form.common_name.choices

    def test_validate_categories(self, db):
        """Raise validation error if any categories not in common name."""
        cn = CommonName()
        cat1 = Category()
        cat2 = Category()
        db.session.add_all([cn, cat1, cat2])
        cn.name = 'Foxglove'
        cat1.name = 'Perennial Flower'
        cat2.name = 'Rock'
        cn.categories.append(cat1)
        db.session.commit()
        form = AddCultivarForm()
        form.common_name.data = cn.id
        form.categories.data = [cat1.id]
        form.validate_categories(form.categories)
        form.categories.data = [cat1.id, cat2.id]
        with pytest.raises(ValidationError):
            form.validate_categories(form.categories)

    def test_validate_name(self, db):
        """Raise error if name is already in the database."""
        cultivar = Cultivar()
        cn = CommonName()
        cv2 = Cultivar()
        cv3 = Cultivar()
        db.session.add_all([cn, cultivar, cv2, cv3])
        cultivar.name = 'Soulmate'
        cv2.name = 'Foxy'
        cv3.name = 'Lady'
        cv3.syn_only = True
        cv2.synonyms.append(cv3)
        cn.name = 'Butterfly Weed'
        cv2.common_name = cn
        cultivar.common_name = cn
        db.session.commit()
        form = AddCultivarForm()
        form.name.data = 'Soulmate'
        form.common_name.data = cn.id
        with pytest.raises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Lady'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)

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
    def test_set_common_name(self, db):
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        form = AddSeriesForm()
        form.set_common_name()
        assert (cn1.id, cn1.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices
        assert (cn3.id, cn3.name) in form.common_name.choices

    def test_validate_name(self, db):
        series = Series()
        series.name = 'Polkadot'
        db.session.add(series)
        db.session.commit()
        form = AddSeriesForm()
        form.name.data = 'Dalmatian'
        form.validate_name(form.name)
        form.name.data = 'Polkadot'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestEditBotanicalNameFormWithDB:
    """Test custom methods of EditBotanicalNameForm."""
    def test_set_common_name(self, db):
        """Set common_name.choices with CommonNames from db."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        form = EditBotanicalNameForm()
        form.set_common_name()
        assert (cn1.id, cn1.name) in form.common_name.choices
        assert (cn2.id, cn2.name) in form.common_name.choices
        assert (cn3.id, cn3.name) in form.common_name.choices


class TestEditCommonNameFormWithDB:
    """Test custom methods of EditCommonNameForm."""
    def test_set_selects(self, db):
        """Set selects with data from the db."""
        cat1 = Category()
        cat2 = Category()
        cn1 = CommonName()
        cn2 = CommonName()
        cv1 = Cultivar()
        cv2 = Cultivar()
        db.session.add_all([cat1, cat2, cn1, cn2, cv1, cv2])
        cat1.name = 'Annual Flower'.title()
        cat2.name = 'Perennial Flower'.title()
        cn1.name = 'Foxglove'
        cn2.name = 'Butterfly Weed'
        cv1.name = 'Foxy'
        cv2.name = 'Soulmate'
        db.session.commit()
        form = EditCommonNameForm()
        form.set_selects()
        assert (cat1.id, cat1.name) in form.categories.choices
        assert (cat2.id, cat2.name) in form.categories.choices
        assert (cn1.id, cn1.name) in form.gw_common_names.choices
        assert (cn2.id, cn2.name) in form.gw_common_names.choices
        assert (cv1.id, cv1.name) in form.gw_cultivars.choices
        assert (cv2.id, cv2.name) in form.gw_cultivars.choices
        assert (cn1.id, cn1.name) in form.parent_cn.choices
        assert (cn2.id, cn2.name) in form.parent_cn.choices


class TestEditCategoryFormWithDB:
    """Test custom methods of EditCategoryForm."""
    def test_populate(self, db):
        """Populate form from a Category object."""
        category = Category()
        db.session.add(category)
        category.name = 'Annual Flowers'
        category.description = 'Not really built to last.'
        db.session.commit()
        form = EditCategoryForm()
        form.populate(category)
        assert form.category.data == category.name
        assert form.description.data == category.description


class TestEditCultivarFormWithDB:
    """Test custom methods of EditCultivarForm."""
    def test_set_selects(self, db):
        """Set selects with values loaded from database."""
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Foxy'
        db.session.commit()
        form = EditCultivarForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_name.choices
        assert (cn.id, cn.name) in form.common_name.choices
        assert (cat.id, cat.name) in form.categories.choices

    def test_validate_categories(self, db):
        """Raise ValidationError if categories not in selected CommonName."""
        cat1 = Category(name='Perennial Flower')
        cat2 = Category(name='Annual Flower')
        cn = CommonName(name='Foxglove')
        db.session.add_all([cat1, cat2, cn])
        cn.categories.append(cat1)
        db.session.commit()
        form = EditCultivarForm()
        form.common_name.data = cn.id
        form.categories.data = [cat1.id]
        form.validate_categories(form.categories)
        form.categories.data.append(cat2.id)
        with pytest.raises(ValidationError):
            form.validate_categories(form.categories)


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


class TestSelectCategoryFormWithDB:
    """Test custom methods of SelectCategoryForm."""
    def test_set_categories(self, db):
        """Load all categories from database into select field."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.name = 'Perennial Flowers'
        cat2.name = 'Annual Flowers'
        cat3.name = 'Vegetables'
        db.session.commit()
        form = SelectCategoryForm()
        form.set_category()
        assert (cat1.id, cat1.name) in form.category.choices
        assert (cat2.id, cat2.name) in form.category.choices
        assert (cat3.id, cat3.name) in form.category.choices


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
        """Set select with cultivars loaded from database."""
        cv1 = Cultivar()
        cv2 = Cultivar()
        cv3 = Cultivar()
        db.session.add_all([cv1, cv2, cv3])
        cv1.name = 'Soulmate'
        cv2.name = 'Tumbling Tom'
        cv2.name = 'Foxy'
        db.session.commit()
        form = SelectCultivarForm()
        form.set_cultivar()
        assert (cv1.id, cv1.name) in form.cultivar.choices
        assert (cv2.id, cv2.name) in form.cultivar.choices
        assert (cv3.id, cv3.name) in form.cultivar.choices


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
        s2 = Series(name='Polkadot')
        s3 = Series(name='World')
        db.session.add_all([s1, s2, s3])
        form = SelectSeriesForm()
        form.set_series()
        assert (s1.id, s1.name) in form.series.choices
        assert (s2.id, s2.name) in form.series.choices
        assert (s3.id, s3.name) in form.series.choices

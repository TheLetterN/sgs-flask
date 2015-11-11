import pytest
from decimal import Decimal
from fractions import Fraction
from werkzeug import FileStorage, secure_filename
from wtforms import ValidationError
from app.seeds.forms import (
    AddBotanicalNameForm,
    AddCategoryForm,
    AddCommonNameForm,
    AddPacketForm,
    AddSeedForm,
    botanical_name_select_list,
    category_select_list,
    common_name_select_list,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    EditPacketForm,
    EditSeedForm,
    packet_select_list,
    seed_select_list,
    SelectBotanicalNameForm,
    SelectCategoryForm,
    SelectCommonNameForm,
    SelectPacketForm,
    SelectSeedForm
)
from app.seeds.models import (
    BotanicalName,
    Category,
    CommonName,
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
        cat1.category = 'Annual Flower'.title()
        cat2.category = 'Perennial Flower'.title()
        cat3.category = 'Vegetable'.title()
        db.session.commit()
        catlist = category_select_list()
        assert (cat1.id, cat1.category) in catlist
        assert (cat2.id, cat2.category) in catlist
        assert (cat3.id, cat3.category) in catlist

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
        sd1 = Seed()
        sd2 = Seed()
        sd3 = Seed()
        cn1 = CommonName()
        cn2 = CommonName()
        db.session.add_all([pkt1, pkt2, pkt3, sd1, sd2, sd3, cn1, cn2])
        pkt1.price = Decimal('1.99')
        pkt2.price = Decimal('2.99')
        pkt3.price = Decimal('3.99')
        pkt1.quantity = 100
        pkt2.quantity = 200
        pkt3.quantity = 50
        pkt1.unit = 'seeds'
        pkt2.unit = 'seeds'
        pkt3.unit = 'seeds'
        pkt1.sku = 'F41'
        pkt2.sku = 'F42'
        pkt3.sku = 'B13'
        sd1.name = 'Foxy'
        sd2.name = 'Snow Thimble'
        sd3.name = 'Soulmate'
        cn1.name = 'Foxglove'
        cn2.name = 'Butterfly Weed'
        sd1.common_name = cn1
        sd2.common_name = cn1
        sd3.common_name = cn2
        sd1.packets.append(pkt1)
        sd2.packets.append(pkt2)
        sd3.packets.append(pkt3)
        db.session.commit()
        pktlst = packet_select_list()
        expected = [(pkt3.id,
                     'Butterfly Weed, Soulmate -'
                     ' SKU B13: $3.99 for 50 seeds'),
                    (pkt1.id,
                     'Foxglove, Foxy - SKU F41: $1.99 for 100 seeds'),
                    (pkt2.id,
                     'Foxglove, Snow Thimble - SKU F42: $2.99 for 200 seeds')]
        assert pktlst == expected

    def test_seed_select_list(self, db):
        """Generate correct list of tuples from seeds in db."""
        sd1 = Seed()
        sd2 = Seed()
        sd3 = Seed()
        db.session.add_all([sd1, sd2, sd3])
        sd1.name = 'Soulmate'
        sd2.name = 'Superfine Rainbow'
        sd3.name = 'Tumbling Tom'
        db.session.commit()
        seedlist = seed_select_list()
        assert (sd1.id, sd1.name) in seedlist
        assert (sd2.id, sd2.name) in seedlist
        assert (sd3.id, sd3.name) in seedlist


class TestAddBotanicalNameFormWithDB:
    """Test custom methods of AddBotanicalNameForm."""
    def test_set_common_names(self, db):
        """Set .common_names.choices with all common names from db."""
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        db.session.add_all([cn1, cn2, cn3])
        cn1.name = 'Coleus'
        cn2.name = 'Sunflower'
        cn3.name = 'Zinnia'
        db.session.commit()
        form = AddBotanicalNameForm()
        form.set_common_names()
        assert (cn1.id, cn1.name) in form.common_names.choices
        assert (cn2.id, cn2.name) in form.common_names.choices
        assert (cn2.id, cn2.name) in form.common_names.choices

    def test_validate_name(self, db):
        """Raise error if name in DB or invalid botanical name."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
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


class TestAddCategoryFormWithDB:
    """Test custom methods of AddCategoryForm."""
    def test_validate_category(self, db):
        """Raise a ValidationError if category already in db."""
        category = Category()
        db.session.add(category)
        category.category = 'Annual Flowers'
        db.session.commit()
        form = AddCategoryForm()
        form.category.data = 'Perennial Flowers'
        form.validate_category(form.category)
        form.category.data = 'annual flowers'
        with pytest.raises(ValidationError):
            form.validate_category(form.category)


class TestAddCommonNameFormWithDB:
    """Test custom methods of AddCommonNameForm."""
    def test_set_categories(self, db):
        """Set .categories.choices with Categories from the db."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.category = 'Annual Flower'.title()
        cat2.category = 'Perennial Flower'.title()
        cat3.category = 'Vegetable'.title()
        db.session.commit()
        form = AddCommonNameForm()
        form.set_categories()
        assert (cat1.id, cat1.category) in form.categories.choices
        assert (cat2.id, cat2.category) in form.categories.choices
        assert (cat3.id, cat3.category) in form.categories.choices

    def test_validate_name(self, db):
        """Raise a Validation error if common name already in db."""
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Coleus'
        db.session.commit()
        form = AddCommonNameForm()
        form.name.data = 'Sunflower'
        form.validate_name(form.name)
        form.name.data = 'Coleus'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)


class TestAddPacketFormWithDB:
    """Test custom methods of AddPacketForm."""
    def test_set_selects(self, db):
        """Set prices, units, and quantities with values from db."""
        price = Price()
        unit = Unit()
        qtyd = QtyDecimal()
        qtyf = QtyFraction()
        qtyi = QtyInteger()
        db.session.add_all([price, unit, qtyd, qtyf, qtyi])
        price.price = Decimal('2.99')
        unit.unit = 'seeds'
        qtyd.value = Decimal('4.35')
        qtyf.value = Fraction('1/2')
        qtyi.value = 200
        db.session.commit()
        form = AddPacketForm()
        form.set_selects()
        assert (0, '---') in form.prices.choices
        assert (0, '---') in form.units.choices
        # form.quantities is coerced to string, so first val of tuple is str.
        assert ('0', '---') in form.quantities.choices
        assert (price.id, '${0}'.format(price.price)) in form.prices.choices
        assert (unit.id, unit.unit) in form.units.choices
        assert (str(qtyd.value), str(qtyd.value)) in form.quantities.choices
        assert (str(qtyf.value), str(qtyf.value)) in form.quantities.choices
        assert (str(qtyi.value), str(qtyi.value)) in form.quantities.choices

    def test_validate_prices_different_submitted(self, db):
        """Raise error if prices and price result in different values."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('2.99')
        db.session.commit()
        form = AddPacketForm()
        form.price.data = Decimal('3.99')
        form.prices.data = price.id
        with pytest.raises(ValidationError):
            form.validate_prices(form.prices)

    def test_validate_prices_none_submitted(self, db):
        """Raise error if prices and price are both unset."""
        form = AddPacketForm()
        with pytest.raises(ValidationError):
            form.validate_prices(form.prices)
        # Now check form submission with no user input.
        form.prices.data = 0
        form.price.data = ''
        with pytest.raises(ValidationError):
            form.validate_prices(form.prices)

    def test_validate_prices_one_or_the_other(self, db):
        """Raise no error if only .prices or .price has data."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('3.99')
        db.session.commit()
        form = AddPacketForm()
        form.prices.data = price.id
        form.validate_prices(form.prices)
        form.price.data = ''  # Empty input form submission.
        form.validate_prices(form.prices)
        form.prices.data = None
        form.price.data = '2.99'
        form.validate_prices(form.prices)
        form.prices.data = 0  # Default select form submission.
        form.validate_prices(form.prices)

    def test_validate_prices_same_submitted(self, db):
        """Raise no error if prices and price result in same value."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('3.99')
        db.session.commit()
        form = AddPacketForm()
        form.prices.data = price.id
        form.price.data = Decimal('3.99')
        form.validate_prices(form.prices)

    def test_validate_quantities_different_submitted(self, db):
        """Raise error if quantity and quantities result in diff. values."""
        form = AddPacketForm()
        form.quantity.data = '100'
        form.quantities.data = '200'
        with pytest.raises(ValidationError):
            form.validate_quantities(form.quantities)

    def test_validate_quantities_none_submitted(self, db):
        """Raise error if no data in quantity or quantities."""
        form = AddPacketForm()
        with pytest.raises(ValidationError):
            form.validate_quantities(form.quantities)
        form.quantities.data = '0'  # Default select form submission.
        with pytest.raises(ValidationError):
            form.validate_quantities(form.quantities)

    def test_validate_quantities_one_or_the_other(self, db):
        """Raise no error if only .quantities or .quantity has data."""
        form = AddPacketForm()
        form.quantities.data = '100'
        form.validate_quantities(form.quantities)
        form.quantity.data = ''  # Empty input form submission.
        form.validate_quantities(form.quantities)
        form.quantities.data = None
        form.quantity.data = '100'
        form.validate_quantities(form.quantities)
        form.quantities.data = '0'  # Default select form submission.
        form.validate_quantities(form.quantities)
        form.quantities.data = 'None'  # Form coerces None to str.
        form.validate_quantities(form.quantities)

    def test_validate_quantities_same_submitted(self, db):
        """Raise no error if quantities and quantity result in same value."""
        form = AddPacketForm()
        form.quantity.data = '100'
        form.quantities.data = '100'
        form.validate_quantities(form.quantities)

    def test_validate_quantity(self, db):
        """Raise a ValidationError if field.data can't be used as quantity."""
        form = AddPacketForm()
        form.quantity.data = 'Forty-two'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)

    def test_validate_units_different_submitted(self, db):
        """Raise ValidationError if unit and units conflict."""
        unit = Unit()
        db.session.add(unit)
        unit.unit = 'cubits'
        db.session.commit()
        form = AddPacketForm()
        form.unit.data = 'seeds'
        form.units.data = unit.id
        with pytest.raises(ValidationError):
            form.validate_units(form.units)

    def test_validate_units_none_submitted(self, db):
        """Raise error if no data in unit or units."""
        form = AddPacketForm()
        with pytest.raises(ValidationError):
            form.validate_units(form.units)
        form.units.data = 0  # Check with default selected value.
        with pytest.raises(ValidationError):
            form.validate_units(form.units)

    def test_validate_units_one_or_the_other(self, db):
        """Raise no error if only .units or .unit is set."""
        unit = Unit()
        db.session.add(unit)
        unit.unit = 'bananas'
        db.session.commit()
        form = AddPacketForm()
        form.unit.data = 'hectares'
        form.validate_units(form.units)
        form.units.data = 0  # Default select form submission.
        form.validate_units(form.units)
        form.unit.data = None
        form.units.data = unit.id
        form.validate_units(form.units)
        form.unit.data = ''  # Empty input form submission.
        form.validate_units(form.units)

    def test_validate_units_same_submitted(self, db):
        """Do not raise an error if unit and units refer to same value."""
        unit = Unit()
        db.session.add(unit)
        unit.unit = 'seeds'
        db.session.commit()
        form = AddPacketForm()
        form.units.data = unit.id
        form.unit.data = 'seeds'
        form.validate_units(form.units)

    def test_validate_sku(self, db):
        """Raise ValidationError if SKU already exists in db."""
        packet = Packet()
        seed = Seed()
        db.session.add_all([packet, seed])
        packet.sku = '8675309'
        seed.name = 'Jenny'
        packet.seed = seed
        db.session.commit()
        form = AddPacketForm()
        form.sku.data = '8675309'
        with pytest.raises(ValidationError):
            form.validate_sku(form.sku)


class TestAddSeedFormWithDB:
    """Test custom methods of AddSeedForm."""
    def test_set_selects(self, db):
        """Selects should be set from database."""
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        db.session.add_all([bn, cat, cn])
        bn.name = 'Asclepias incarnata'
        cat.category = 'Perennial Flower'
        cn.name = 'Butterfly Weed'
        db.session.commit()
        form = AddSeedForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_names.choices
        assert (cat.id, cat.category) in form.categories.choices
        assert (cn.id, cn.name) in form.common_names.choices

    def test_validate_name(self, db):
        """Raise error if name is already in the database."""
        seed = Seed()
        db.session.add(seed)
        seed.name = 'Soulmate'
        db.session.commit()
        form = AddSeedForm()
        form.name.data = 'Soulmate'
        with pytest.raises(ValidationError):
            form.validate_name(form.name)

    def test_validate_thumbnail(self, db):
        "Raise ValidationError if image already exists with same filename."""
        image = Image()
        db.session.add(image)
        image.filename = secure_filename('frogfacts.png')
        db.session.commit()
        form = AddSeedForm()
        form.thumbnail.data = FileStorage()
        form.thumbnail.data.filename = 'frogfacts.png'
        with pytest.raises(ValidationError):
            form.validate_thumbnail(form.thumbnail)


class TestEditBotanicalNameFormWithDB:
    """Test custom methods of EditBotanicalNameForm."""
    def test_set_common_names(self, db):
        """Set .add/remove_common_names.choices with CommonNames from db."""
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
    def test_set_categories(self, db):
        """Set categories with Categories from the db."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.category = 'Annual Flower'.title()
        cat2.category = 'Perennial Flower'.title()
        cat3.category = 'Vegetable'.title()
        db.session.commit()
        form = EditCommonNameForm()
        form.set_categories()
        assert (cat1.id, cat1.category) in form.categories.choices
        assert (cat2.id, cat2.category) in form.categories.choices
        assert (cat3.id, cat3.category) in form.categories.choices


class TestEditCategoryFormWithDB:
    """Test custom methods of EditCategoryForm."""
    def test_populate(self, db):
        """Populate form from a Category object."""
        category = Category()
        db.session.add(category)
        category.category = 'Annual Flowers'
        category.description = 'Not really built to last.'
        db.session.commit()
        form = EditCategoryForm()
        form.populate(category)
        assert form.category.data == category.category
        assert form.description.data == category.description


class TestEditPacketFormWithDB:
    """Test custom methods of EditPacketForm."""
    def test_populate(self, db):
        """Populate form with info from database."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.price = Decimal('2.99')
        pkt.quantity = 100
        pkt.unit = 'seeds'
        pkt.sku = '8675309'
        db.session.commit()
        form = EditPacketForm()
        form.set_selects()
        form.populate(pkt)
        assert form.prices.data == pkt._price.id
        assert form.units.data == pkt._unit.id
        assert form.quantities.data == str(pkt.quantity)
        assert form.sku.data == pkt.sku

    def test_set_selects(self, db):
        """Set prices, units, and quantities with values from database."""
        price = Price()
        qd = QtyDecimal()
        qf = QtyFraction()
        qi = QtyInteger()
        unit = Unit()
        db.session.add_all([price, qd, qf, qi, unit])
        price.price = Decimal('1.99')
        qd.value = Decimal('2.5')
        qf.value = Fraction('1/4')
        qi.value = 100
        unit.unit = 'cubits'
        db.session.commit()
        form = EditPacketForm()
        form.set_selects()
        assert (price.id, '$1.99') in form.prices.choices
        assert ('2.5', '2.5') in form.quantities.choices
        assert ('1/4', '1/4') in form.quantities.choices
        assert ('100', '100') in form.quantities.choices
        assert (unit.id, 'cubits') in form.units.choices

    def test_validate_quantity(self, db):
        """Raise a ValidationError if field.data can't be used as quantity."""
        form = EditPacketForm()
        form.quantity.data = 'Forty-two'
        with pytest.raises(ValidationError):
            form.validate_quantity(form.quantity)


class TestEditSeedFormWithDB:
    """Test custom methods of EditSeedForm."""
    def test_populate(self, db):
        """Populate form fields with data from a seed object."""
        seed = Seed()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([seed, bn, cn, cat])
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.in_stock = True
        seed.dropped = True
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        seed.botanical_names.append(bn)
        seed.categories.append(cat)
        seed.common_name = cn
        db.session.commit()
        form = EditSeedForm()
        form.set_selects()
        form.populate(seed)
        assert bn.id in form.botanical_names.data
        assert cat.id in form.categories.data
        assert cn.id == form.common_name.data
        assert seed.name in form.name.data
        assert seed.description in form.description.data
        assert form.in_stock.data
        assert form.dropped.data

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
        form = EditSeedForm()
        form.set_selects()
        assert (bn.id, bn.name) in form.botanical_names.choices
        assert (cn.id, cn.name) in form.common_name.choices
        assert (cat.id, cat.category) in form.categories.choices


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
        form.set_names()
        assert (bn1.id, bn1.name) in form.names.choices
        assert (bn2.id, bn2.name) in form.names.choices
        assert (bn3.id, bn3.name) in form.names.choices


class TestSelectCategoryFormWithDB:
    """Test custom methods of SelectCategoryForm."""
    def test_set_categories(self, db):
        """Load all categories from database into select field."""
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([cat1, cat2, cat3])
        cat1.category = 'Perennial Flowers'
        cat2.category = 'Annual Flowers'
        cat3.category = 'Vegetables'
        db.session.commit()
        form = SelectCategoryForm()
        form.set_categories()
        assert (cat1.id, cat1.category) in form.categories.choices
        assert (cat2.id, cat2.category) in form.categories.choices
        assert (cat3.id, cat3.category) in form.categories.choices


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
        form.set_names()
        assert (cn1.id, cn1.name) in form.names.choices
        assert (cn2.id, cn2.name) in form.names.choices
        assert (cn3.id, cn3.name) in form.names.choices


class TestSelectPacketFormWithDB:
    """Test custom methods of SelectPacketForm."""
    def test_set_packets(self, db):
        """Set select with packets loaded from database."""
        seed = Seed()
        cn = CommonName()
        packet = Packet()
        db.session.add_all([seed, cn, packet])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        packet.price = Decimal('2.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        seed.common_name = cn
        seed.packets.append(packet)
        db.session.commit()
        form = SelectPacketForm()
        form.set_packets()
        assert (packet.id,
                'Foxglove, Foxy - SKU 8675309: $2.99 for 100 seeds') in\
            form.packets.choices


class TestSelectSeedFormWithDB:
    """Test custom methods of SelectSeedForm."""
    def test_set_seeds(self, db):
        """Set select with seeds loaded from database."""
        sd1 = Seed()
        sd2 = Seed()
        sd3 = Seed()
        db.session.add_all([sd1, sd2, sd3])
        sd1.name = 'Soulmate'
        sd2.name = 'Tumbling Tom'
        sd2.name = 'Foxy'
        db.session.commit()
        form = SelectSeedForm()
        form.set_seeds()
        assert (sd1.id, sd1.name) in form.seeds.choices
        assert (sd2.id, sd2.name) in form.seeds.choices
        assert (sd3.id, sd3.name) in form.seeds.choices

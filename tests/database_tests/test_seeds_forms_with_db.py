import unittest
from decimal import Decimal
from fractions import Fraction
from werkzeug import FileStorage, secure_filename
from wtforms import ValidationError
from app import create_app, db
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


class TestFunctionsWithDB(unittest.TestCase):
    """Test module-level methods with the database."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_botanical_name_select_list(self):
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
        self.assertIn((bn1.id, bn1.name), bnlist)
        self.assertIn((bn2.id, bn2.name), bnlist)
        self.assertIn((bn3.id, bn3.name), bnlist)

    def test_category_select_list(self):
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
        self.assertIn((cat1.id, cat1.category), catlist)
        self.assertIn((cat2.id, cat2.category), catlist)
        self.assertIn((cat3.id, cat3.category), catlist)

    def test_common_name_select_list(self):
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
        self.assertIn((cn1.id, cn1.name), cnlist)
        self.assertIn((cn2.id, cn2.name), cnlist)
        self.assertIn((cn3.id, cn3.name), cnlist)

    def test_packet_select_list(self):
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
        self.assertEqual(pktlst, expected)

    def test_seed_select_list(self):
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
        self.assertIn((sd1.id, sd1.name), seedlist)
        self.assertIn((sd2.id, sd2.name), seedlist)
        self.assertIn((sd3.id, sd3.name), seedlist)


class testAddBotanicalNameFormWithDB(unittest.TestCase):
    """Test custom methods of AddBotanicalNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_common_names(self):
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
        self.assertIn((cn1.id, cn1.name), form.common_names.choices)
        self.assertIn((cn2.id, cn2.name), form.common_names.choices)
        self.assertIn((cn2.id, cn2.name), form.common_names.choices)

    def test_validate_name(self):
        """Raise error if name in DB or invalid botanical name."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        form = AddBotanicalNameForm()
        form.name.data = 'Innagada davida'
        form.validate_name(form.name)
        form.name.data = 'Title Case is not a binomen'
        with self.assertRaises(ValidationError):
            form.validate_name(form.name)
        form.name.data = 'Asclepias incarnata'
        with self.assertRaises(ValidationError):
            form.validate_name(form.name)


class TestAddCategoryFormWithDB(unittest.TestCase):
    """Test custom methods of AddCategoryForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_validate_category(self):
        """Raise a ValidationError if category already in db."""
        category = Category()
        db.session.add(category)
        category.category = 'Annual Flowers'
        db.session.commit()
        form = AddCategoryForm()
        form.category.data = 'Perennial Flowers'
        form.validate_category(form.category)
        form.category.data = 'annual flowers'
        with self.assertRaises(ValidationError):
            form.validate_category(form.category)


class TestAddCommonNameFormWithDB(unittest.TestCase):
    """Test custom methods of AddCommonNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_categories(self):
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
        self.assertIn((cat1.id, cat1.category), form.categories.choices)
        self.assertIn((cat2.id, cat2.category), form.categories.choices)
        self.assertIn((cat3.id, cat3.category), form.categories.choices)

    def test_validate_name(self):
        """Raise a Validation error if common name already in db."""
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Coleus'
        db.session.commit()
        form = AddCommonNameForm()
        form.name.data = 'Sunflower'
        form.validate_name(form.name)
        form.name.data = 'Coleus'
        with self.assertRaises(ValidationError):
            form.validate_name(form.name)


class TestAddPacketFormWithDB(unittest.TestCase):
    """Test custom methods of AddPacketForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_selects(self):
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
        self.assertIn((0, '---'), form.prices.choices)
        self.assertIn((0, '---'), form.units.choices)
        # form.quantities is coerced to string, so first value of tuple is str.
        self.assertIn(('0', '---'), form.quantities.choices)
        self.assertIn((price.id, '${0}'.format(price.price)),
                      form.prices.choices)
        self.assertIn((unit.id, unit.unit), form.units.choices)
        self.assertIn((str(qtyd.value), str(qtyd.value)),
                      form.quantities.choices)
        self.assertIn((str(qtyf.value), str(qtyf.value)),
                      form.quantities.choices)
        self.assertIn((str(qtyi.value), str(qtyi.value)),
                      form.quantities.choices)

    def test_validate_prices_different_submitted(self):
        """Raise error if prices and price result in different values."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('2.99')
        db.session.commit()
        form = AddPacketForm()
        form.price.data = Decimal('3.99')
        form.prices.data = price.id
        with self.assertRaises(ValidationError):
            form.validate_prices(form.prices)

    def test_validate_prices_none_submitted(self):
        """Raise error if prices and price are both unset."""
        form = AddPacketForm()
        with self.assertRaises(ValidationError):
            form.validate_prices(form.prices)
        # Now check form submission with no user input.
        form.prices.data = 0
        form.price.data = ''
        with self.assertRaises(ValidationError):
            form.validate_prices(form.prices)

    def test_validate_prices_one_or_the_other(self):
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

    def test_validate_prices_same_submitted(self):
        """Raise no error if prices and price result in same value."""
        price = Price()
        db.session.add(price)
        price.price = Decimal('3.99')
        db.session.commit()
        form = AddPacketForm()
        form.prices.data = price.id
        form.price.data = Decimal('3.99')
        form.validate_prices(form.prices)

    def test_validate_quantities_different_submitted(self):
        """Raise error if quantity and quantities result in diff. values."""
        form = AddPacketForm()
        form.quantity.data = '100'
        form.quantities.data = '200'
        with self.assertRaises(ValidationError):
            form.validate_quantities(form.quantities)

    def test_validate_quantities_none_submitted(self):
        """Raise error if no data in quantity or quantities."""
        form = AddPacketForm()
        with self.assertRaises(ValidationError):
            form.validate_quantities(form.quantities)
        form.quantities.data = '0'  # Default select form submission.
        with self.assertRaises(ValidationError):
            form.validate_quantities(form.quantities)

    def test_validate_quantities_one_or_the_other(self):
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

    def test_validate_quantities_same_submitted(self):
        """Raise no error if quantities and quantity result in same value."""
        form = AddPacketForm()
        form.quantity.data = '100'
        form.quantities.data = '100'
        form.validate_quantities(form.quantities)

    def test_validate_quantity(self):
        """Raise a ValidationError if field.data can't be used as quantity."""
        form = AddPacketForm()
        form.quantity.data = 'Forty-two'
        with self.assertRaises(ValidationError):
            form.validate_quantity(form.quantity)

    def test_validate_units_different_submitted(self):
        """Raise ValidationError if unit and units conflict."""
        unit = Unit()
        db.session.add(unit)
        unit.unit = 'cubits'
        db.session.commit()
        form = AddPacketForm()
        form.unit.data = 'seeds'
        form.units.data = unit.id
        with self.assertRaises(ValidationError):
            form.validate_units(form.units)

    def test_validate_units_none_submitted(self):
        """Raise error if no data in unit or units."""
        form = AddPacketForm()
        with self.assertRaises(ValidationError):
            form.validate_units(form.units)
        form.units.data = 0  # Check with default selected value.
        with self.assertRaises(ValidationError):
            form.validate_units(form.units)

    def test_validate_units_one_or_the_other(self):
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

    def test_validate_units_same_submitted(self):
        """Do not raise an error if unit and units refer to same value."""
        unit = Unit()
        db.session.add(unit)
        unit.unit = 'seeds'
        db.session.commit()
        form = AddPacketForm()
        form.units.data = unit.id
        form.unit.data = 'seeds'
        form.validate_units(form.units)

    def test_validate_sku(self):
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
        with self.assertRaises(ValidationError):
            form.validate_sku(form.sku)


class TestAddSeedFormWithDB(unittest.TestCase):
    """Test custom methods of AddSeedForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_selects(self):
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
        self.assertIn((bn.id, bn.name), form.botanical_names.choices)
        self.assertIn((cat.id, cat.category), form.categories.choices)
        self.assertIn((cn.id, cn.name), form.common_names.choices)

    def test_validate_name(self):
        """Raise error if name is already in the database."""
        seed = Seed()
        db.session.add(seed)
        seed.name = 'Soulmate'
        db.session.commit()
        form = AddSeedForm()
        form.name.data = 'Soulmate'
        with self.assertRaises(ValidationError):
            form.validate_name(form.name)

    def test_validate_thumbnail(self):
        "Raise ValidationError if image already exists with same filename."""
        image = Image()
        db.session.add(image)
        image.filename = secure_filename('frogfacts.png')
        db.session.commit()
        form = AddSeedForm()
        form.thumbnail.data = FileStorage()
        form.thumbnail.data.filename = 'frogfacts.png'
        with self.assertRaises(ValidationError):
            form.validate_thumbnail(form.thumbnail)


class TestEditBotanicalNameFormWithDB(unittest.TestCase):
    """Test custom methods of EditBotanicalNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_common_names(self):
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
        self.assertIn((cn1.id, cn1.name), form.common_names.choices)
        self.assertIn((cn2.id, cn2.name), form.common_names.choices)
        self.assertIn((cn3.id, cn3.name), form.common_names.choices)


class TestEditCommonNameFormWithDB(unittest.TestCase):
    """Test custom methods of EditCommonNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_categories(self):
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
        self.assertIn((cat1.id, cat1.category), form.categories.choices)
        self.assertIn((cat2.id, cat2.category), form.categories.choices)
        self.assertIn((cat3.id, cat3.category), form.categories.choices)


class TestEditCategoryFormWithDB(unittest.TestCase):
    """Test custom methods of EditCategoryForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_populate(self):
        """Populate form from a Category object."""
        category = Category()
        db.session.add(category)
        category.category = 'Annual Flowers'
        category.description = 'Not really built to last.'
        db.session.commit()
        form = EditCategoryForm()
        form.populate(category)
        self.assertEqual(form.category.data, category.category)
        self.assertEqual(form.description.data, category.description)


class TestEditPacketFormWithDB(unittest.TestCase):
    """Test custom methods of EditPacketForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_populate(self):
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
        self.assertEqual(form.prices.data, pkt._price.id)
        self.assertEqual(form.units.data, pkt._unit.id)
        self.assertEqual(form.quantities.data, str(pkt.quantity))
        self.assertEqual(form.sku.data, pkt.sku)

    def test_set_selects(self):
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
        self.assertIn((price.id, '$1.99'), form.prices.choices)
        self.assertIn(('2.5', '2.5'), form.quantities.choices)
        self.assertIn(('1/4', '1/4'), form.quantities.choices)
        self.assertIn(('100', '100'), form.quantities.choices)
        self.assertIn((unit.id, 'cubits'), form.units.choices)

    def test_validate_quantity(self):
        """Raise a ValidationError if field.data can't be used as quantity."""
        form = EditPacketForm()
        form.quantity.data = 'Forty-two'
        with self.assertRaises(ValidationError):
            form.validate_quantity(form.quantity)


class TestEditSeedFormWithDB(unittest.TestCase):
    """Test custom methods of EditSeedForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_populate(self):
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
        self.assertIn(bn.id, form.botanical_names.data)
        self.assertIn(cat.id, form.categories.data)
        self.assertEqual(cn.id, form.common_name.data)
        self.assertIn(seed.name, form.name.data)
        self.assertIn(seed.description, form.description.data)
        self.assertTrue(form.in_stock.data)
        self.assertTrue(form.dropped.data)

    def test_set_selects(self):
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
        self.assertIn((bn.id, bn.name), form.botanical_names.choices)
        self.assertIn((cn.id, cn.name), form.common_name.choices)
        self.assertIn((cat.id, cat.category), form.categories.choices)


class TestSelectBotanicalFormWithDB(unittest.TestCase):
    """Test custom methods of SelectBotanicalNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_names(self):
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
        self.assertIn((bn1.id, bn1.name), form.names.choices)
        self.assertIn((bn2.id, bn2.name), form.names.choices)
        self.assertIn((bn3.id, bn3.name), form.names.choices)


class TestSelectCategoryFormWithDB(unittest.TestCase):
    """Test custom methods of SelectCategoryForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_categories(self):
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
        self.assertIn((cat1.id, cat1.category), form.categories.choices)
        self.assertIn((cat2.id, cat2.category), form.categories.choices)
        self.assertIn((cat3.id, cat3.category), form.categories.choices)


class TestSelectCommonNameFormWithDB(unittest.TestCase):
    """Test custom methods of SelectCommonNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_names(self):
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
        self.assertIn((cn1.id, cn1.name), form.names.choices)
        self.assertIn((cn2.id, cn2.name), form.names.choices)
        self.assertIn((cn3.id, cn3.name), form.names.choices)


class TestSelectPacketFormWithDB(unittest.TestCase):
    """Test custom methods of SelectPacketForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_packets(self):
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
        self.assertIn((packet.id,
                       'Foxglove, Foxy - SKU 8675309: $2.99 for 100 seeds'),
                      form.packets.choices)


class TestSelectSeedFormWithDB(unittest.TestCase):
    """Test custom methods of SelectSeedForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_set_seeds(self):
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
        self.assertIn((sd1.id, sd1.name), form.seeds.choices)
        self.assertIn((sd2.id, sd2.name), form.seeds.choices)
        self.assertIn((sd3.id, sd3.name), form.seeds.choices)


if __name__ == '__main__':
    unittest.main()

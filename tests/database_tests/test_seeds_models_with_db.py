import unittest
from app import create_app, db
from app.seeds.models import BotanicalName, Category, CommonName, Packet, \
    Seed, UnitType


class TestPacketWithDB(unittest.TestCase):
    """Test Packet model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_unit_type_expression(self):
        """unit_type should be usable in queries."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit_type = 'frogs'
        self.assertIs(Packet.query.filter_by(unit_type='frogs').first(), pkt)

    def test_unit_type_getter(self):
        """.unit_type returns ._unit_type.unit_type"""
        pkt = Packet()
        db.session.add(pkt)
        pkt._unit_type = UnitType('seeds')
        self.assertEqual(pkt.unit_type, 'seeds')

    def test_unit_type_setter_new_type(self):
        """create a new UnitType in the database if not already there."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit_type = 'seeds'
        db.session.commit()
        self.assertEqual(UnitType.query.filter_by(unit_type='seeds').count(),
                         1)

    def test_unit_type_setter_existing_type(self):
        """Set the packet's unit_type to type from database if it exists."""
        pkt = Packet()
        db.session.add(pkt)
        pkt.unit_type = 'seeds'
        pkt2 = Packet()
        db.session.add(pkt2)
        pkt2.unit_type = 'seeds'
        self.assertIsNot(pkt, pkt2)
        self.assertIs(pkt.unit_type, pkt2.unit_type)
        pkt3 = Packet()
        db.session.add(pkt3)
        pkt3.unit_type = ('oz')
        self.assertIsNot(pkt.unit_type, pkt3.unit_type)


class TestSeedWithDB(unittest.TestCase):
    """Test Seed model methods that require database access."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_botanical_name_already_in_db(self):
        """Add botanical name from DB to ._botanical_names if present."""
        bn = BotanicalName('Asclepias incarnata')
        db.session.add(bn)
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertIs(seed._botanical_names[0], bn)

    def test_add_botanical_name_new(self):
        """Adds a new botanical name if not already in db."""
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertEqual(BotanicalName.query.count(), 1)
        self.assertEqual(seed._botanical_names[0]._name,
                         'Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        db.session.add(seed)
        self.assertEqual(BotanicalName.query.count(), 2)
        self.assertEqual(len(seed._botanical_names), 2)
        self.assertEqual(seed._botanical_names[1]._name,
                         'Echinacea purpurea')

    def test_add_category_already_in_db(self):
        """Add category from DB to ._categories if present."""
        cat = Category(category='Herb')
        db.session.add(cat)
        seed = Seed()
        db.session.add(seed)
        seed.add_category('Herb')
        self.assertIs(seed._categories[0], cat)

    def test_add_category_new(self):
        """Add new category to DB if it does not already exist."""
        seed = Seed()
        db.session.add(seed)
        self.assertEqual(Category.query.filter_by(category='Herb').count(), 0)
        seed.add_category('Herb')
        self.assertEqual(Category.query.filter_by(category='Herb').count(), 1)

    def test_add_common_name_already_in_db(self):
        """Add common name from DB to ._common_names if already present."""
        cn = CommonName(name='Coleus')
        db.session.add(cn)
        seed = Seed()
        db.session.add(seed)
        seed.add_common_name(name='Coleus')
        self.assertIs(seed._common_names[0], cn)

    def test_add_common_name_new(self):
        """Add a new common name if not already present."""
        seed = Seed()
        db.session.add(seed)
        self.assertEqual(CommonName.query.count(), 0)
        seed.add_common_name('Coleus')
        self.assertEqual(CommonName.query.count(), 1)

    def test_botanical_name_does_not_clash_with_botanical_names(self):
        """Use the same instance if same name is in both.

        It should not be possible to cause a UNIQUE constraint failure
        by setting botanical_name and botanical_names in the same session.
        """
        seed = Seed()
        seed.botanical_name = 'Asclepias incarnata'
        seed.add_botanical_name('Asclepias incarnata')
        db.session.add(seed)
        db.session.commit()
        seed1 = Seed()
        seed1.add_botanical_name('Echinacea purpurea')
        seed1.botanical_name = 'Echinacea purpurea'
        db.session.add(seed1)
        db.session.commit()

    def test_botanical_name_expression(self):
        """botanical_name should be usable in queries."""
        seed = Seed()
        seed.botanical_name = 'Asclepias incarnata'
        db.session.add(seed)
        self.assertIs(Seed.query.filter_by(
            botanical_name='Asclepias incarnata').first(), seed)

    def test_botanical_name_setter_already_in_db(self):
        """Set botanical_name to existing instance if present."""
        bn = BotanicalName('Asclepias incarnata')
        db.session.add(bn)
        seed = Seed()
        seed.botanical_name = 'Asclepias incarnata'
        self.assertIs(seed._botanical_name, bn)

    def test_botanical_name_setter_new_entry(self):
        """Set botanical_name to new instance if not present in db."""
        seed = Seed()
        seed.botanical_name = 'Asclepias incarnata'
        self.assertEqual(BotanicalName.query.count(), 0)
        db.session.add(seed)
        self.assertEqual(BotanicalName.query.count(), 1)

    def test_botanical_names_setter_list(self):
        """Clear _botanical_names and add assigned list of names to it."""
        seed = Seed()
        seed.add_botanical_name('Canis lupus')  # Well, maybe it's a seed.
        db.session.add(seed)
        bn_list = ['Asclepias incarnata',
                   'Echinacea purpurea',
                   'Digitalis lanata']
        seed.botanical_names = bn_list
        self.assertNotIn('Canis lupus', seed.botanical_names)
        self.assertEqual(seed.botanical_names, bn_list)

    def test_botanical_names_setter_string_no_commas(self):
        """Clear _botanical_names and add the name assigned."""
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        seed.botanical_names = 'Echinacea purpurea'
        self.assertIn('Echinacea purpurea', seed.botanical_names)
        self.assertNotIn('Asclepias incarnata', seed.botanical_names)

    def test_botanical_names_setter_string_with_commas(self):
        """Split names into a list if commas are present, and add each."""
        seed = Seed()
        db.session.add(seed)
        seed.botanical_names = 'Asclepias incarnata, Echinacea purpurea, ' + \
            'Digitalis lanata, Canis lupus'
        self.assertEqual(seed.botanical_names.sort(),
                         ['Asclepias incarnata', 'Echinacea purpurea',
                          'Digitalis lanata', 'Canis lupus'].sort())

    def test_categories_setter_clears_when_appropriate(self):
        """Clear categories before setting if given valid input.

        It should not clear categories if given invalid input.
        """
        seed = Seed()
        db.session.add(seed)
        seed.add_category('Perennial Flower')
        self.assertIn('Perennial Flower', seed.categories)
        try:
            seed.categories = 42
        except:
            pass
        self.assertIn('Perennial Flower', seed.categories)
        self.assertNotIn('Herb', seed.categories)
        seed.categories = 'Herb'
        self.assertNotIn('Perennial Flower', seed.categories)
        seed.categories = 'Vegetable, Annual Flower'
        self.assertNotIn('Herb', seed.categories)
        seed.categories = ['Herb', 'Annual Flower']
        self.assertNotIn('Vegetable', seed.categories)
        try:
            seed.categories = ['Vegetable', 42]
        except:
            pass
        self.assertEqual(seed.categories.sort(),
                         ['Herb', 'Annual Flower'].sort())

    def test_categories_setter_string_no_commas(self):
        """Set categories to a single string if no commas are present."""
        seed = Seed()
        db.session.add(seed)
        seed.categories = 'Perennial Flower'
        self.assertEqual(seed.categories, ['Perennial Flower'])

    def test_categories_setter_string_with_commas(self):
        """Split categories into a list if commas are present and add each."""
        seed = Seed()
        db.session.add(seed)
        seed.categories = 'Vegetable, Herb, Perennial Flower'
        self.assertEqual(seed.categories.sort(),
                         ['Vegetable', 'Herb', 'Perennial Flower'].sort())

    def test_category_expression(self):
        """.category should be usable in Seed.query."""
        seed = Seed()
        db.session.add(seed)
        seed._category = Category(category='Annual Flower')
        self.assertIs(Seed.query.filter_by(category='Annual Flower').first(),
                      seed)

    def test_category_setter_already_in_categories(self):
        """Set ._category to category from ._categories if exists already."""
        seed = Seed()
        db.session.add(seed)
        seed._categories.append(Category('Vegetable'))
        seed.category = 'Vegetable'
        self.assertIs(seed._category, seed._categories[0])

    def test_category_setter_already_in_db(self):
        """Set ._category to category from database if present."""
        cat = Category('Vegetable')
        db.session.add(cat)
        seed = Seed()
        db.session.add(seed)
        seed.category = 'Vegetable'
        self.assertIs(seed._category, cat)

    def test_category_setter_new(self):
        """Set ._category to a new Category if it is new."""
        seed = Seed()
        db.session.add(seed)
        self.assertEqual(Category.query.filter_by(category='Herb').count(), 0)
        seed.category = 'Herb'
        self.assertEqual(Category.query.filter_by(category='Herb').count(), 1)

    def test_clear_botanical_names(self):
        """Remove all botanical names from seed and return of removed.

        This should not remove them from the database!
        """
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        seed.add_botanical_name('Digitalis lanata')
        self.assertEqual(len(seed._botanical_names), 3)
        self.assertEqual(seed.clear_botanical_names(), 3)
        self.assertEqual(len(seed._botanical_names), 0)
        db.session.commit()
        self.assertEqual(BotanicalName.query.count(), 3)

    def test_clear_categories(self):
        """Remove all categories from seed and return # removed.

        This should not remove them from the database!
        """
        seed = Seed()
        db.session.add(seed)
        seed.add_category('Vegetable')
        seed.add_category('Herb')
        seed.add_category('Perennial Flower')
        self.assertEqual(len(seed._categories), 3)
        self.assertEqual(seed.clear_categories(), 3)
        self.assertEqual(len(seed._categories), 0)
        self.assertEqual(Category.query.count(), 3)

    def test_clear_common_names(self):
        """Remove all common names from seed and return # removed.

        This should not remove them from the database!
        """
        seed = Seed()
        db.session.add(seed)
        seed.add_common_name('Coleus')
        seed.add_common_name('Tomato')
        seed.add_common_name('Sunflower')
        self.assertEqual(len(seed._common_names), 3)
        self.assertEqual(seed.clear_common_names(), 3)
        self.assertEqual(len(seed._common_names), 0)
        db.session.commit()
        self.assertEqual(CommonName.query.count(), 3)

    def test_common_name_does_not_conflict_with_common_names(self):
        """Different copies of the same common name should not be made.

        A UNIQUE clash should not happen if .common_name and .common_names are
        given the same values in the same transaction.
        """
        seed = Seed()
        seed.common_name = 'Coleus'
        seed.add_common_name('Coleus')
        db.session.add(seed)
        db.session.commit()
        seed.add_common_name('Tomato')
        seed.common_name = 'Tomato'
        db.session.commit()

    def test_common_name_expression(self):
        """.common_name should be usable in queries."""
        seed = Seed()
        db.session.add(seed)
        seed.common_name = 'Coleus'
        self.assertIs(seed, Seed.query.filter_by(common_name='Coleus').first())

    def test_common_name_setter_already_in_db(self):
        """Set _common_name to loaded CommonName from db if it exists."""
        cn = CommonName(name='Coleus')
        db.session.add(cn)
        db.session.commit()
        seed = Seed()
        seed.common_name = 'Coleus'
        self.assertIs(seed._common_name, cn)

    def test_common_name_setter_already_in_common_names(self):
        """Set _common_name to object from _common_names if present."""
        cn = CommonName(name='Coleus')
        seed = Seed()
        seed._common_names.append(cn)
        seed._common_names.append(CommonName('Tomato'))
        seed.common_name = 'Coleus'
        self.assertIs(seed._common_name, cn)

    def test_common_name_setter_new_entry(self):
        """Create a new CommonName object if it doesn't exist already."""
        seed = Seed()
        self.assertEqual(CommonName.query.filter_by(name='Coleus').count(), 0)
        seed.common_name = 'Coleus'
        db.session.add(seed)
        db.session.commit()
        self.assertEqual(CommonName.query.filter_by(name='Coleus').count(), 1)

    def test_common_names_setter_iterable_containing_strings(self):
        """Given an iterable containing strings, set them to .common_names."""
        seed = Seed()
        db.session.add(seed)
        seed.common_names = ['Coleus', 'Tomato', 'Cabbage']
        self.assertEqual(seed.common_names.sort(),
                         ['Coleus', 'Tomato', 'Cabbage'].sort())
        seed.common_names = ('Carrot', 'Sage', 'Grass')
        self.assertEqual(seed.common_names.sort(),
                         ['Carrot', 'Sage', 'Grass'].sort())

    def test_common_names_setter_str_no_commas(self):
        """Given a string with no commas, set the string to .common_names."""
        seed = Seed()
        db.session.add(seed)
        seed.common_names = 'Coleus'
        self.assertEqual(seed.common_names, ['Coleus'])
        seed.common_names = 'Tomato'
        self.assertEqual(seed.common_names, ['Tomato'])

    def test_common_names_setter_str_with_commas(self):
        """Split a string with commas into a list and add each element."""
        seed = Seed()
        db.session.add(seed)
        seed.common_names = 'Coleus, Tomato, Cabbage'
        self.assertEqual(seed.common_names.sort(),
                         ['Coleus', 'Tomato', 'Cabbage'].sort())

    def test_remove_botanical_name_not_in_database(self):
        """Returns false if the botanical name is not in _botanical_names."""
        seed = Seed()
        db.session.add(seed)
        self.assertFalse(seed.remove_botanical_name('Asclepias incarnata'))

    def test_remove_botanical_name_succeeds(self):
        """Returns true and removes name from _botanical_names on success.

        It also should not delete the botanical name from the database.
        """
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Canis lupus')  # Okay, not really a seed.
        db.session.add(seed)
        db.session.commit()
        self.assertTrue(seed.remove_botanical_name('Canis lupus'))
        db.session.commit()
        self.assertNotIn('Canis Lupus', seed.botanical_names)
        self.assertIn('Canis lupus',
                      [bn.name for bn in BotanicalName.query.all()])


if __name__ == '__main__':
    unittest.main()

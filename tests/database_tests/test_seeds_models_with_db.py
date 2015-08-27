import unittest
from app import create_app, db
from app.seeds.models import BotanicalName, CommonName, Packet, Seed, UnitType


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

    def test_add_botanical_name_already_in_botanical_name(self):
        """Use the same instance as _botanical_name if name is the same."""
        seed = Seed()
        db.session.add(seed)
        seed.botanical_name = 'Asclepias incarnata'
        seed.add_botanical_name('Asclepias incarnata')
        self.assertIn(seed._botanical_name, seed._botanical_names)

    def test_add_botanical_name_already_in_botanical_names(self):
        """If botanical_names has not been comitted, don't add duplicates."""
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertEqual(len(seed._botanical_names), 1)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertEqual(len(seed._botanical_names), 1)
        seed.add_botanical_name('Echinacea purpurea')
        self.assertEqual(len(seed._botanical_names), 2)
        seed.add_botanical_name('Echinacea purpurea')
        self.assertEqual(len(seed._botanical_names), 2)

    def test_add_botanical_name_already_in_db(self):
        """Add botanical name from DB to ._botanical_names if present."""
        bn = BotanicalName('Asclepias incarnata')
        db.session.add(bn)
        db.session.commit()
        self.assertIn(bn, BotanicalName.query.all())
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        db.session.commit()
        self.assertIn(bn, seed._botanical_names)
        self.assertEqual(BotanicalName.query.count(), 1)

    def test_add_botanical_name_new(self):
        """Adds a new botanical name if not already in db."""
        seed = Seed()
        db.session.add(seed)
        seed.add_botanical_name('Asclepias incarnata')
        self.assertEqual(BotanicalName.query.count(), 1)
        self.assertEqual(seed._botanical_names[0]._botanical_name,
                         'Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        db.session.add(seed)
        self.assertEqual(BotanicalName.query.count(), 2)
        self.assertEqual(len(seed._botanical_names), 2)
        self.assertEqual(seed._botanical_names[1]._botanical_name,
                         'Echinacea purpurea')

    def test_add_common_name_already_in_common_name(self):
        """Set to same instance as ._common_name if the same name."""
        seed = Seed()
        db.session.add(seed)
        seed.common_name = 'Coleus'
        seed.add_common_name('Coleus')
        self.assertIn(seed._common_name, seed._common_names)

    def test_add_common_name_already_in_common_names(self):
        """Don't add a common name if it's already in ._common_names."""
        seed = Seed()
        db.session.add(seed)
        seed.add_common_name('Coleus')
        self.assertEqual(len(seed._common_names), 1)
        seed.add_common_name('Coleus')
        print(seed._common_names)
        self.assertEqual(len(seed._common_names), 1)
        seed.add_common_name('Tomato')
        self.assertEqual(len(seed._common_names), 2)
        seed.add_common_name('Tomato')
        self.assertEqual(len(seed._common_names), 2)

    def test_add_common_name_already_in_db(self):
        """Add common name from DB to ._common_names if already present."""
        cn = CommonName(name='Coleus')
        db.session.add(cn)
        db.session.commit()
        self.assertIn(cn, CommonName.query.all())
        seed = Seed()
        seed.add_common_name(name='Coleus')
        db.session.add(seed)
        db.session.commit()
        self.assertIn(cn, seed._common_names)
        self.assertEqual(CommonName.query.count(), 1)

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

    def test_botanical_names_getter_returns_list_of_strings(self):
        """Returns a list of strings from BotanicalName.botanical_name."""
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        seed.add_botanical_name('Canis lupus')  # Totally a seed!
        db.session.add(seed)
        bns = seed.botanical_names
        self.assertTrue(isinstance(bns, list))
        self.assertIn('Asclepias incarnata', bns)
        self.assertIn('Echinacea purpurea', bns)
        self.assertIn('Canis lupus', bns)

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
        seed.add_botanical_name('Asclepias incarnata')
        db.session.add(seed)
        seed.botanical_names = 'Echinacea purpurea'
        self.assertIn('Echinacea purpurea', seed.botanical_names)
        self.assertNotIn('Asclepias incarnata', seed.botanical_names)

    def test_botanical_names_setter_string_with_commas(self):
        """Split names into a list if commas are present, and add each."""
        seed = Seed()
        seed.botanical_names = 'Asclepias incarnata, Echinacea purpurea, ' + \
            'Digitalis lanata, Canis lupus'
        self.assertEqual(seed.botanical_names.sort(),
                         ['Asclepias incarnata', 'Echinacea purpurea',
                          'Digitalis lanata', 'Canis lupus'].sort())

    def test_common_name_expression(self):
        """.common_name should be usable in queries."""
        seed = Seed()
        db.session.add(seed)
        seed.common_name = 'Coleus'
        self.assertIs(seed, Seed.query.filter_by(common_name='Coleus').first())

    def test_common_name_getter(self):
        """Return ._common_name.name."""
        seed = Seed()
        seed._common_name = CommonName(name='Coleus')
        self.assertEqual(seed.common_name, 'Coleus')

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

    def test_common_names_setter_iterable_containing_non_strings(self):
        """Raise a TypeError if iterable contains any non-string data."""
        seed = Seed()
        db.session.add(seed)
        with self.assertRaises(TypeError):
            seed.common_names = ['Coleus', 'Tomato', 42]
        with self.assertRaises(TypeError):
            seed.common_names = ('Coleus', 'Tomato', 41)

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

    def test_common_names_setter_not_iterable_or_string(self):
        """Raise a TypeError given data that is not str or iterable."""
        seed = Seed()
        db.session.add(seed)
        with self.assertRaises(TypeError):
            seed.common_names = 42
        with self.assertRaises(TypeError):
            seed.common_names = CommonName('Coleus')

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
                      [bn.botanical_name for bn in BotanicalName.query.all()])


if __name__ == '__main__':
    unittest.main()

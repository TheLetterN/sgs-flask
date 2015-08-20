import unittest
from app import create_app, db
from app.seeds.models import BotanicalName, Packet, Seed, UnitType


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

    def test_unit_type_getter(self):
        """Packet.unit_type returns Packet._unit_type.unit_type"""
        pkt = Packet()
        pkt._unit_type = UnitType('seeds')
        db.session.add(pkt)
        self.assertEqual(pkt.unit_type, 'seeds')

    def test_unit_type_setter_new_type(self):
        """create a new UnitType in the database if not already there."""
        pkt = Packet()
        pkt.unit_type = 'seeds'
        db.session.add(pkt)
        db.session.commit()
        self.assertEqual(UnitType.query.filter_by(unit_type='seeds').count(),
                         1)

    def test_unit_type_setter_existing_type(self):
        """Set the packet's unit_type to type from database if it exists."""
        pkt = Packet()
        pkt.unit_type = 'seeds'
        db.session.add(pkt)
        pkt2 = Packet()
        pkt2.unit_type = 'seeds'
        db.session.add(pkt)
        self.assertIsNot(pkt, pkt2)
        self.assertIs(pkt.unit_type, pkt2.unit_type)
        pkt3 = Packet()
        pkt3.unit_type = ('oz')
        db.session.add(pkt3)
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

    def test_add_botanical_name_same_as_botanical_name(self):
        """Use the same instance as _botanical_name if name is the same."""
        seed = Seed()
        seed.botanical_name = 'Asclepias incarnata'
        seed.add_botanical_name('Asclepias incarnata')
        self.assertIn(seed._botanical_name, seed._botanical_names.all())

    def test_add_botanical_name_no_duplicates_in_db(self):
        """There should only be one of each botanical name in the db."""
        seed1 = Seed()
        seed1.add_botanical_name('Asclepias incarnata')
        db.session.add(seed1)
        db.session.commit()
        seed2 = Seed()
        seed2.add_botanical_name('Asclepias incarnata')
        db.session.add(seed2)
        self.assertEqual(BotanicalName.query.count(), 1)
        self.assertIs(seed1._botanical_names.first(),
                      seed2._botanical_names.first())
        seed1.add_botanical_name('Echinacea purpurea')
        db.session.add(seed1)
        self.assertEqual(seed1._botanical_names.count(), 2)
        self.assertEqual(seed2._botanical_names.count(), 1)

    def test_add_botanical_name_no_duplicates_in_botanical_names(self):
        """If botanical_names has not been comitted, don't add duplicates.

        Adding multiples of the same botanical name to a seed that has not
        yet been committed to the database should not cause an attempt to
        add duplicates to the database.
        """
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        seed.add_botanical_name('Echinacea purpurea')
        db.session.add(seed)
        self.assertEqual(seed._botanical_names.count(), 2)

    def test_add_botanical_name_new(self):
        """Adds a new botanical name if not already in db."""
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        db.session.add(seed)
        self.assertEqual(BotanicalName.query.count(), 1)
        print(seed._botanical_names.first().botanical_name)
        self.assertEqual(seed._botanical_names.filter_by(
            _botanical_name='Asclepias incarnata').count(), 1)
        seed.add_botanical_name('Echinacea purpurea')
        db.session.add(seed)
        self.assertEqual(BotanicalName.query.count(), 2)
        self.assertEqual(seed._botanical_names.count(), 2)
        self.assertEqual(seed._botanical_names.filter_by(
            _botanical_name='Echinacea purpurea').count(), 1)

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

    def test_botanical_names_setter_string(self):
        """Clear _botanical_names and add the name assigned."""
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        db.session.add(seed)
        seed.botanical_names = 'Echinacea purpurea'
        self.assertIn('Echinacea purpurea', seed.botanical_names)
        self.assertNotIn('Asclepias incarnata', seed.botanical_names)

    def test_clear_botanical_names_removes_names(self):
        """Remove all botanical names from seed and return # of removed."""
        seed = Seed()
        seed.add_botanical_name('Asclepias incarnata')
        seed.add_botanical_name('Echinacea purpurea')
        seed.add_botanical_name('Digitalis lanata')
        db.session.add(seed)
        self.assertEqual(seed.clear_botanical_names(), 3)
        self.assertEqual(seed._botanical_names.count(), 0)
        self.assertEqual(BotanicalName.query.count(), 3)

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

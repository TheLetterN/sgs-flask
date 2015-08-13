import unittest
from app import create_app, db
from app.seeds.models import Packet, UnitType


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


if __name__ == '__main__':
    unittest.main()

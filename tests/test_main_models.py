import unittest
from app.main.models import Category, CommonName, Seed


class TestCategory(unittest.TestCase):
    """Unit tests for Category in app/main/models."""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_repr(self):
        """Category.__repr__ should return "<Category 'Category.name'>"."""
        gorycat = Category()
        gorycat.name = 'Undead'
        self.assertEqual(repr(gorycat), '<Category \'Undead\'>')


class TestCommonName(unittest.TestCase):
    """Unit tests for CommonName in app/main/models."""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_repr(self):
        """CommonName.__repr__ returns "<CommonName 'CommonName.name'>"."""
        cn = CommonName()
        cn.name = 'Bob'
        self.assertEqual(repr(cn), '<CommonName \'Bob\'>')


class TestSeed(unittest.TestCase):
    """Unit tests for Seed in app/main/models."""
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_repr(self):
        """Seed.__repr__ returns "<Seed 'Seed.name'>"."""
        seed = Seed()
        seed.name = 'Groot'
        self.assertEqual(repr(seed), '<Seed \'Groot\'>')


if __name__ == '__main__':
    unittest.main()

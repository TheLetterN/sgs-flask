import unittest
from app import create_app
from app.seeds.forms import (
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm
)
from app.seeds.models import BotanicalName, Category, CommonName


class TestEditBotanicalNameForm(unittest.TestCase):
    """Test custom methods of EditBotanicalNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_populate(self):
        """Populate form from a BotanicalName object."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        form = EditBotanicalNameForm()
        form.populate(bn)
        self.assertEqual(form.name.data, bn.name)


class TestEditCategoryForm(unittest.TestCase):
    """Test custom methods of EditCategoryForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_populate(self):
        """Populate form from a Category object."""
        category = Category()
        category.category = 'Annual Flowers'
        category.description = 'Not really built to last.'
        form = EditCategoryForm()
        form.populate(category)
        self.assertEqual(form.category.data, category.category)
        self.assertEqual(form.description.data, category.description)


class TestEditCommonNameForm(unittest.TestCase):
    """Test custom methods of EditCommonNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_populate(self):
        """Populate form from CommonName object."""
        cn = CommonName()
        cn.name = 'Coleus'
        cn.description = 'Not mint.'
        form = EditCommonNameForm()
        form.populate(cn)
        self.assertEqual(cn.name, form.name.data)
        self.assertEqual(cn.description, form.description.data)

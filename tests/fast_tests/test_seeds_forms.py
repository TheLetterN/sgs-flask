import unittest
from wtforms import ValidationError
from app import create_app
from app.seeds.forms import AddCommonNameForm, EditBotanicalNameForm, \
    EditCategoryForm, EditCommonNameForm
from app.seeds.models import BotanicalName, Category, CommonName


class TestAddCommonNameForm(unittest.TestCase):
    """Test custom methods of AddCommonNameForm."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_validate_additional_categories(self):
        """Raise ValidationError if contains category > 64 characters."""
        form = AddCommonNameForm()
        form.additional_categories.data = 'Animal, Mineral, Vegetable'
        form.validate_additional_categories(form.additional_categories)
        form.additional_categories.data = 'Sixty-four characters is a lot ' + \
            'more than you would expect it to be.'
        with self.assertRaises(ValidationError):
            form.validate_additional_categories(form.additional_categories)

    def test_validate_categories(self):
        """Raise ValidationError if categories & additional_categories empty.
        """
        form = AddCommonNameForm()
        with self.assertRaises(ValidationError):
            form.validate_categories(form.categories)
        form.categories.data = [42]
        form.validate_categories(form.categories)
        form.categories.data = []
        with self.assertRaises(ValidationError):
            form.validate_categories(form.categories)
        form.additional_categories.data = 'Not Nothing'
        form.validate_categories(form.categories)


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

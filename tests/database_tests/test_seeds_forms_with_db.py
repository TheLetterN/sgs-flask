import unittest
from wtforms import ValidationError
from app import create_app, db
from app.seeds.forms import AddCategoryForm, EditCategoryForm, \
    SelectCategoryForm
from app.seeds.models import Category


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

    def test_load_categories(self):
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
        form.load_categories()
        self.assertIn((cat1.id, cat1.category), form.categories.choices)
        self.assertIn((cat2.id, cat2.category), form.categories.choices)
        self.assertIn((cat3.id, cat3.category), form.categories.choices)


if __name__ == '__main__':
    unittest.main()

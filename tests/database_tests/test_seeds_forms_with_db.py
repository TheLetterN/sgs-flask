import unittest
from wtforms import ValidationError
from app import create_app, db
from app.seeds.forms import AddBotanicalNameForm, AddCategoryForm, \
    AddCommonNameForm, botanical_name_select_list, category_select_list, \
    common_name_select_list, EditBotanicalNameForm, EditCategoryForm, \
    EditCommonNameForm, SelectBotanicalNameForm, SelectCategoryForm, \
    SelectCommonNameForm
from app.seeds.models import BotanicalName, Category, CommonName


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
        self.assertIn((cn1.id, cn1.name), form.add_common_names.choices)
        self.assertIn((cn2.id, cn2.name), form.add_common_names.choices)
        self.assertIn((cn3.id, cn3.name), form.add_common_names.choices)
        self.assertIn((cn1.id, cn1.name), form.remove_common_names.choices)
        self.assertIn((cn2.id, cn2.name), form.remove_common_names.choices)
        self.assertIn((cn3.id, cn3.name), form.remove_common_names.choices)


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
        """Set add/remove categories with Categories from the db."""
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
        self.assertIn((cat1.id, cat1.category), form.add_categories.choices)
        self.assertIn((cat2.id, cat2.category), form.add_categories.choices)
        self.assertIn((cat3.id, cat3.category), form.add_categories.choices)
        self.assertIn((cat1.id, cat1.category), form.remove_categories.choices)
        self.assertIn((cat2.id, cat2.category), form.remove_categories.choices)
        self.assertIn((cat3.id, cat3.category), form.remove_categories.choices)


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


if __name__ == '__main__':
    unittest.main()

import io
import os
import unittest
from decimal import Decimal
from flask import current_app, url_for
from unittest import mock
from app import create_app, db
from app.auth.models import Permission, User
from app.seeds.models import BotanicalName, Category, CommonName, Image, \
    Price, QtyInteger, Seed, Unit
from tests.database_tests.test_auth_views_with_db import login


def seed_manager():
    """Generate a user with MANAGE_SEEDS permission.

    Returns:
        User: A confirmed user with MANAGE_SEEDS permission.
    """
    user = User()
    user.name = 'AzureDiamond'
    user.set_password('hunter2')
    user.email = 'gullible@bash.org'
    user.confirmed = True
    user.grant_permission(Permission.MANAGE_SEEDS)
    return user


class TestAddBotanicalNameRouteWithDB(unittest.TestCase):
    """Test seeds.add_botanical_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_botanical_name_adds_to_database(self):
        """Add a botanical name to the db on successful form submission."""
        user = seed_manager()
        db.session.add(user)
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Butterfly Weed'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_botanical_name'),
                         data=dict(name='Asclepias incarnata',
                                   common_names=[cn.id]),
                         follow_redirects=True)
        bn = BotanicalName.query.filter_by(name='Asclepias incarnata').first()
        self.assertIsNotNone(bn)
        self.assertIn(cn, bn.common_names)
        self.assertIn('has been added to the database', str(rv.data))

    def test_add_botanical_name_renders_page(self):
        """Render the Add Botanical Name page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_botanical_name'),
                        follow_redirects=True)
        self.assertIn('Add Botanical Name', str(rv.data))


class TestAddCategoryRouteWithDB(unittest.TestCase):
    """Test seeds.add_category."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_category_adds_to_database(self):
        """Add new Category to the database on successful form submit."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_category'),
                         data=dict(category='Perennial Flower',
                                   description='Built to last.'),
                         follow_redirects=True)
        cat = Category.query.filter_by(category='Perennial Flower').first()
        self.assertEqual(cat.category, 'Perennial Flower')
        self.assertEqual(cat.description, 'Built to last.')
        self.assertIn('has been added to the database', str(rv.data))

    def test_add_category_renders_page(self):
        """Render the Add Category page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_category'), follow_redirects=True)
        self.assertIn('Add Category', str(rv.data))


class TestAddCommonNameRouteWithDB(unittest.TestCase):
    """Test seeds.add_common_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_common_name_adds_additional_categories(self):
        """Add CommonName adds additional categories to db if present."""
        user = seed_manager()
        db.session.add(user)
        cat1 = Category()
        cat1.name = 'Annual Flower'
        db.session.add(cat1)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_common_name'),
                         data=dict(name='Foxglove',
                                   categories=[cat1.id],
                                   additional_categories='Vegetable, Herb',
                                   description='Foxy!'),
                         follow_redirects=True)
        cn = CommonName.query.filter_by(name='Foxglove').first()
        self.assertIsNotNone(cn)
        self.assertEqual(Category.query.count(), 3)
        self.assertIn('added to categories', str(rv.data))

    def test_add_common_name_adds_common_name_to_database(self):
        """Add CommonName to db on successful form submit."""
        user = seed_manager()
        db.session.add(user)
        cat = Category()
        db.session.add(cat)
        cat.category = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_common_name'),
                         data=dict(name='Foxglove',
                                   categories=[cat.id],
                                   description='Foxy!'),
                         follow_redirects=True)
        cn = CommonName.query.filter_by(name='Foxglove').first()
        self.assertIsNotNone(cn)
        self.assertIn(cat, cn.categories)
        self.assertIn('has been added to the database', str(rv.data))

    def test_add_common_name_renders_page(self):
        """"Render the Add Common Name page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_common_name'),
                        follow_redirects=True)
        self.assertIn('Add Common Name', str(rv.data))


class TestAddPacketRouteWithDB(unittest.TestCase):
    """Test seeds.add_packet."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_packet_no_seed_id(self):
        """Redirect to seeds.select_seed if no seed_id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet'))
        self.assertEqual(rv.location, url_for('seeds.select_seed',
                                              dest='seeds.add_packet',
                                              _external=True))

    def test_add_packet_success_redirect_with_again(self):
        """Redirect to seeds.add_packet w/ same seed_id if again selected."""
        user = seed_manager()
        seed = Seed()
        cn = CommonName()
        db.session.add_all([user, seed, cn])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        seed.common_name = cn
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_packet', seed_id=seed.id),
                         data=(dict(price='2.99',
                                    prices=0,
                                    quantity='100',
                                    quantities='0',
                                    unit='seeds',
                                    units=0,
                                    sku='8675309',
                                    again=True)))
        self.assertEqual(url_for('seeds.add_packet',
                                 seed_id=seed.id,
                                 _external=True),
                         rv.location)

    def test_add_packet_success_with_inputs(self):
        """Flash a message on successful submission with data in inputs."""
        user = seed_manager()
        seed = Seed()
        cn = CommonName()
        db.session.add_all([user, seed, cn])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        seed.common_name = cn
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_packet', seed_id=seed.id),
                         data=(dict(price='2.99',
                                    prices=0,
                                    quantity='100',
                                    quantities='0',
                                    unit='seeds',
                                    units=0,
                                    sku='8675309')),
                         follow_redirects=True)
        self.assertIn('Packet SKU 8675309', str(rv.data))

    def test_add_packet_success_with_selects(self):
        """Flash a message on successful submission with data in selects."""
        user = seed_manager()
        seed = Seed()
        cn = CommonName()
        price = Price()
        qty = QtyInteger()
        unit = Unit()
        db.session.add_all([user, seed, cn, price, qty, unit])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        price.price = Decimal('2.99')
        qty.value = 100
        unit.unit = 'seeds'
        seed.common_name = cn
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_packet', seed_id=seed.id),
                         data=dict(prices=price.id,
                                   price='',
                                   quantities='100',
                                   quantity='',
                                   units=unit.id,
                                   unit='',
                                   sku='8675309'),
                         follow_redirects=True)
        self.assertIn('Packet SKU 8675309', str(rv.data))

    def test_add_packet_renders_page(self):
        """Render form page given a valid seed_id."""
        user = seed_manager()
        seed = Seed()
        db.session.add_all([user, seed])
        seed.name = 'Foxy'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet', seed_id=seed.id))
        self.assertIn('Add a Packet', str(rv.data))


class TestAddSeedRouteWithDB(unittest.TestCase):
    """Test seeds.add_seed."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_add_seed_renders_page(self):
        """Render form page with no form data submitted."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_seed'))
        self.assertIn('Add Seed', str(rv.data))

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_seed_successful_submit(self, mock_save):
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_seed'),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_names=str(cn.id),
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg'),
                                   name='Foxy',
                                   description='Very foxy.'),
                         follow_redirects=True)
        self.assertIn('&#39;Digitalis purpurea&#39; added', str(rv.data))
        self.assertIn('&#39;Perennial Flower&#39; added', str(rv.data))
        self.assertIn('Thumbnail uploaded', str(rv.data))
        self.assertIn('New seed &#39;Foxy Foxglove&#39; has been',
                      str(rv.data))
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'foxy.jpg'))


class TestCategoryRouteWithDB(unittest.TestCase):
    """Test seeds.category."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_category_with_bad_slug(self):
        """Return the 404 page given a bad slug."""
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.category',
                                cat_slug='bad-slug-no-biscuit'),
                        follow_redirects=True)
            self.assertEqual(rv.status_code, 404)

    def test_category_with_valid_slug(self):
        """Return valid page given a valid category slug."""
        cat = Category()
        db.session.add(cat)
        cat.category = 'Annual Flower'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.category', cat_slug=cat.slug),
                        follow_redirects=True)
        self.assertIn('Annual Flower', str(rv.data))


class TestCommonNameRouteWithDB(unittest.TestCase):
    """Test seeds.common_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_common_name_bad_cat_slug(self):
        """Give a 404 page if given a malformed cat_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug='pewennial-flower',
                                cn_slug=cn.slug))
        self.assertEqual(rv.status_code, 404)

    def test_common_name_bad_cn_slug(self):
        """Give a 404 page if given a malformed cn_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug=cat.slug,
                                cn_slug='fawksglove'))
        self.assertEqual(rv.status_code, 404)

    def test_common_name_bad_slugs(self):
        """Give a 404 page if given malformed cn_slug and cat_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug='pewennial-flower',
                                cn_slug='fawksglove'))
        self.assertEqual(rv.status_code, 404)

    def test_common_name_renders_page(self):
        """Render page with common name info given valid slugs."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cn.description = 'Do foxes really wear these?'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug=cat.slug,
                                cn_slug=cn.slug))
        self.assertIn('Do foxes really wear these?', str(rv.data))


class TestEditBotanicalNameRouteWithDB(unittest.TestCase):
    """Test seeds.edit_botanical_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_edit_botanical_name_bad_id(self):
        """Redirect to seeds.select_botanical_name given a non-digit bn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location,
                         url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name',
                                 _external=True))
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'),
                        follow_redirects=True)
            self.assertIn('Error: Botanical name id must be an integer!',
                          str(rv.data))

    def test_edit_botanical_name_does_not_exist(self):
        """Redirect if bn_id does not correspond to a BotanicalName.id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location,
                         url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name',
                                 _external=True))
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42),
                        follow_redirects=True)
        self.assertIn('Error: No botanical name exists with that id!',
                      str(rv.data))

    def test_edit_botanical_name_no_changes(self):
        """Redirect to self and flash a message if no changes made."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        db.session.add_all([user, bn, cn])
        bn.name = 'Asclepias incarnata'
        cn.name = 'Butterly Weed'
        bn.common_names.append(cn)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name=bn.name,
                                   add_common_names=[cn.id]),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))

    def test_edit_botanical_name_no_id(self):
        """Redirect to seeds.select_botanical_name if given no bn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location,
                         url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name',
                                 _external=True))

    def test_edit_botanical_name_renders_page(self):
        """Render the page for editing botanical names given valid bn_id."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([bn, user])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                        follow_redirects=True)
        self.assertIn('Edit Botanical Name', str(rv.data))

    def test_edit_botanical_name_succesful_edit(self):
        """Push changes to db on successful edit of BotanicalName."""
        bn = BotanicalName()
        cn1 = CommonName()
        cn2 = CommonName()
        cn3 = CommonName()
        user = seed_manager()
        db.session.add_all([bn, cn1, cn2, cn3, user])
        bn.name = 'Asclepias incarnata'
        cn1.name = 'Butterfly Weed'
        cn2.name = 'Milkweed'
        cn3.name = 'Swamp Milkweed'
        bn.common_names.append(cn1)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name='Asclepias tuberosa',
                                   add_common_names=[cn2.id, cn3.id],
                                   remove_common_names=[cn1.id]),
                         follow_redirects=True)
        self.assertEqual(bn.name, 'Asclepias tuberosa')
        self.assertIn(cn2, bn.common_names)
        self.assertIn(cn3, bn.common_names)
        self.assertNotIn(cn1, bn.common_names)
        self.assertIn('changed to', str(rv.data))
        self.assertIn('added to common names', str(rv.data))
        self.assertIn('removed from common names', str(rv.data))


class TestEditCategoryRouteWithDB(unittest.TestCase):
    """Test seeds.edit_category."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_edit_category_bad_id(self):
        """Redirect if category_id is not an integer."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location, url_for('seeds.select_category',
                                              dest='seeds.edit_category',
                                              _external=True))
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id='frogs'),
                        follow_redirects=True)
        self.assertIn('Error: Category id must be an integer!', str(rv.data))

    def test_edit_category_does_not_exist(self):
        """Redirect if no Category.id corresponds with category_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=42))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location, url_for('seeds.select_category',
                                              dest='seeds.edit_category',
                                              _external=True))
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=42),
                        follow_redirects=True)
        self.assertIn('Error: No category exists with that id!', str(rv.data))

    def test_edit_category_no_changes(self):
        """Redirect to self and flash a message if no changes are made."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', category_id=cat.id),
                         data=dict(category=cat.category,
                                   description=cat.description),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))

    def test_edit_category_no_id(self):
        """Redirect to seeds.select_category if no category_id specified."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location, url_for('seeds.select_category',
                                              dest='seeds.edit_category',
                                              _external=True))

    def test_edit_category_renders_page(self):
        """Render the page for editing a category given valid category_id."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Vegetable'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=cat.id),
                        follow_redirects=True)
        self.assertIn('Edit Category', str(rv.data))

    def test_edit_category_successful_edit(self):
        """Change Category in db if edited successfully."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flowers'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', category_id=cat.id),
                         data=dict(category='Perennial Flowers',
                                   description='Built to last.'),
                         follow_redirects=True)
        self.assertEqual(cat.category, 'Perennial Flowers')
        self.assertEqual(cat.description, 'Built to last.')
        self.assertIn('Category changed from', str(rv.data))
        self.assertIn('description changed to', str(rv.data))


class TestEditCommonNameRouteWithDB(unittest.TestCase):
    """Test seeds.edit_common_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_edit_common_name_bad_id(self):
        """Redirect given a cn_id that isn't an integer."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location, url_for('seeds.select_common_name',
                                              dest='seeds.edit_common_name',
                                              _external=True))
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'),
                        follow_redirects=True)
        self.assertIn('Error: Common name id must be an integer!',
                      str(rv.data))

    def test_edit_common_name_no_changes(self):
        """Redirect to self and flash message if no changes made."""
        user = seed_manager()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, cn, cat])
        cn.name = 'Butterfly Weed'
        cn.description = 'Butterflies love this stuff.'
        cat.category = 'Perennial Flower'
        cn.categories.append(cat)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Butterfly Weed',
                                   description='Butterflies love this stuff.',
                                   add_categories=[cat.id]),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))

    def test_edit_common_name_no_id(self):
        """Redirect to seeds.select_common_name given no cn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv.location, url_for('seeds.select_common_name',
                                              dest='seeds.edit_common_name',
                                              _external=True))

    def test_edit_common_name_renders_page(self):
        """Render the page to edit common name given valid cn_id."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Butterfly Weed'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id=cn.id),
                        follow_redirects=True)
        self.assertIn('Edit Common Name', str(rv.data))

    def test_edit_common_name_successful_edit(self):
        """Change CommonName in database upon successful edit."""
        user = seed_manager()
        cn = CommonName()
        cat1 = Category()
        cat2 = Category()
        cat3 = Category()
        db.session.add_all([user, cn, cat1, cat2, cat3])
        cn.name = 'Butterfly Weed'
        cn.description = 'Butterflies _really_ like this.'
        cat1.category = 'Annual Flower'
        cat2.category = 'Vegetable'
        cat3.category = 'Herb'
        cn.categories.append(cat1)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Celery',
                                   description='Crunchy!',
                                   add_categories=[cat2.id, cat3.id],
                                   remove_categories=[cat1.id]),
                         follow_redirects=True)
        self.assertEqual(cn.name, 'Celery')
        self.assertNotIn(cat1, cn.categories)
        self.assertIn(cat2, cn.categories)
        self.assertIn(cat3, cn.categories)
        self.assertIn('Common name &#39;Butterfly Weed&#39;', str(rv.data))
        self.assertIn('added to categories', str(rv.data))
        self.assertIn('removed from categories', str(rv.data))
        self.assertIn('Description changed to', str(rv.data))


class TestEditSeedRouteWithDB(unittest.TestCase):
    """Test seeds.edit_seed."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_edit_seed_change_botanical_names(self):
        """Flash messages if botanical names are added or removed."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        bn2 = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, bn2, cat, cn])
        bn.name = 'Digitalis purpurea'
        bn2.name = 'Innagada davida'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn2.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('Added botanical name', str(rv.data))
        self.assertIn('Removed botanical name', str(rv.data))
        self.assertIn(bn2, seed.botanical_names)
        self.assertNotIn(bn, seed.botanical_names)

    def test_edit_seed_change_categories(self):
        """Flash messages if categories added or removed."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cat2 = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cat2, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        cat2.category = 'Plant'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat2.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('Added category', str(rv.data))
        self.assertIn('Removed category', str(rv.data))
        self.assertIn(cat2, seed.categories)
        self.assertNotIn(cat, seed.categories)

    def test_edit_seed_change_common_name(self):
        """Flash message if common name changed."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        cn2 = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn, cn2])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cn2.name = 'Vulpinemitten'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn2.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('Changed common name', str(rv.data))
        self.assertIs(seed.common_name, cn2)
        self.assertIsNot(seed.common_name, cn)

    def test_edit_seed_change_description(self):
        """Flash message if description changed."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description='Like a lady.',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('Changed description', str(rv.data))
        self.assertEqual(seed.description, 'Like a lady.')

    def test_edit_seed_change_name(self):
        """Flash message if name changed."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name='Fawksy',
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('Changed seed name', str(rv.data))
        self.assertEqual(seed.name, 'Fawksy')

    @mock.patch('werkzeug.FileStorage.save')
    def test_edit_seed_change_thumbnail(self, mock_save):
        """Flash message if thumbnail changed, and move old one to .images."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'fawksy.jpg')),
                         follow_redirects=True)
        self.assertIn('New thumbnail', str(rv.data))
        self.assertEqual(seed.thumbnail.filename, 'fawksy.jpg')
        self.assertIn(thumb, seed.images)
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'fawksy.jpg'))

    def test_edit_seed_no_changes(self):
        """Submission with no changes flashes relevant message."""
        user = seed_manager()
        seed = Seed()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        seed.categories.append(cat)
        seed.botanical_names.append(bn)
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))

    def test_edit_seed_no_seed(self):
        """Redirect to seeds.select_seed if no seed exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_seed', seed_id=42))
        self.assertEqual(rv.location, url_for('seeds.select_seed',
                                              dest='seeds.edit_seed',
                                              _external=True))

    def test_edit_seed_no_seed_id(self):
        """Redirect to seeds.select_seed if no id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_seed'))
        self.assertEqual(rv.location, url_for('seeds.select_seed',
                                              dest='seeds.edit_seed',
                                              _external=True))


class TestIndexRouteWithDB(unittest.TestCase):
    """Test seeds.index."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_index_renders_page(self):
        """seeds.index should render a page with no redirects."""
        with self.app.test_client() as tc:
            rv = tc.get(url_for('seeds.index'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(rv.location)


class TestManageRouteWithDB(unittest.TestCase):
    """Test seeds.manage."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_manage_renders_page(self):
        """Render the page with no redirects."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.manage'))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(rv.location)
        self.assertIn('Manage Seeds', str(rv.data))


class TestRemoveBotanicalNameRouteWithDB(unittest.TestCase):
    """Test seeds.manage."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_remove_botanical_name_bad_id(self):
        """Redirect given a non-integer bn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_botanical_name',
                                 dest='seeds.remove_botanical_name',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id='frogs'),
                        follow_redirects=True)
        self.assertIn('Error: Botanical name id must be an integer!',
                      str(rv.data))

    def test_remove_botanical_name_does_not_exist(self):
        """Redirect if no BotanicalName corresponds to bn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_botanical_name',
                                 dest='seeds.remove_botanical_name',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42),
                        follow_redirects=True)
        self.assertIn('Error: No such botanical name exists!', str(rv.data))

    def test_remove_botanical_name_no_id(self):
        """Redirect to seeds.select_botanical_name given no bn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_botanical_name',
                                 dest='seeds.remove_botanical_name',
                                 _external=True),
                         rv.location)

    def test_remove_botanical_name_not_verified(self):
        """Redirect to self and flash message if verify_removal unchecked."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''))
            self.assertEqual(rv.status_code, 302)
            self.assertEqual(url_for('seeds.remove_botanical_name',
                                     bn_id=bn.id,
                                     _external=True),
                             rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
            self.assertIn('No changes made', str(rv.data))

    def test_remove_botanical_name_renders_page(self):
        """Render seeds/remove_botanical_name.html with valid bn_id."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=bn.id))
        self.assertIn('Remove Botanical Name', str(rv.data))

    def test_remove_botanical_name_verified(self):
        """Delete BotanicalName from db if verify_removal checked."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        self.assertEqual(BotanicalName.query.count(), 1)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        self.assertEqual(BotanicalName.query.count(), 0)
        self.assertIn('has been removed from the database', str(rv.data))


class TestRemoveCategoryRouteWithDB(unittest.TestCase):
    """Test seeds.remove_category."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_remove_category_bad_id(self):
        """Redirect given a non-integer category_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_category',
                                 dest='seeds.remove_category',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id='frogs'),
                        follow_redirects=True)
        self.assertIn('Error: Category id must be an integer!', str(rv.data))

    def test_remove_category_does_not_exist(self):
        """Redirect if no Category corresponds to category_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=42))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_category',
                                 dest='seeds.remove_category',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=42),
                        follow_redirects=True)
        self.assertIn('Error: No such category exists.', str(rv.data))

    def test_remove_category_no_id(self):
        """Redirect to seeds.select_category if no category_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_category',
                                 dest='seeds.remove_category',
                                 _external=True),
                         rv.location)

    def test_remove_category_not_verified(self):
        """Redirect to self if verify_removal not checked."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Asclepias incarnata'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=''))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.remove_category',
                                 category_id=cat.id,
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))

    def test_remove_category_renders_page(self):
        """Render seeds/remove_category.html with valid category_id."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=cat.id))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Remove Category', str(rv.data))

    def test_remove_category_verified(self):
        """Remove Category from db if verify_removal is checked."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        self.assertEqual(Category.query.count(), 1)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        self.assertEqual(Category.query.count(), 0)
        self.assertIn('has been removed from the database', str(rv.data))


class TestRemoveCommonNameRouteWithDB(unittest.TestCase):
    """Test seeds.remove_common_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_remove_common_name_bad_id(self):
        """Redirect given a non-integer cn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_common_name',
                                 dest='seeds.remove_common_name',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'),
                        follow_redirects=True)
        self.assertIn('Common name id must be an integer!', str(rv.data))

    def test_remove_common_name_does_not_exist(self):
        """Redirect to select of no CommonName corresponds to cn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_common_name',
                                 dest='seeds.remove_common_name',
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42),
                        follow_redirects=True)
        self.assertIn('Error: No such common name exists', str(rv.data))

    def test_remove_common_name_no_id(self):
        """Redirect to seeds.select_common_name with no cn_id."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.select_common_name',
                                 dest='seeds.remove_common_name',
                                 _external=True),
                         rv.location)

    def test_remove_common_name_not_verified(self):
        """Redirect to self with flash if verify_removal not checked."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        self.assertEqual(CommonName.query.count(), 1)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=''))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.remove_common_name',
                                 cn_id=cn.id,
                                 _external=True),
                         rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        self.assertIn('No changes made', str(rv.data))
        self.assertEqual(CommonName.query.count(), 1)

    def test_remove_common_name_renders_page(self):
        """Render seeds/remove_common_name.html given valid cn_id."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=cn.id))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Remove Common Name', str(rv.data))

    def test_remove_common_name_verified(self):
        """Delete CommonName from db on successful submit."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        self.assertEqual(CommonName.query.count(), 1)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        self.assertIn('has been removed from the database', str(rv.data))
        self.assertEqual(CommonName.query.count(), 0)


class TestSelectBotanicalNameRouteWithDB(unittest.TestCase):
    """Test seeds.select_botanical_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_select_botanical_name_no_dest(self):
        """Redirect to seeds.manage if no dest given."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.manage', _external=True), rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name'),
                        follow_redirects=True)
        self.assertIn('Error: No destination', str(rv.data))

    def test_select_botanical_name_renders_page(self):
        """Render seeds/select_botanical_name.html given no form data."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Select Botanical Name', str(rv.data))

    def test_select_botanical_name_selected(self):
        """Redirect to dest if a botanical name is selected."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name'),
                         data=dict(names=bn.id))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.edit_botanical_name',
                                 bn_id=bn.id,
                                 _external=True),
                         rv.location)


class TestSelectCategoryRouteWithDB(unittest.TestCase):
    """Test seeds.select_category."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_select_category_no_dest(self):
        """Redirect to seeds.manage given no dest."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.manage', _external=True), rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category'),
                        follow_redirects=True)
        self.assertIn('Error: No destination', str(rv.data))

    def test_select_category_renders_page(self):
        """Render seeds/select_category.html given no form data."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Select Category', str(rv.data))

    def test_select_category_success(self):
        """Redirect to dest with category_id selected by form."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_category',
                                 dest='seeds.edit_category'),
                         data=dict(categories=cat.id))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.edit_category',
                                 category_id=cat.id,
                                 _external=True),
                         rv.location)


class TestSelectCommonNameRouteWithDB(unittest.TestCase):
    """Test seeds.select_common_name."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_select_common_name_no_dest(self):
        """Redirect to seeds.manage with an error if no dest given."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name'))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.manage', _external=True), rv.location)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name'),
                        follow_redirects=True)
        self.assertIn('Error: No destination', str(rv.data))

    def test_select_common_name_renders_page(self):
        """Render seeds/select_common_name.html given a dest."""
        user = seed_manager()
        db.session.add(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('Select Common Name', str(rv.data))

    def test_select_common_name_success(self):
        """Redirect to dest with cn_id selected by form."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_common_name',
                                 dest='seeds.edit_common_name'),
                         data=dict(names=cn.id))
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(url_for('seeds.edit_common_name',
                                 cn_id=cn.id,
                                 _external=True),
                         rv.location)


class TestSelectSeedRouteWithDB(unittest.TestCase):
    """Test seeds.select_seed."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_select_seed_no_dest(self):
        """Redirect to seeds.manage given no dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_seed'))
        self.assertEqual(rv.location, url_for('seeds.manage', _external=True))

    def test_select_seed_renders_page(self):
        """Render form page given a dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_seed', dest='seeds.add_packet'))
        self.assertIn('Select Seed', str(rv.data))

    def test_select_seed_successful_submission(self):
        """Redirect to dest on valid form submission."""
        user = seed_manager()
        seed = Seed()
        db.session.add_all([user, seed])
        seed.name = 'Foxy'
        db.session.commit()
        dest = 'seeds.add_packet'
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_seed', dest=dest),
                         data=dict(seeds=seed.id))
        self.assertEqual(url_for(dest, seed_id=str(seed.id), _external=True),
                         rv.location)


if __name__ == '__main__':
    unittest.main()

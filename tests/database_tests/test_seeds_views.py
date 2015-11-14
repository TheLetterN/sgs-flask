import io
import os
from decimal import Decimal
from flask import current_app, url_for
from unittest import mock
from app.auth.models import Permission, User
from app.seeds.models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Packet,
    Price,
    QtyInteger,
    Seed,
    Unit
)
from tests.database_tests.test_auth_views_with_db import login
from tests.conftest import app, db  # noqa


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


def foxy_seed():
    """Generate a Seed object based on Foxy Foxglove."""
    seed = Seed()
    seed.name = 'Foxy'
    seed.description = 'Not to be confused with that Hendrix song.'
    bn = BotanicalName()
    bn.name = 'Digitalis purpurea'
    seed.botanical_name = bn
    cat = Category()
    cat.category = 'Perennial Flower'
    seed.categories.append(cat)
    cn = CommonName()
    cn.name = 'Foxglove'
    seed.common_name = cn
    return seed


class TestAddBotanicalNameRouteWithDB:
    """Test seeds.add_botanical_name."""
    def test_add_botanical_name_adds_to_database(self, app, db):
        """Add a botanical name to the db on successful form submission."""
        user = seed_manager()
        db.session.add(user)
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Butterfly Weed'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_botanical_name'),
                         data=dict(name='Asclepias incarnata',
                                   common_names=cn.id),
                         follow_redirects=True)
        bn = BotanicalName.query.filter_by(name='Asclepias incarnata').first()
        assert bn is not None
        assert cn is bn.common_name
        assert '&#39;Asclepias incarnata&#39; has been added' in str(rv.data)

    def test_add_botanical_name_renders_page(self, app, db):
        """Render the Add Botanical Name page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_botanical_name'),
                        follow_redirects=True)
        assert 'Add Botanical Name' in str(rv.data)


class TestAddCategoryRouteWithDB:
    """Test seeds.add_category."""
    def test_add_category_adds_to_database(self, app, db):
        """Add new Category to the database on successful form submit."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_category'),
                         data=dict(category='Perennial Flower',
                                   description='Built to last.'),
                         follow_redirects=True)
        cat = Category.query.filter_by(category='Perennial Flower').first()
        assert cat.category == 'Perennial Flower'
        assert cat.description == 'Built to last.'
        assert 'has been added to the database' in str(rv.data)

    def test_add_category_renders_page(self, app, db):
        """Render the Add Category page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_category'), follow_redirects=True)
        assert 'Add Category' in str(rv.data)


class TestAddCommonNameRouteWithDB:
    """Test seeds.add_common_name."""
    def test_add_common_name_adds_common_name_to_database(self, app, db):
        """Add CommonName to db on successful form submit."""
        user = seed_manager()
        db.session.add(user)
        cat = Category()
        db.session.add(cat)
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_common_name'),
                         data=dict(name='Foxglove',
                                   parent_cn=0,
                                   categories=[cat.id],
                                   description='Foxy!'),
                         follow_redirects=True)
        cn = CommonName.query.filter_by(name='Foxglove').first()
        assert cn is not None
        assert cat in cn.categories
        assert '&#39;Foxglove&#39; has been added to' in str(rv.data)

    def test_add_common_name_renders_page(self, app, db):
        """"Render the Add Common Name page given no form data."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_common_name'),
                        follow_redirects=True)
        assert 'Add Common Name' in str(rv.data)


class TestAddPacketRouteWithDB:
    """Test seeds.add_packet."""
    def test_add_packet_no_seed_id(self, app, db):
        """Redirect to seeds.select_seed if no seed_id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet'))
        assert rv.location == url_for('seeds.select_seed',
                                      dest='seeds.add_packet',
                                      _external=True)

    def test_add_packet_success_redirect_with_again(self, app, db):
        """Redirect to seeds.add_packet w/ same seed_id if again selected."""
        user = seed_manager()
        seed = Seed()
        cn = CommonName()
        db.session.add_all([user, seed, cn])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        seed.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
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
        assert rv.location == url_for('seeds.add_packet',
                                      seed_id=seed.id,
                                      _external=True)

    def test_add_packet_success_with_inputs(self, app, db):
        """Flash a message on successful submission with data in inputs."""
        user = seed_manager()
        seed = Seed()
        cn = CommonName()
        db.session.add_all([user, seed, cn])
        seed.name = 'Foxy'
        cn.name = 'Foxglove'
        seed.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'Packet SKU 8675309' in str(rv.data)

    def test_add_packet_success_with_selects(self, app, db):
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
        with app.test_client() as tc:
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
        assert 'Packet SKU 8675309' in str(rv.data)

    def test_add_packet_renders_page(self, app, db):
        """Render form page given a valid seed_id."""
        user = seed_manager()
        seed = Seed()
        db.session.add_all([user, seed])
        seed.name = 'Foxy'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet', seed_id=seed.id))
        assert 'Add a Packet' in str(rv.data)


class TestAddSeedRouteWithDB:
    """Test seeds.add_seed."""
    def test_add_seed_renders_page(self, app, db):
        """Render form page with no form data submitted."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_seed'))
        assert 'Add Seed' in str(rv.data)

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_seed_successful_submit_in_stock_and_active(self,
                                                            mock_save,
                                                            app,
                                                            db):
        """Add seed and flash messages for added items."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_seed'),
                         data=dict(botanical_names=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_names=str(cn.id),
                                   in_stock='y',
                                   dropped='',
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg'),
                                   name='Foxy',
                                   description='Very foxy.'),
                         follow_redirects=True)
        assert '&#39;Perennial Flower&#39; added' in str(rv.data)
        assert '&#39;Foxy Foxglove&#39; is in stock' in str(rv.data)
        assert '&#39;Foxy Foxglove&#39; is currently active' in str(rv.data)
        assert 'Thumbnail uploaded' in str(rv.data)
        assert 'New seed &#39;Foxy Foxglove&#39; has been' in str(rv.data)
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'foxy.jpg'))

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_seed_successful_submit_no_stock_and_dropped(self,
                                                             mock_save,
                                                             app,
                                                             db):
        """Flash messages if seed is not in stock and has been dropped."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_seed'),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_names=str(cn.id),
                                   in_stock='',
                                   dropped='y',
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg'),
                                   name='Foxy',
                                   description='Very foxy.'),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is not in stock' in str(rv.data)
        assert '&#39;Foxy Foxglove&#39; is currently dropped/inactive' in\
            str(rv.data)


class TestCategoryRouteWithDB:
    """Test seeds.category."""
    def test_category_with_bad_slug(self, app, db):
        """Return the 404 page given a bad slug."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.category',
                                cat_slug='bad-slug-no-biscuit'),
                        follow_redirects=True)
        assert rv.status_code == 404

    def test_category_with_valid_slug(self, app, db):
        """Return valid page given a valid category slug."""
        cat = Category()
        db.session.add(cat)
        cat.category = 'Annual Flower'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.category', cat_slug=cat.slug),
                        follow_redirects=True)
        assert 'Annual Flower' in str(rv.data)


class TestCommonNameRouteWithDB:
    """Test seeds.common_name."""
    def test_common_name_bad_cat_slug(self, app, db):
        """Give a 404 page if given a malformed cat_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug='pewennial-flower',
                                cn_slug=cn.slug))
        assert rv.status_code == 404

    def test_common_name_bad_cn_slug(self, app, db):
        """Give a 404 page if given a malformed cn_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug=cat.slug,
                                cn_slug='fawksglove'))
        assert rv.status_code == 404

    def test_common_name_bad_slugs(self, app, db):
        """Give a 404 page if given malformed cn_slug and cat_slug."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug='pewennial-flower',
                                cn_slug='fawksglove'))
        assert rv.status_code == 404

    def test_common_name_renders_page(self, app, db):
        """Render page with common name info given valid slugs."""
        cn = CommonName()
        cat = Category()
        db.session.add_all([cn, cat])
        cn.name = 'Foxglove'
        cn.description = 'Do foxes really wear these?'
        cat.category = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug=cat.slug,
                                cn_slug=cn.slug))
        assert 'Do foxes really wear these?' in str(rv.data)


class TestEditBotanicalNameRouteWithDB:
    """Test seeds.edit_botanical_name."""
    def test_edit_botanical_name_bad_id(self, app, db):
        """Redirect to seeds.select_botanical_name given a non-digit bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'),
                        follow_redirects=True)
        assert 'Error: Botanical name id must be an integer!' in str(rv.data)

    def test_edit_botanical_name_does_not_exist(self, app, db):
        """Redirect if bn_id does not correspond to a BotanicalName.id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42),
                        follow_redirects=True)
        assert 'Error: No botanical name exists with that id!' in str(rv.data)

    def test_edit_botanical_name_no_changes(self, app, db):
        """Redirect to self and flash a message if no changes made."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        db.session.add_all([user, bn, cn])
        bn.name = 'Asclepias incarnata'
        cn.name = 'Butterly Weed'
        bn.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name=bn.name,
                                   common_names=[cn.id]),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_botanical_name_no_id(self, app, db):
        """Redirect to seeds.select_botanical_name if given no bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

    def test_edit_botanical_name_renders_page(self, app, db):
        """Render the page for editing botanical names given valid bn_id."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([bn, user])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                        follow_redirects=True)
        assert 'Edit Botanical Name' in str(rv.data)

    def test_edit_botanical_name_succesful_edit(self, app, db):
        """Push changes to db on successful edit of BotanicalName."""
        bn = BotanicalName()
        cn1 = CommonName()
        cn2 = CommonName()
        user = seed_manager()
        db.session.add_all([bn, cn1, cn2, user])
        bn.name = 'Asclepias incarnata'
        cn1.name = 'Butterfly Weed'
        cn2.name = 'Milkweed'
        bn.common_name = cn1
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name='Asclepias tuberosa',
                                   common_names=cn2.id),
                         follow_redirects=True)
        assert bn.name == 'Asclepias tuberosa'
        assert cn2 is bn.common_name
        assert 'Botanical name &#39;Asclepias incarnata&#39; changed to '\
            '&#39;Asclepias tuberosa&#39;.' in str(rv.data)
        assert 'Common name associated with botanical name &#39;Asclepias '\
            'tuberosa&#39; changed from &#39;Butterfly Weed&#39; to: '\
            '&#39;Milkweed&#39;.' in str(rv.data)


class TestEditCategoryRouteWithDB:
    """Test seeds.edit_category."""
    def test_edit_category_bad_id(self, app, db):
        """Redirect if category_id is not an integer."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.edit_category',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id='frogs'),
                        follow_redirects=True)
        assert 'Error: Category id must be an integer!' in str(rv.data)

    def test_edit_category_does_not_exist(self, app, db):
        """Redirect if no Category.id corresponds with category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=42))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.edit_category',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=42),
                        follow_redirects=True)
        assert 'Error: No category exists with that id!' in str(rv.data)

    def test_edit_category_no_changes(self, app, db):
        """Redirect to self and flash a message if no changes are made."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', category_id=cat.id),
                         data=dict(category=cat.category,
                                   description=cat.description),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_category_no_id(self, app, db):
        """Redirect to seeds.select_category if no category_id specified."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.edit_category',
                                      _external=True)

    def test_edit_category_renders_page(self, app, db):
        """Render the page for editing a category given valid category_id."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Vegetable'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=cat.id),
                        follow_redirects=True)
        assert 'Edit Category' in str(rv.data)

    def test_edit_category_successful_edit(self, app, db):
        """Change Category in db if edited successfully."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flowers'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', category_id=cat.id),
                         data=dict(category='Perennial Flowers',
                                   description='Built to last.'),
                         follow_redirects=True)
        assert cat.category == 'Perennial Flowers'
        assert cat.description == 'Built to last.'
        assert 'Category changed from' in str(rv.data)
        assert 'description changed to'in str(rv.data)


class TestEditCommonNameRouteWithDB:
    """Test seeds.edit_common_name."""
    def test_edit_common_name_bad_id(self, app, db):
        """Redirect given a cn_id that isn't an integer."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.edit_common_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'),
                        follow_redirects=True)
        assert 'Error: Common name id must be an integer!' in str(rv.data)

    def test_edit_common_name_no_changes(self, app, db):
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
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Butterfly Weed',
                                   description='Butterflies love this stuff.',
                                   categories=[cat.id],
                                   parent_cn=0),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_common_name_no_id(self, app, db):
        """Redirect to seeds.select_common_name given no cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.edit_common_name',
                                      _external=True)

    def test_edit_common_name_renders_page(self, app, db):
        """Render the page to edit common name given valid cn_id."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Butterfly Weed'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id=cn.id),
                        follow_redirects=True)
        assert 'Edit Common Name' in str(rv.data)

    def test_edit_common_name_successful_edit(self, app, db):
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
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Celery',
                                   description='Crunchy!',
                                   parent_cn=0,
                                   categories=[cat2.id, cat3.id]),
                         follow_redirects=True)
        assert cn.name == 'Celery'
        assert cat1 not in cn.categories
        assert cat2 in cn.categories
        assert cat3 in cn.categories
        assert 'Common name &#39;Butterfly Weed&#39;' in str(rv.data)
        assert 'added to categories' in str(rv.data)
        assert 'removed from categories' in str(rv.data)
        assert 'Description changed to' in str(rv.data)


class TestEditPacketRouteWithDB:
    """Test seeds.edit_packet."""
    def test_edit_packet_no_id(self, app, db):
        """Redirect to select_packet given no pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_packet'))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.edit_packet',
                                      _external=True)

    def test_edit_packet_no_packet(self, app, db):
        """Redirect and flash message if no packet exists with pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.edit_packet',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=42),
                        follow_redirects=True)
        assert 'packet was not found' in str(rv.data)

    def test_edit_packet_renders_page(self, app, db):
        """Render form page with valid pkt_id and no post data."""
        user = seed_manager()
        seed = Seed()
        packet = Packet()
        db.session.add_all([user, packet, seed])
        packet.price = Decimal('2.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        seed.name = 'Foxy'
        seed.common_name = CommonName(name='Foxglove')
        seed.packets.append(packet)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=packet.id))
        assert 'Edit Packet' in str(rv.data)

    def test_edit_packet_submission_change_inputs(self, app, db):
        """Change packet and flash message if new values present in inputs."""
        user = seed_manager()
        packet = Packet()
        db.session.add_all([user, packet])
        packet.price = Decimal('1.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                         data=dict(price='2.99',
                                   quantity='2.5',
                                   unit='grams',
                                   sku='BOUT350',
                                   prices=packet._price.id,
                                   quantities=str(packet.quantity),
                                   units=packet._unit.id),
                         follow_redirects=True)
        assert packet.price == Decimal('2.99')
        assert packet.quantity == Decimal('2.5')
        assert packet.unit == 'grams'
        assert packet.sku == 'BOUT350'
        assert 'Packet changed to: SKU BOUT350 - $2.99 for 2.5 grams' in\
            str(rv.data)

    def test_edit_packet_submission_change_selects(self, app, db):
        """Change packet and flash message if different values selected."""
        user = seed_manager()
        seed = Seed()
        pkt1 = Packet()
        pkt2 = Packet()
        db.session.add_all([user, seed, pkt1, pkt2])
        seed.name = 'Foxy'
        seed.common_name = CommonName(name='Foxglove')
        pkt1.price = Decimal('1.99')
        pkt2.price = Decimal('2.99')
        pkt1.quantity = 100
        pkt2.quantity = Decimal('2.5')
        pkt1.unit = 'seeds'
        pkt2.unit = 'grams'
        pkt1.sku = '8675309'
        pkt2.sku = 'BOUT350'
        seed.packets.append(pkt1)
        seed.packets.append(pkt2)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=pkt1.id),
                         data=dict(prices=pkt2._price.id,
                                   quantities=str(pkt2.quantity),
                                   units=pkt2._unit.id,
                                   sku=pkt1.sku),
                         follow_redirects=True)
        assert pkt1._price is pkt2._price
        assert pkt1.quantity == pkt2.quantity
        assert pkt1._unit is pkt2._unit
        assert 'Packet changed to: SKU 8675309 - $2.99 for 2.5 grams' in\
            str(rv.data)

    def test_edit_packet_submission_no_changes(self, app, db):
        """Flash a message if no changes are made in a form submission."""
        user = seed_manager()
        seed = Seed()
        packet = Packet()
        db.session.add_all([user, packet, seed])
        packet.price = Decimal('2.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        seed.name = 'Foxy'
        seed.common_name = CommonName(name='Foxglove')
        seed.packets.append(packet)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                         data=dict(prices=packet._price.id,
                                   quantities=str(packet.quantity),
                                   units=packet._unit.id,
                                   sku=packet.sku),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)


class TestEditSeedRouteWithDB:
    """Test seeds.edit_seed."""
    def test_edit_seed_change_botanical_name(self, app, db):
        """Flash messages if botanical name is changed."""
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=str(bn2.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert 'Changed botanical name' in str(rv.data)
        assert bn2 is seed.botanical_name

    def test_edit_seed_change_categories(self, app, db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'Added category' in str(rv.data)
        assert 'Removed category' in str(rv.data)
        assert cat2 in seed.categories
        assert cat not in seed.categories

    def test_edit_seed_change_common_name(self, app, db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'Changed common name' in str(rv.data)
        assert seed.common_name is cn2
        assert seed.common_name is not cn

    def test_edit_seed_change_description(self, app, db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'Changed description' in str(rv.data)
        assert seed.description == 'Like a lady.'

    def test_edit_seed_change_dropped(self, app, db):
        """Flash message if dropped status changed."""
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.in_stock = True
        seed.dropped = False
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   dropped='y',
                                   in_stock='y',
                                   name=seed.name,
                                   description='Like that Hendrix song.',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been dropped.' in str(rv.data)
        assert seed.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   dropped='',
                                   in_stock='y',
                                   name=seed.name,
                                   description='Like that Hendrix song.',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now active' in str(rv.data)
        assert not seed.dropped

    def test_edit_seed_change_in_stock(self, app, db):
        """Flash message if in_stock status changed."""
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.in_stock = False
        seed.dropped = False
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   dropped='',
                                   in_stock='y',
                                   name=seed.name,
                                   description='Like that Hendrix song.',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now in stock' in str(rv.data)
        assert seed.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=[str(bn.id)],
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   dropped='',
                                   in_stock='',
                                   name=seed.name,
                                   description='Like that Hendrix song.',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now out of stock' in str(rv.data)
        assert not seed.in_stock

    def test_edit_seed_change_name(self, app, db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'Changed seed name' in str(rv.data)
        assert seed.name == 'Fawksy'

    @mock.patch('werkzeug.FileStorage.save')
    def test_edit_seed_change_thumbnail(self,
                                        mock_save,
                                        app,
                                        db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
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
        assert 'New thumbnail' in str(rv.data)
        assert seed.thumbnail.filename == 'fawksy.jpg'
        assert thumb in seed.images
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'fawksy.jpg'))

    def test_edit_seed_no_changes(self, app, db):
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
        seed.botanical_name = bn
        seed.common_name = cn
        seed.in_stock = True
        seed.dropped = False
        seed.name = 'Foxy'
        seed.description = 'Like that Hendrix song.'
        seed.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_seed', seed_id=seed.id),
                         data=dict(botanical_names=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   in_stock='y',
                                   dropped='',
                                   name=seed.name,
                                   description=seed.description,
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_seed_no_seed(self, app, db):
        """Redirect to seeds.select_seed if no seed exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_seed', seed_id=42))
        assert rv.location == url_for('seeds.select_seed',
                                      dest='seeds.edit_seed',
                                      _external=True)

    def test_edit_seed_no_seed_id(self, app, db):
        """Redirect to seeds.select_seed if no id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_seed'))
        assert rv.location == url_for('seeds.select_seed',
                                      dest='seeds.edit_seed',
                                      _external=True)


class TestFlipDroppedRouteWithDB:
    """Test seeds.flip_dropped."""
    def test_flip_dropped_no_seed(self, app, db):
        """Return 404 if no seed exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', seed_id=42))
        assert rv.status_code == 404

    def test_flip_dropped_no_seed_id(self, app, db):
        """Return 404 if no seed_id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped'))
        assert rv.status_code == 404

    def test_flip_dropped_success(self, app, db):
        """Set dropped to the opposite of its current value and redirect."""
        user = seed_manager()
        seed = foxy_seed()
        seed.dropped = False
        db.session.add_all([seed, user])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', seed_id=seed.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert seed.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped',
                                seed_id=seed.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not seed.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', seed_id=seed.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been dropped.' in str(rv.data)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', seed_id=seed.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been returned to active' in\
            str(rv.data)


class TestFlipInStockRouteWithDB:
    """Test seeds.flip_in_stock."""
    def test_flip_in_stock_no_seed(self, app, db):
        """Return 404 if no seed exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', seed_id=42))
        assert rv.status_code == 404

    def test_flip_in_stock_no_seed_id(self, app, db):
        """Return 404 if no seed_id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock'))
        assert rv.status_code == 404

    def test_flip_in_stock_success(self, app, db):
        """Reverse value of in_stock and redirect on successful submit."""
        user = seed_manager()
        seed = foxy_seed()
        seed.in_stock = False
        db.session.add_all([seed, user])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', seed_id=seed.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert seed.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock',
                                seed_id=seed.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not seed.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', seed_id=seed.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now in stock' in str(rv.data)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', seed_id=seed.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now out of stock.' in str(rv.data)


class TestIndexRouteWithDB:
    """Test seeds.index."""
    def test_index_renders_page(self, app, db):
        """seeds.index should render a page with no redirects."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.index'))
        assert rv.status_code == 200
        assert rv.location is None


class TestManageRouteWithDB:
    """Test seeds.manage."""
    def test_manage_renders_page(self, app, db):
        """Render the page with no redirects."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.manage'))
        assert rv.status_code == 200
        assert rv.location is None
        assert 'Manage Seeds' in str(rv.data)


class TestRemoveBotanicalNameRouteWithDB:
    """Test seeds.manage."""
    def test_remove_botanical_name_bad_id(self, app, db):
        """Redirect given a non-integer bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id='frogs'),
                        follow_redirects=True)
        assert 'Error: Botanical name id must be an integer!' in str(rv.data)

    def test_remove_botanical_name_does_not_exist(self, app, db):
        """Redirect if no BotanicalName corresponds to bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42),
                        follow_redirects=True)
        assert 'Error: No such botanical name exists!' in str(rv.data)

    def test_remove_botanical_name_no_id(self, app, db):
        """Redirect to seeds.select_botanical_name given no bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

    def test_remove_botanical_name_not_verified(self, app, db):
        """Redirect to self and flash message if verify_removal unchecked."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.remove_botanical_name',
                                      bn_id=bn.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_botanical_name_renders_page(self, app, db):
        """Render seeds/remove_botanical_name.html with valid bn_id."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=bn.id))
        assert 'Remove Botanical Name' in str(rv.data)

    def test_remove_botanical_name_verified(self, app, db):
        """Delete BotanicalName from db if verify_removal checked."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        assert BotanicalName.query.count() == 1
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert BotanicalName.query.count() == 0
        assert 'has been removed from the database' in str(rv.data)


class TestRemoveCategoryRouteWithDB:
    """Test seeds.remove_category."""
    def test_remove_category_bad_id(self, app, db):
        """Redirect given a non-integer category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id='frogs'),
                        follow_redirects=True)
        assert 'Error: Category id must be an integer!' in str(rv.data)

    def test_remove_category_does_not_exist(self, app, db):
        """Redirect if no Category corresponds to category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=42))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=42),
                        follow_redirects=True)
        assert 'Error: No such category exists.' in str(rv.data)

    def test_remove_category_no_id(self, app, db):
        """Redirect to seeds.select_category if no category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)

    def test_remove_category_not_verified(self, app, db):
        """Redirect to self if verify_removal not checked."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=''))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.remove_category',
                                      category_id=cat.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_category_renders_page(self, app, db):
        """Render seeds/remove_category.html with valid category_id."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', category_id=cat.id))
        assert rv.status_code == 200
        assert 'Remove Category' in str(rv.data)

    def test_remove_category_verified(self, app, db):
        """Remove Category from db if verify_removal is checked."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        assert Category.query.count() == 1
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', category_id=cat.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert Category.query.count() == 0
        assert 'has been removed from the database' in str(rv.data)


class TestRemoveCommonNameRouteWithDB:
    """Test seeds.remove_common_name."""
    def test_remove_common_name_bad_id(self, app, db):
        """Redirect given a non-integer cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'),
                        follow_redirects=True)
        assert 'Common name id must be an integer!' in str(rv.data)

    def test_remove_common_name_does_not_exist(self, app, db):
        """Redirect to select of no CommonName corresponds to cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42),
                        follow_redirects=True)
        assert 'Error: No such common name exists' in str(rv.data)

    def test_remove_common_name_no_id(self, app, db):
        """Redirect to seeds.select_common_name with no cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_not_verified(self, app, db):
        """Redirect to self with flash if verify_removal not checked."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        assert CommonName.query.count() == 1
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=''))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.remove_common_name',
                                      cn_id=cn.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)
        assert CommonName.query.count() == 1

    def test_remove_common_name_renders_page(self, app, db):
        """Render seeds/remove_common_name.html given valid cn_id."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=cn.id))
        assert rv.status_code == 200
        assert 'Remove Common Name' in str(rv.data)

    def test_remove_common_name_verified(self, app, db):
        """Delete CommonName from db on successful submit."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        assert CommonName.query.count(), 1
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'has been removed from the database' in str(rv.data)
        assert CommonName.query.count() == 0


class TestRemovePacketRouteWithDB:
    """Test seeds.remove_packet."""
    def test_remove_packet_no_id(self, app, db):
        """Redirect to select_packet given no pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_packet',
                                dest='seeds.remove_packet'))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.remove_packet',
                                      _external=True)

    def test_remove_packet_no_packet(self, app, db):
        """Flash error and redirect if no packet corresponds to pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.remove_packet',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=42),
                        follow_redirects=True)
        assert 'Error: No packet exists' in str(rv.data)

    def test_remove_packet_renders_page(self, app, db):
        """Render form page given a valid packet id."""
        user = seed_manager()
        packet = Packet()
        db.session.add_all([packet, user])
        packet.price = Decimal('1.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=packet.id))
        assert 'Remove Packet' in str(rv.data)

    def test_remove_packet_submission_no_changes(self, app, db):
        """Redirect and flash a message if verify_removal unchecked."""
        user = seed_manager()
        packet = Packet()
        db.session.add_all([packet, user])
        packet.price = Decimal('1.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=None))
        assert rv.location in url_for('seeds.remove_packet',
                                      pkt_id=packet.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=None),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_packet_submission_verified(self, app, db):
        """Delete packet and flash a message if verify_removal is checked."""
        user = seed_manager()
        packet = Packet()
        db.session.add_all([packet, user])
        packet.price = Decimal('1.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'Packet SKU 8675309: $1.99 for 100 seeds has'\
            ' been removed from the database' in str(rv.data)
        assert Packet.query.count() == 0


class TestRemoveSeedRouteWithDB:
    """Test seeds.remove_seed."""
    @mock.patch('app.seeds.models.Image.delete_file')
    def test_remove_seed_delete_images_deletes_images(self,
                                                      mock_delete,
                                                      app,
                                                      db):
        """Delete images and thumbnail if delete_images is checked."""
        user = seed_manager()
        seed = foxy_seed()
        img = Image()
        img.filename = 'foxee.jpg'
        thumb = Image()
        thumb.filename = 'foxy.jpg'
        seed.images.append(img)
        seed.thumbnail = thumb
        db.session.add_all([user, seed])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_seed', seed_id=seed.id),
                         data=dict(verify_removal=True, delete_images=True),
                         follow_redirects=True)
        assert 'Image file &#39;foxee.jpg&#39; deleted' in str(rv.data)
        assert 'Thumbnail image &#39;foxy.jpg&#39; has' in str(rv.data)
        assert Image.query.count() == 0
        assert mock_delete.called

    @mock.patch('app.seeds.models.Image.delete_file', side_effect=OSError)
    def test_remove_seed_delete_images_no_file(self,
                                               mock_delete,
                                               app,
                                               db):
        """Flash errors if OSError raised trying to delete images.
        Do not remove images from the database if files can't be deleted.
        """
        user = seed_manager()
        seed = foxy_seed()
        img = Image()
        img.filename = 'foxee.jpg'
        thumb = Image()
        thumb.filename = 'foxy.jpg'
        seed.images.append(img)
        seed.thumbnail = thumb
        db.session.add_all([user, seed])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_seed', seed_id=seed.id),
                         data=dict(verify_removal=True, delete_images=True),
                         follow_redirects=True)
        assert 'Error: Attempting to delete &#39;foxee.jpg&#39;' in\
            str(rv.data)
        assert 'Error: Attempting to delete &#39;foxy.jpg&#39;' in\
            str(rv.data)
        assert 'Error: Seed could not be deleted', str(rv.data)
        assert img in seed.images
        assert thumb is seed.thumbnail
        assert Image.query.count() == 2
        assert mock_delete.called

    def test_remove_seed_deletes_seed(self, app, db):
        """Delete seed from the database on successful submission."""
        user = seed_manager()
        seed = foxy_seed()
        db.session.add_all([user, seed])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_seed', seed_id=seed.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'The seed &#39;Foxy Foxglove&#39; has been deleted' in\
            str(rv.data)
        assert Seed.query.count() == 0

    def test_remove_seed_no_id(self, app, db):
        """Redirect to seeds.select_seed given no seed_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_seed'))
        assert rv.location == url_for('seeds.select_seed',
                                      dest='seeds.remove_seed',
                                      _external=True)

    def test_remove_seed_no_seed(self, app, db):
        """Redirect to seeds.select_seed if no seed exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_seed', seed_id=42))
        assert rv.location == url_for('seeds.select_seed',
                                      dest='seeds.remove_seed',
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_seed', seed_id=42),
                        follow_redirects=True)
        assert 'Error: No seed exists with that id' in str(rv.data)

    def test_remove_seed_not_verified(self, app, db):
        """Redirect and flash message if verify_removal not checked."""
        user = seed_manager()
        seed = foxy_seed()
        db.session.add_all([user, seed])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_seed', seed_id=seed.id),
                         data=dict(verify_removal=None))
        assert rv.location == url_for('seeds.remove_seed',
                                      seed_id=seed.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_seed', seed_id=seed.id),
                         data=dict(verify_removal=None),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_seed_renders_page(self, app, db):
        """Render remove seed form page given valid seed id."""
        user = seed_manager()
        seed = foxy_seed()
        db.session.add_all([user, seed])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_seed', seed_id=seed.id))
        assert 'Remove Seed' in str(rv.data)


class TestSeedRouteWithDB:
    """Test seeds.seed."""
    def test_seed_bad_slugs(self, app, db):
        """Return 404 if any slug given does not correspond to a db entry."""
        cat = Category()
        cn = CommonName()
        seed = Seed()
        db.session.add_all([cat, cn, seed])
        cat.category = 'Perennial Flower'
        cn.name = 'Foxglove'
        seed.name = 'Foxy'
        seed.categories.append(cat)
        seed.common_name = cn
        seed.description = 'Like that Hendrix song.'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug=cat.slug,
                                cn_slug=cn.slug,
                                seed_slug='no-biscuit'))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug='no_biscuit',
                                cn_slug=cn.slug,
                                seed_slug=seed.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug=cat.slug,
                                cn_slug='no-biscuit',
                                seed_slug=seed.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug='no-biscuit',
                                cn_slug='no-biscuit',
                                seed_slug='no-biscuit'))
        assert rv.status_code == 404

    def test_seed_slugs_not_in_seed(self, app, db):
        """Return 404 if slugs return db entries, but entry not in seed."""
        cat1 = Category()
        cat2 = Category()
        cn1 = CommonName()
        cn2 = CommonName()
        seed = Seed()
        db.session.add_all([cat1, cat2, cn1, cn2, seed])
        cat1.category = 'Perennial Flower'
        cat2.category = 'Long Hair'
        cn1.name = 'Foxglove'
        cn2.name = 'Persian'
        seed.name = 'Foxy'
        seed.categories.append(cat1)
        seed.common_name = cn1
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug=cat1.slug,
                                cn_slug=cn2.slug,
                                seed_slug=seed.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug=cat2.slug,
                                cn_slug=cn1.slug,
                                seed_slug=seed.slug))
        assert rv.status_code == 404

    def test_seed_renders_page(self, app, db):
        """Render page given valid slugs."""
        seed = foxy_seed()
        db.session.add(seed)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.seed',
                                cat_slug=seed.categories[0].slug,
                                cn_slug=seed.common_name.slug,
                                seed_slug=seed.slug))
        assert 'Foxy Foxglove' in str(rv.data)


class TestSelectBotanicalNameRouteWithDB:
    """Test seeds.select_botanical_name."""
    def test_select_botanical_name_no_dest(self, app, db):
        """Redirect to seeds.manage if no dest given."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_botanical_name_renders_page(self, app, db):
        """Render seeds/select_botanical_name.html given no form data."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
        assert rv.status_code == 200
        assert 'Select Botanical Name' in str(rv.data)

    def test_select_botanical_name_selected(self, app, db):
        """Redirect to dest if a botanical name is selected."""
        user = seed_manager()
        bn = BotanicalName()
        db.session.add_all([user, bn])
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name'),
                         data=dict(names=bn.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_botanical_name',
                                      bn_id=bn.id,
                                      _external=True)


class TestSelectCategoryRouteWithDB:
    """Test seeds.select_category."""
    def test_select_category_no_dest(self, app, db):
        """Redirect to seeds.manage given no dest."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_category_renders_page(self, app, db):
        """Render seeds/select_category.html given no form data."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
        assert rv.status_code == 200
        assert 'Select Category' in str(rv.data)

    def test_select_category_success(self, app, db):
        """Redirect to dest with category_id selected by form."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.category = 'Annual Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_category',
                                 dest='seeds.edit_category'),
                         data=dict(categories=cat.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_category',
                                      category_id=cat.id,
                                      _external=True)


class TestSelectCommonNameRouteWithDB:
    """Test seeds.select_common_name."""
    def test_select_common_name_no_dest(self, app, db):
        """Redirect to seeds.manage with an error if no dest given."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_common_name_renders_page(self, app, db):
        """Render seeds/select_common_name.html given a dest."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
        assert rv.status_code == 200
        assert 'Select Common Name' in str(rv.data)

    def test_select_common_name_success(self, app, db):
        """Redirect to dest with cn_id selected by form."""
        user = seed_manager()
        cn = CommonName()
        db.session.add_all([user, cn])
        cn.name = 'Coleus'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_common_name',
                                 dest='seeds.edit_common_name'),
                         data=dict(names=cn.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_common_name',
                                      cn_id=cn.id,
                                      _external=True)


class TestSelectPacketRouteWithDB:
    """Test seeds.select_packet."""
    def test_select_packet_no_dest(self, app, db):
        """Flash an error and redirect if no dest specified."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_packet'))
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_packet'),
                        follow_redirects=True)
        assert 'No destination' in str(rv.data)

    def test_select_packet_renders_page(self, app, db):
        """Render form page if given a dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
        assert 'Select Packet' in str(rv.data)

    def test_select_packet_valid_submission(self, app, db):
        """Redirect to dest given valid selection."""
        seed = Seed()
        packet = Packet()
        user = seed_manager()
        db.session.add_all([seed, packet, user])
        seed.name = 'Foxy'
        seed.common_name = CommonName(name='Foxglove')
        seed.packets.append(packet)
        packet.price = Decimal('1.99')
        packet.quantity = 100
        packet.unit = 'seeds'
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_packet',
                                 dest='seeds.edit_packet'),
                         data=dict(packets=packet.id))
        assert rv.location == url_for('seeds.edit_packet',
                                      pkt_id=packet.id,
                                      _external=True)


class TestSelectSeedRouteWithDB:
    """Test seeds.select_seed."""
    def test_select_seed_no_dest(self, app, db):
        """Redirect to seeds.manage given no dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_seed'))
        assert rv.location == url_for('seeds.manage', _external=True)

    def test_select_seed_renders_page(self, app, db):
        """Render form page given a dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_seed', dest='seeds.add_packet'))
        assert 'Select Seed' in str(rv.data)

    def test_select_seed_successful_submission(self, app, db):
        """Redirect to dest on valid form submission."""
        user = seed_manager()
        seed = Seed()
        db.session.add_all([user, seed])
        seed.name = 'Foxy'
        db.session.commit()
        dest = 'seeds.add_packet'
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_seed', dest=dest),
                         data=dict(seeds=seed.id))
        assert rv.location == url_for(dest, seed_id=str(seed.id),
                                      _external=True)

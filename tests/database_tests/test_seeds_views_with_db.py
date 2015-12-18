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
    Quantity,
    Cultivar
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


def foxy_cultivar():
    """Generate a Cultivar object based on Foxy Foxglove."""
    cultivar = Cultivar()
    cultivar.name = 'Foxy'
    cultivar.description = 'Not to be confused with that Hendrix song.'
    bn = BotanicalName()
    bn.name = 'Digitalis purpurea'
    cultivar.botanical_name = bn
    cat = Category()
    cat.name = 'Perennial Flower'
    cultivar.categories.append(cat)
    cn = CommonName()
    cn.name = 'Foxglove'
    cn.categories.append(cat)
    cultivar.common_name = cn
    return cultivar


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
                                   common_name=cn.id),
                         follow_redirects=True)
        bn = BotanicalName.query.filter_by(name='Asclepias incarnata').first()
        assert bn is not None
        assert cn is bn.common_name
        assert 'Botanical name &#39;Asclepias incarnata&#39;' in str(rv.data)

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
        cat = Category.query.filter_by(name='Perennial Flower').first()
        assert cat.name == 'Perennial Flower'
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
        cat.name = 'Perennial Flower'
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
    def test_add_packet_no_cv_id(self, app, db):
        """Redirect to seeds.select_cultivar if no cv_id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.add_packet',
                                      _external=True)

    def test_add_packet_success_redirect_with_again(self, app, db):
        """Redirect to seeds.add_packet w/ same cv_id if again selected."""
        user = seed_manager()
        cultivar = Cultivar()
        cn = CommonName()
        db.session.add_all([user, cultivar, cn])
        cultivar.name = 'Foxy'
        cn.name = 'Foxglove'
        cultivar.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_packet', cv_id=cultivar.id),
                         data=(dict(price='2.99',
                                    prices=0,
                                    quantity='100',
                                    quantities='0',
                                    unit='seeds',
                                    units=0,
                                    sku='8675309',
                                    again=True)))
        assert rv.location == url_for('seeds.add_packet',
                                      cv_id=cultivar.id,
                                      _external=True)

    def test_add_packet_success_with_inputs(self, app, db):
        """Flash a message on successful submission with data in inputs."""
        user = seed_manager()
        cultivar = Cultivar()
        cn = CommonName()
        db.session.add_all([user, cultivar, cn])
        cultivar.name = 'Foxy'
        cn.name = 'Foxglove'
        cultivar.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_packet', cv_id=cultivar.id),
                         data=(dict(price='2.99',
                                    quantity='100',
                                    units='seeds',
                                    sku='8675309')),
                         follow_redirects=True)
        assert 'Packet SKU #8675309' in str(rv.data)

    def test_add_packet_renders_page(self, app, db):
        """Render form page given a valid cv_id."""
        user = seed_manager()
        cultivar = Cultivar()
        db.session.add_all([user, cultivar])
        cultivar.name = 'Foxy'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_packet', cv_id=cultivar.id))
        assert 'Add a Packet' in str(rv.data)


class TestAddCultivarRouteWithDB:
    """Test seeds.add_cultivar."""
    def test_add_cultivar_renders_page(self, app, db):
        """Render form page with no form data submitted."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.add_cultivar'))
        assert 'Add Cultivar' in str(rv.data)

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_cultivar_successful_submit_in_stock_and_active(self,
                                                                mock_save,
                                                                app,
                                                                db):
        """Add cultivar and flash messages for added items."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cat.name = 'Perennial Flower'
        cn.name = 'Foxglove'
        cn.categories.append(cat)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_cultivar'),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description='Very foxy.',
                                   dropped='',
                                   in_stock='y',
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg'),
                                   name='Foxy'),
                         follow_redirects=True)
        assert '&#39;Perennial Flower&#39; added' in str(rv.data)
        assert '&#39;Foxy Foxglove&#39; is in stock' in str(rv.data)
        assert '&#39;Foxy Foxglove&#39; is currently active' in str(rv.data)
        assert 'Thumbnail uploaded' in str(rv.data)
        assert 'New cultivar &#39;Foxy Foxglove&#39; has been' in str(rv.data)
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'foxy.jpg'))

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_cultivar_successful_submit_no_stock_and_dropped(self,
                                                                 mock_save,
                                                                 app,
                                                                 db):
        """Flash messages if cultivar is not in stock and has been dropped."""
        user = seed_manager()
        bn = BotanicalName()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, bn, cn, cat])
        bn.name = 'Digitalis purpurea'
        cat.name = 'Perennial Flower'
        cn.name = 'Foxglove'
        cn.categories.append(cat)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.add_cultivar'),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description='Very foxy.',
                                   dropped='y',
                                   in_stock='',
                                   name='Foxy',
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
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
        cat.name = 'Annual Flower'
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
        cat.name = 'Perennial Flower'
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
        cat.name = 'Perennial Flower'
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
        cat.name = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                cat_slug=cat.slug,
                                cn_slug=cn.slug))
        assert 'Do foxes really wear these?' in str(rv.data)


class TestCultivarRouteWithDB:
    """Test seeds.cultivar."""
    def test_cultivar_bad_slugs(self, app, db):
        """Return 404 if any slug given does not correspond to a db entry."""
        cat = Category()
        cn = CommonName()
        cultivar = Cultivar()
        db.session.add_all([cat, cn, cultivar])
        cat.name = 'Perennial Flower'
        cn.name = 'Foxglove'
        cultivar.name = 'Foxy'
        cultivar.categories.append(cat)
        cultivar.common_name = cn
        cultivar.description = 'Like that Hendrix song.'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug=cat.slug,
                                cn_slug=cn.slug,
                                cv_slug='no-biscuit'))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug='no_biscuit',
                                cn_slug=cn.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug=cat.slug,
                                cn_slug='no-biscuit',
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug='no-biscuit',
                                cn_slug='no-biscuit',
                                cv_slug='no-biscuit'))
        assert rv.status_code == 404

    def test_cv_slugs_not_in_cultivar(self, app, db):
        """Return 404 if slugs return db entries, but entry not in cultivar."""
        cat1 = Category()
        cat2 = Category()
        cn1 = CommonName()
        cn2 = CommonName()
        cultivar = Cultivar()
        db.session.add_all([cat1, cat2, cn1, cn2, cultivar])
        cat1.name = 'Perennial Flower'
        cat2.name = 'Long Hair'
        cn1.name = 'Foxglove'
        cn2.name = 'Persian'
        cultivar.name = 'Foxy'
        cultivar.categories.append(cat1)
        cultivar.common_name = cn1
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug=cat1.slug,
                                cn_slug=cn2.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug=cat2.slug,
                                cn_slug=cn1.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404

    def test_cultivar_renders_page(self, app, db):
        """Render page given valid slugs."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        print(cultivar.categories[0].slug)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                cat_slug=cultivar.categories[0].slug,
                                cn_slug=cultivar.common_name.slug,
                                cv_slug=cultivar.slug))
        assert 'Foxy Foxglove' in str(rv.data)


class TestEditBotanicalNameRouteWithDB:
    """Test seeds.edit_botanical_name."""
    def test_edit_botanical_name_bad_id(self, app, db):
        """Redirect to seeds.select_botanical_name given a non-digit bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

    def test_edit_botanical_name_does_not_exist(self, app, db):
        """Redirect if bn_id does not correspond to a BotanicalName.id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

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
                                   common_name=[cn.id]),
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
                                   common_name=cn2.id),
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
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.edit_category',
                                      _external=True)

    def test_edit_category_does_not_exist(self, app, db):
        """Redirect if no Category.id corresponds with category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', category_id=42))
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.edit_category',
                                      _external=True)

    def test_edit_category_no_changes(self, app, db):
        """Redirect to self and flash a message if no changes are made."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.name = 'Annual Flower'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', cat_id=cat.id),
                         data=dict(category=cat.name,
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
        cat.name = 'Vegetable'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_category', cat_id=cat.id),
                        follow_redirects=True)
        assert 'Edit Category' in str(rv.data)

    def test_edit_category_successful_edit(self, app, db):
        """Change Category in db if edited successfully."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.name = 'Annual Flowers'
        cat.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_category', cat_id=cat.id),
                         data=dict(category='Perennial Flowers',
                                   description='Built to last.'),
                         follow_redirects=True)
        assert cat.name == 'Perennial Flowers'
        assert cat.description == 'Built to last.'
        assert 'Category changed from' in str(rv.data)
        assert 'Description for &#39;Perennial Flowers&#39; changed to' in\
            str(rv.data)


class TestEditCommonNameRouteWithDB:
    """Test seeds.edit_common_name."""
    def test_edit_common_name_bad_id(self, app, db):
        """Redirect given a cn_id that isn't an integer."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.edit_common_name',
                                      _external=True)

    def test_edit_common_name_no_changes(self, app, db):
        """Redirect to self and flash message if no changes made."""
        user = seed_manager()
        cn = CommonName()
        cat = Category()
        db.session.add_all([user, cn, cat])
        cn.name = 'Butterfly Weed'
        cn.description = 'Butterflies love this stuff.'
        cat.name = 'Perennial Flower'
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
        cat1.name = 'Annual Flower'
        cat2.name = 'Vegetable'
        cat3.name = 'Herb'
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
        assert 'Description for &#39;Celery&#39; changed' in str(rv.data)


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
        """Redirect to select if no packet exists with pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.edit_packet',
                                      _external=True)

    def test_edit_packet_renders_page(self, app, db):
        """Render form page with valid pkt_id and no post data."""
        user = seed_manager()
        cultivar = Cultivar()
        packet = Packet()
        db.session.add_all([user, packet, cultivar])
        packet.price = Decimal('2.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
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
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                         data=dict(price='2.99',
                                   quantity='2.5',
                                   units='grams',
                                   sku='BOUT350'),
                         follow_redirects=True)
        assert packet.price == Decimal('2.99')
        assert packet.quantity.value == Decimal('2.5')
        assert packet.quantity.units == 'grams'
        assert packet.sku == 'BOUT350'
        assert 'Packet changed to: SKU #BOUT350: $2.99 for 2.5 grams' in\
            str(rv.data)

    def test_edit_packet_submission_no_changes(self, app, db):
        """Flash a message if no changes are made in a form submission."""
        user = seed_manager()
        cultivar = Cultivar()
        packet = Packet()
        db.session.add_all([user, packet, cultivar])
        packet.price = Decimal('2.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                         data=dict(price=packet.price,
                                   quantity=str(packet.quantity.value),
                                   units=packet.quantity.units,
                                   sku=packet.sku),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)


class TestEditCultivarRouteWithDB:
    """Test seeds.edit_cultivar."""
    def test_edit_cultivar_change_botanical_name(self, app, db):
        """Flash messages if botanical name is changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        bn2 = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, bn2, cat, cn])
        bn.name = 'Digitalis purpurea'
        bn2.name = 'Innagada davida'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn2.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed botanical name' in str(rv.data)
        assert bn2 is cultivar.botanical_name

    def test_edit_cultivar_change_categories(self, app, db):
        """Flash messages if categories added or removed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cat2 = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cat2, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        cat2.name = 'Plant'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cn.categories.append(cat2)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat2.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Added category' in str(rv.data)
        assert 'Removed category' in str(rv.data)
        assert cat2 in cultivar.categories
        assert cat not in cultivar.categories

    def test_edit_cultivar_change_common_name(self, app, db):
        """Flash message if common name changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        cn2 = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn, cn2])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cn2.name = 'Vulpinemitten'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cn2.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn2.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed common name' in str(rv.data)
        assert cultivar.common_name is cn2
        assert cultivar.common_name is not cn

    def test_edit_cultivar_change_description(self, app, db):
        """Flash message if description changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description='Like a lady.',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed description' in str(rv.data)
        assert cultivar.description == 'Like a lady.'

    def test_edit_cultivar_change_dropped(self, app, db):
        """Flash message if dropped status changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.in_stock = True
        cultivar.dropped = False
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   dropped='y',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been dropped.' in str(rv.data)
        assert cultivar.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   dropped='',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now active' in str(rv.data)
        assert not cultivar.dropped

    def test_edit_cultivar_change_in_stock(self, app, db):
        """Flash message if in_stock status changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.in_stock = False
        cultivar.dropped = False
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   dropped='',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now in stock' in str(rv.data)
        assert cultivar.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description='Like that Hendrix song.',
                                   dropped='',
                                   in_stock='',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now out of stock' in str(rv.data)
        assert not cultivar.in_stock

    def test_edit_cultivar_change_name(self, app, db):
        """Flash message if name changed."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name='Fawksy',
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed cultivar name' in str(rv.data)
        assert cultivar.name == 'Fawksy'

    @mock.patch('werkzeug.FileStorage.save')
    def test_edit_cultivar_change_thumbnail(self,
                                            mock_save,
                                            app,
                                            db):
        """Flash message if thumbnail changed, and move old one to .images."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'fawksy.jpg')),
                         follow_redirects=True)
        assert 'New thumbnail' in str(rv.data)
        assert cultivar.thumbnail.filename == 'fawksy.jpg'
        assert thumb in cultivar.images
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'fawksy.jpg'))

    def test_edit_cultivar_no_changes(self, app, db):
        """Submission with no changes flashes relevant message."""
        user = seed_manager()
        cultivar = Cultivar()
        bn = BotanicalName()
        cat = Category()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([user, bn, cat, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cat.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.categories.append(cat)
        cultivar.botanical_name = bn
        cn.categories.append(cat)
        cultivar.common_name = cn
        cultivar.in_stock = True
        cultivar.dropped = False
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   categories=[str(cat.id)],
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   dropped='',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        print(rv.data)
        assert 'No changes made' in str(rv.data)

    def test_edit_cultivar_no_cultivar(self, app, db):
        """Redirect to seeds.select_cultivar if no cultivar w/ given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_cultivar', cv_id=42))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.edit_cultivar',
                                      _external=True)

    def test_edit_cultivar_no_cv_id(self, app, db):
        """Redirect to seeds.select_cultivar if no id given."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.edit_cultivar'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.edit_cultivar',
                                      _external=True)


class TestFlipDroppedRouteWithDB:
    """Test seeds.flip_dropped."""
    def test_flip_dropped_no_cultivar(self, app, db):
        """Return 404 if no cultivar exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=42))
        assert rv.status_code == 404

    def test_flip_dropped_no_cv_id(self, app, db):
        """Return 404 if no cv_id given."""
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
        cultivar = foxy_cultivar()
        cultivar.dropped = False
        db.session.add_all([cultivar, user])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert cultivar.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped',
                                cv_id=cultivar.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not cultivar.dropped
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been dropped.' in str(rv.data)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; has been returned to active' in\
            str(rv.data)


class TestFlipInStockRouteWithDB:
    """Test seeds.flip_in_stock."""
    def test_flip_in_stock_no_cultivar(self, app, db):
        """Return 404 if no cultivar exists with given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=42))
        assert rv.status_code == 404

    def test_flip_in_stock_no_cv_id(self, app, db):
        """Return 404 if no cv_id given."""
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
        cultivar = foxy_cultivar()
        cultivar.in_stock = False
        db.session.add_all([cultivar, user])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert cultivar.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock',
                                cv_id=cultivar.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not cultivar.in_stock
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '&#39;Foxy Foxglove&#39; is now in stock' in str(rv.data)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id),
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
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

    def test_remove_botanical_name_does_not_exist(self, app, db):
        """Redirect if no BotanicalName corresponds to bn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

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
            rv = tc.get(url_for('seeds.remove_category', cat_id='frogs'))
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)

    def test_remove_category_does_not_exist(self, app, db):
        """Redirect if no Category corresponds to category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', cat_id=42))
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)

    def test_remove_category_no_id(self, app, db):
        """Redirect to seeds.select_category if no category_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category'))
        assert rv.location == url_for('seeds.select_category',
                                      dest='seeds.remove_category',
                                      _external=True)

    def test_remove_category_not_verified(self, app, db):
        """Redirect to self if verify_removal not checked."""
        user = seed_manager()
        cat = Category()
        cat2 = Category()
        db.session.add_all([user, cat, cat2])
        cat.name = 'Annual Flower'
        cat2.name = 'Herb'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', cat_id=cat.id),
                         data=dict(verify_removal='', move_to=cat2.id))
        assert rv.location == url_for('seeds.remove_category',
                                      cat_id=cat.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', cat_id=cat.id),
                         data=dict(verify_removal='', move_to=cat2.id),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_category_renders_page(self, app, db):
        """Render seeds/remove_category.html with valid category_id."""
        user = seed_manager()
        cat = Category()
        db.session.add_all([user, cat])
        cat.name = 'Annual Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_category', cat_id=cat.id))
        assert rv.status_code == 200
        assert 'Remove Category' in str(rv.data)

    def test_remove_category_verified(self, app, db):
        """Remove Category from db if verify_removal is checked."""
        user = seed_manager()
        cat = Category()
        cat2 = Category()
        db.session.add_all([user, cat, cat2])
        cat.name = 'Annual Flower'
        cat2.name = 'Herb'
        db.session.commit()
        assert cat in Category.query.all()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_category', cat_id=cat.id),
                         data=dict(verify_removal=True, move_to=cat2.id),
                         follow_redirects=True)
        assert cat not in Category.query.all()
        assert 'has been removed from the database' in str(rv.data)


class TestRemoveCommonNameRouteWithDB:
    """Test seeds.remove_common_name."""
    def test_remove_common_name_bad_id(self, app, db):
        """Redirect to select given a non-integer cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_does_not_exist(self, app, db):
        """Redirect to select if no CommonName corresponds to cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_no_id(self, app, db):
        """Redirect to seeds.select_common_name with no cn_id."""
        user = seed_manager()
        db.session.add(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_common_name'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_not_verified(self, app, db):
        """Redirect to self with flash if verify_removal not checked."""
        user = seed_manager()
        cn = CommonName()
        cn2 = CommonName()
        db.session.add_all([user, cn, cn2])
        cn.name = 'Coleus'
        cn2.name = 'Kingus'
        db.session.commit()
        assert cn in CommonName.query.all()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal='', move_to=cn2.id))
        assert rv.location == url_for('seeds.remove_common_name',
                                      cn_id=cn.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal='', move_to=cn2.id),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)
        assert cn in CommonName.query.all()

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
        cn2 = CommonName()
        db.session.add_all([user, cn, cn2])
        cn.name = 'Coleus'
        cn2.name = 'Kingus'
        db.session.commit()
        assert cn in CommonName.query.all()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=True, move_to=cn2.id),
                         follow_redirects=True)
        assert 'has been removed from the database' in str(rv.data)
        assert cn not in CommonName.query.all()


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
        """Redirect back to select if no packet corresponds to pkt_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.remove_packet',
                                      _external=True)

    def test_remove_packet_renders_page(self, app, db):
        """Render form page given a valid packet id."""
        user = seed_manager()
        packet = Packet()
        db.session.add_all([packet, user])
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
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
        packet.quantity = Quantity(value=100, units='seeds')
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
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'Packet SKU #8675309: $1.99 for 100 seeds has'\
            ' been removed from the database' in str(rv.data)
        assert Packet.query.count() == 0


class TestRemoveCultivarRouteWithDB:
    """Test seeds.remove_cultivar."""
    @mock.patch('app.seeds.models.Image.delete_file')
    def test_remove_cultivar_delete_images_deletes_images(self,
                                                          mock_delete,
                                                          app,
                                                          db):
        """Delete images and thumbnail if delete_images is checked."""
        user = seed_manager()
        cultivar = foxy_cultivar()
        img = Image()
        img.filename = 'foxee.jpg'
        thumb = Image()
        thumb.filename = 'foxy.jpg'
        cultivar.images.append(img)
        cultivar.thumbnail = thumb
        db.session.add_all([user, cultivar])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=True, delete_images=True),
                         follow_redirects=True)
        assert 'Image file &#39;foxee.jpg&#39; deleted' in str(rv.data)
        assert 'Thumbnail image &#39;foxy.jpg&#39; has' in str(rv.data)
        assert Image.query.count() == 0
        assert mock_delete.called

    def test_remove_cultivar_deletes_cultivar(self, app, db):
        """Delete cultivar from the database on successful submission."""
        user = seed_manager()
        cultivar = foxy_cultivar()
        db.session.add_all([user, cultivar])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'The cultivar &#39;Foxy Foxglove&#39; has been deleted' in\
            str(rv.data)
        assert Cultivar.query.count() == 0

    def test_remove_cultivar_no_id(self, app, db):
        """Redirect to seeds.select_cultivar given no cv_id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_cultivar'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.remove_cultivar',
                                      _external=True)

    def test_remove_cultivar_no_cultivar(self, app, db):
        """Redirect to seeds.select_cultivar if no cultivar w/ given id."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_cultivar', cv_id=42))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.remove_cultivar',
                                      _external=True)

    def test_remove_cultivar_not_verified(self, app, db):
        """Redirect and flash message if verify_removal not checked."""
        user = seed_manager()
        cultivar = foxy_cultivar()
        db.session.add_all([user, cultivar])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=None))
        assert rv.location == url_for('seeds.remove_cultivar',
                                      cv_id=cultivar.id,
                                      _external=True)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=None),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_cultivar_renders_page(self, app, db):
        """Render remove cultivar form page given valid cultivar id."""
        user = seed_manager()
        cultivar = foxy_cultivar()
        db.session.add_all([user, cultivar])
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.remove_cultivar', cv_id=cultivar.id))
        assert 'Remove Cultivar' in str(rv.data)


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
                         data=dict(botanical_name=bn.id))
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
        cat.name = 'Annual Flower'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_category',
                                 dest='seeds.edit_category'),
                         data=dict(category=cat.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_category',
                                      cat_id=cat.id,
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
                         data=dict(common_name=cn.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_common_name',
                                      cn_id=cn.id,
                                      _external=True)


class TestSelectCultivarRouteWithDB:
    """Test seeds.select_cultivar."""
    def test_select_cultivar_no_dest(self, app, db):
        """Redirect to seeds.manage given no dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_cultivar'))
        assert rv.location == url_for('seeds.manage', _external=True)

    def test_select_cultivar_renders_page(self, app, db):
        """Render form page given a dest."""
        user = seed_manager()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('seeds.select_cultivar',
                                dest='seeds.add_packet'))
        assert 'Select Cultivar' in str(rv.data)

    def test_select_seed_successful_submission(self, app, db):
        """Redirect to dest on valid form submission."""
        user = seed_manager()
        cultivar = Cultivar()
        db.session.add_all([user, cultivar])
        cultivar.name = 'Foxy'
        db.session.commit()
        dest = 'seeds.add_packet'
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_cultivar', dest=dest),
                         data=dict(cultivar=cultivar.id))
        assert rv.location == url_for(dest, cv_id=str(cultivar.id),
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
        cultivar = Cultivar()
        packet = Packet()
        user = seed_manager()
        db.session.add_all([cultivar, packet, user])
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('seeds.select_packet',
                                 dest='seeds.edit_packet'),
                         data=dict(packet=packet.id))
        assert rv.location == url_for('seeds.edit_packet',
                                      pkt_id=packet.id,
                                      _external=True)

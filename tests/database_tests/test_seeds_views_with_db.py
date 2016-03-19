import io
import os
from decimal import Decimal
from flask import current_app, url_for
from unittest import mock
from app.seeds.models import (
    BotanicalName,
    Index,
    CommonName,
    Cultivar,
    Image,
    Packet,
    Quantity,
    Series,
    Synonym
)


def foxy_cultivar():
    """Generate a Cultivar object based on Foxy Foxglove."""
    cultivar = Cultivar()
    cultivar.name = 'Foxy'
    cultivar.description = 'Not to be confused with that Hendrix song.'
    bn = BotanicalName()
    bn.name = 'Digitalis purpurea'
    cultivar.botanical_name = bn
    idx = Index()
    idx.name = 'Perennial Flower'
    cn = CommonName()
    cn.name = 'Foxglove'
    cn.index = idx
    cultivar.common_name = cn
    return cultivar


class TestAddCommonNameRouteWithDB:
    """Test seeds.add_common_name."""
    def test_add_common_name_blanks(self, app, db):
        """Set description and instructions to None if given a blank string."""
        idx = Index(name='Perennial Flower')
        db.session.add(idx)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.add_common_name', idx_id=idx.id),
                         data=dict(name='Foxglove',
                                   parent_cn=0,
                                   description='',
                                   instructions=''),
                         follow_redirects=True)
            cn = CommonName.query.filter_by(name='Foxglove').first()
            assert cn.description is None
            assert 'Description for' not in str(rv.data)

    def test_add_common_name_renders_page(self, app, db):
        """Render form page for add_common_name."""
        idx = Index(name='Perennial')
        db.session.add(idx)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_common_name', idx_id=idx.id))
        assert 'Add Common Name' in str(rv.data)


class TestAddBotanicalNameRouteWithDB:
    """Test seeds.add_botanical_name."""
    def test_add_botanical_name_renders_page(self, app, db):
        """Load form page given a valid cn_id."""
        cn = CommonName(name='Foxglove')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_botanical_name', cn_id=cn.id),
                        follow_redirects=True)
        assert 'Add Botanical Name' in str(rv.data)

    def test_add_botanical_name_bad_cn_id(self, app, db):
        """Redirect to select common name if CommonName can't be loaded."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_botanical_name'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_botanical_name',
                                      _external=True)
        cn = CommonName()
        cn.id = 1
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_botanical_name', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_botanical_name',
                                      _external=True)


class TestAddSeriesRouteWithDB:
    """Test add_series route."""
    def test_add_series_renders_page(self, app, db):
        """Load form page given a valid cn_id."""
        cn = CommonName(name='Foxglove')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_series', cn_id=cn.id))
            assert 'Add Series' in str(rv.data)

    def test_add_series_bad_cn_id(self, app, db):
        """Redirect to select_common_name if cn_id is invalid."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_series'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_series',
                                      _external=True)
        cn = CommonName(name='Foxglove')
        cn.id = 1
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_series', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_series',
                                      _external=True)


class TestAddCultivarRouteWithDB:
    """Test seeds.add_cultivar."""
    def test_add_cultivar_renders_page(self, app, db):
        """Load form page given a valid cn_id."""
        cn = CommonName(name='Foxglove')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_cultivar', cn_id=cn.id))
        assert 'Add Cultivar' in str(rv.data)

    def test_add_cultivar_bad_cn_id(self, app, db):
        """Redirect to select_common_name if cn_id is invalid."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_cultivar'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_cultivar',
                                      _external=True)
        cn = CommonName(name='Foxglove')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_cultivar', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_cultivar',
                                      _external=True)

    @mock.patch('werkzeug.FileStorage.save')
    def test_add_cultivar_successful_submit_no_stock_and_inactive(self,
                                                                  mock_save,
                                                                  app,
                                                                  db):
        """Flash messages if cultivar is not in stock and has been dropped."""
        bn = BotanicalName()
        cn = CommonName()
        idx = Index()
        db.session.add_all([bn, cn, idx])
        bn.name = 'Digitalis purpurea'
        idx.name = 'Perennial Flower'
        cn.name = 'Foxglove'
        cn.index = idx
        bn.common_names.append(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.add_cultivar', cn_id=cn.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   description='Very foxy.',
                                   active='',
                                   in_stock='',
                                   name='Foxy',
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is not in stock' in str(rv.data)
        assert '\\\'Foxy Foxglove\\\' is currently inactive' in\
            str(rv.data)


class TestAddPacketRouteWithDB:
    """Test seeds.add_packet."""
    def test_add_packet_bad_cv_id(self, app, db):
        """Redirect to seeds.select_cultivar if invalid cv_id given."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_packet', cv_id=42))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.add_packet',
                                      _external=True)

    def test_add_packet_success_redirect_with_again(self, app, db):
        """Redirect to seeds.add_packet w/ same cv_id if again selected."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.add_packet', cv_id=cultivar.id),
                         data=dict(price='2.99',
                                   prices=0,
                                   quantity='100',
                                   quantities='0',
                                   unit='seeds',
                                   units=0,
                                   sku='8675309',
                                   again=True))
        assert rv.location == url_for('seeds.add_packet',
                                      cv_id=cultivar.id,
                                      _external=True)

    def test_add_packet_successs_with_existing_quantity(self, app, db):
        """Load existing quantity if it has the same values as submitted."""
        cultivar = foxy_cultivar()
        qty = Quantity(value=100, units='seeds')
        db.session.add_all([cultivar, qty])
        db.session.commit()
        with app.test_client() as tc:
            tc.post(url_for('seeds.add_packet', cv_id=cultivar.id),
                    data=dict(price='2.99',
                              quantity='100',
                              units='seeds',
                              sku='8675309'))
        pkt = Packet.query.filter_by(sku='8675309').first()
        assert pkt.quantity is qty

    def test_add_packet_renders_page(self, app, db):
        """Render form page given a valid cv_id."""
        cultivar = Cultivar()
        db.session.add(cultivar)
        cultivar.name = 'Foxy'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_packet', cv_id=cultivar.id))
        assert 'Add a Packet' in str(rv.data)


class TestIndexRouteWithDB:
    """Test seeds.index."""
    def test_index_with_bad_slug(self, app, db):
        """Return the 404 page given a bad slug."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.index',
                                idx_slug='bad-slug-no-biscuit'),
                        follow_redirects=True)
        assert rv.status_code == 404

    def test_index_with_valid_slug(self, app, db):
        """Return valid page given a valid index slug."""
        idx = Index()
        db.session.add(idx)
        idx.name = 'Annual Flower'
        idx.description = 'Not really built to last.'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.index', idx_slug=idx.slug),
                        follow_redirects=True)
        assert 'Annual Flower' in str(rv.data)


class TestCommonNameRouteWithDB:
    """Test seeds.common_name."""
    def test_common_name_bad_idx_slug(self, app, db):
        """Give a 404 page if given a malformed idx_slug."""
        cn = CommonName()
        idx = Index()
        db.session.add_all([cn, idx])
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                idx_slug='pewennial-flower',
                                cn_slug=cn.slug))
        assert rv.status_code == 404

    def test_common_name_bad_cn_slug(self, app, db):
        """Give a 404 page if given a malformed cn_slug."""
        cn = CommonName()
        idx = Index()
        db.session.add_all([cn, idx])
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                idx_slug=idx.slug,
                                cn_slug='fawksglove'))
        assert rv.status_code == 404

    def test_common_name_bad_slugs(self, app, db):
        """Give a 404 page if given malformed cn_slug and idx_slug."""
        cn = CommonName()
        idx = Index()
        db.session.add_all([cn, idx])
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                idx_slug='pewennial-flower',
                                cn_slug='fawksglove'))
        assert rv.status_code == 404

    def test_common_name_renders_page(self, app, db):
        """Render page with common name info given valid slugs."""
        cn = CommonName()
        idx = Index()
        db.session.add_all([cn, idx])
        cn.name = 'Foxglove'
        cn.description = 'Do foxes really wear these?'
        idx.name = 'Perennial Flower'
        cn.index = idx
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.common_name',
                                idx_slug=idx.slug,
                                cn_slug=cn.slug))
        assert 'Do foxes really wear these?' in str(rv.data)


class TestCultivarRouteWithDB:
    """Test seeds.cultivar."""
    def test_cultivar_bad_slugs(self, app, db):
        """Return 404 if any slug given does not correspond to a db entry."""
        app.config['SHOW_CULTIVAR_PAGES'] = True
        idx = Index()
        cn = CommonName()
        cultivar = Cultivar()
        db.session.add_all([idx, cn, cultivar])
        idx.name = 'Perennial Flower'
        cn.name = 'Foxglove'
        cultivar.name = 'Foxy'
        cultivar.common_name = cn
        cultivar.description = 'Like that Hendrix song.'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug=idx.slug,
                                cn_slug=cn.slug,
                                cv_slug='no-biscuit'))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug='no_biscuit',
                                cn_slug=cn.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug=idx.slug,
                                cn_slug='no-biscuit',
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug='no-biscuit',
                                cn_slug='no-biscuit',
                                cv_slug='no-biscuit'))
        assert rv.status_code == 404

    def test_cv_slugs_not_in_cultivar(self, app, db):
        """Return 404 if slugs return db entries, but entry not in cultivar."""
        app.config['SHOW_CULTIVAR_PAGES'] = True
        idx1 = Index()
        idx2 = Index()
        cn1 = CommonName()
        cn2 = CommonName()
        cultivar = Cultivar()
        db.session.add_all([idx1, idx2, cn1, cn2, cultivar])
        idx1.name = 'Perennial Flower'
        idx2.name = 'Long Hair'
        cn1.name = 'Foxglove'
        cn2.name = 'Persian'
        cultivar.name = 'Foxy'
        cultivar.common_name = cn1
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug=idx1.slug,
                                cn_slug=cn2.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug=idx2.slug,
                                cn_slug=cn1.slug,
                                cv_slug=cultivar.slug))
        assert rv.status_code == 404

    def test_cultivar_renders_page(self, app, db):
        """Render page given valid slugs."""
        app.config['SHOW_CULTIVAR_PAGES'] = True
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.cultivar',
                                idx_slug=cultivar.common_name.index.slug,
                                cn_slug=cultivar.common_name.slug,
                                cv_slug=cultivar.slug))
        assert 'Foxy Foxglove' in str(rv.data)


class TestEditBotanicalNameRouteWithDB:
    """Test seeds.edit_botanical_name."""
    def test_edit_botanical_name_bad_id(self, app, db):
        """Redirect to seeds.select_botanical_name given a non-digit bn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id='frogs'))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

    def test_edit_botanical_name_does_not_exist(self, app, db):
        """Redirect if bn_id does not correspond to a BotanicalName.id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=42))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

    def test_edit_botanical_name_no_changes(self, app, db):
        """Redirect to self and flash a message if no changes made."""
        bn = BotanicalName()
        cn = CommonName()
        db.session.add_all([bn, cn])
        bn.name = 'Asclepias incarnata'
        cn.name = 'Butterly Weed'
        bn.common_name = cn
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name=bn.name,
                                   common_name=[cn.id]),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_botanical_name_no_id(self, app, db):
        """Redirect to seeds.select_botanical_name if given no bn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.edit_botanical_name',
                                      _external=True)

    def test_edit_botanical_name_renders_page(self, app, db):
        """Render the page for editing botanical names given valid bn_id."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                        follow_redirects=True)
        assert 'Edit Botanical Name' in str(rv.data)

    def test_edit_botanical_name_succesful_edit(self, app, db):
        """Push changes to db on successful edit of BotanicalName."""
        bn = BotanicalName()
        cn1 = CommonName()
        cn2 = CommonName()
        db.session.add_all([bn, cn1, cn2])
        bn.name = 'Asclepias incarnata'
        cn1.name = 'Butterfly Weed'
        cn2.name = 'Milkweed'
        bn.common_names = [cn1]
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name='Asclepias tuberosa',
                                   common_names=[cn2.id]),
                         follow_redirects=True)
        assert bn.name == 'Asclepias tuberosa'
        assert cn2 in bn.common_names
        assert cn1 not in bn.common_names
        assert 'Botanical name \\\'Asclepias incarnata\\\' changed to '\
            '\\\'Asclepias tuberosa\\\'.' in str(rv.data)
        assert 'Removed common name \\\'Butterfly Weed' in str(rv.data)
        assert 'Added common name \\\'Milkweed' in str(rv.data)

    def test_edit_botanical_name_clears_synonyms(self, app, db):
        """Clear synonyms if synonyms field is empty."""
        bn = BotanicalName(name='Digitalis purpurea')
        cn = CommonName(name='Foxglove')
        bn.common_name = cn
        bn.synonyms_string = 'Digitalis über alles'
        db.session.add_all([bn, cn])
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_botanical_name', bn_id=bn.id),
                         data=dict(name='Digitalis purpurea',
                                   common_name=cn.id,
                                   synonyms=''),
                         follow_redirects=True)
        assert 'Synonyms for \\\'Digitalis purpurea\\\' clea' in str(rv.data)


class TestEditIndexRouteWithDB:
    """Test seeds.edit_index."""
    def test_edit_index_bad_id(self, app, db):
        """Redirect if idx_id is not an integer."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_index', idx_id='frogs'))
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.edit_index',
                                      _external=True)

    def test_edit_index_does_not_exist(self, app, db):
        """Redirect if no Index.id corresponds with idx_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_index', idx_id=42))
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.edit_index',
                                      _external=True)

    def test_edit_index_no_changes(self, app, db):
        """Redirect to self and flash a message if no changes are made."""
        idx = Index(name='Annual Flower', description='Not built to last.')
        db.session.add(idx)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_index', idx_id=idx.id),
                         data=dict(id=idx.id,
                                   name=idx.name,
                                   description=idx.description),
                         follow_redirects=True)
        assert 'No changes to \\\'Annual Flower\\\' were made' in str(rv.data)

    def test_edit_index_no_id(self, app, db):
        """Redirect to seeds.select_index if no idx_id specified."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_index'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.edit_index',
                                      _external=True)

    def test_edit_index_renders_page(self, app, db):
        """Render the page for editing a index given valid idx_id."""
        idx = Index()
        db.session.add(idx)
        idx.name = 'Vegetable'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_index', idx_id=idx.id),
                        follow_redirects=True)
        assert 'Edit Index' in str(rv.data)

    def test_edit_index_suggests_redirect(self, app, db):
        """Flash a message linking to add_redirect if paths change."""
        app.config['SHOW_CULTIVAR_PAGES'] = True
        idx = Index(name='Perennial')
        cn = CommonName(name='Foxglove')
        cv = Cultivar(name='Foxy')
        idx.common_names.append(cn)
        cn.cultivars.append(cv)
        db.session.add_all([idx, cn, cv])
        db.session.commit()
        idx_slug = idx.slug
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_index', idx_id=idx.id),
                         data=dict(name='Perennial Flower'),
                         follow_redirects=True)
        assert url_for('seeds.common_name',
                       idx_slug=idx_slug,
                       cn_slug=cn.slug) in str(rv.data)
        assert idx_slug != idx.slug
        assert url_for('seeds.common_name',
                       idx_slug=idx.slug,
                       cn_slug=cn.slug) in str(rv.data)
        assert url_for('seeds.cultivar',
                       idx_slug=idx_slug,
                       cn_slug=cn.slug,
                       cv_slug=cv.slug) in str(rv.data)
        assert url_for('seeds.cultivar',
                       idx_slug=idx_slug,
                       cn_slug=cn.slug,
                       cv_slug=cv.slug) in str(rv.data)


class TestEditCommonNameRouteWithDB:
    """Test seeds.edit_common_name."""
    def test_edit_common_name_bad_id(self, app, db):
        """Redirect given a cn_id that isn't an integer."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_common_name', cn_id='frogs'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.edit_common_name',
                                      _external=True)

    def test_edit_common_name_blank_description_instructions(self, app, db):
        """Set description/instructions to none if it it is a blank string."""
        cn = CommonName(name='Foxglove',
                        description='Foxy!',
                        instructions='Put in ground')
        idx = Index(name='Perennial Flower')
        cn.index = idx
        db.session.add_all([cn, idx])
        db.session.commit()
        assert cn.description is not None
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Foxglove',
                                   index=idx.id,
                                   description='',
                                   instructions='',
                                   parent_cn=0),
                         follow_redirects=True)
        assert 'Description for \\\'Foxglove\\\' has been cleared'\
            in str(rv.data)
        assert cn.description is None
        assert 'Planting instructions for \\\'Foxglove\\\' have been clear'\
            in str(rv.data)

    def test_edit_common_name_clears_synonyms(self, app, db):
        """Clear synonyms if form field is blank."""
        cn = CommonName(name='Foxglove')
        cn.synonyms_string = 'Fauxglove'
        idx = Index('Flower')
        cn.index = idx
        db.session.add_all([cn, idx])
        db.session.commit()
        assert cn.synonyms_string == 'Fauxglove'
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Foxglove',
                                   index=idx.id,
                                   parent_cn=0,
                                   synonyms=''),
                         follow_redirects=True)
        assert 'Synonyms for \\\'Foxglove\\\' cleared' in str(rv.data)
        assert not cn.synonyms

    def test_edit_common_name_no_changes(self, app, db):
        """Redirect to self and flash message if no changes made."""
        cn = CommonName()
        idx = Index()
        db.session.add_all([cn, idx])
        cn.name = 'Butterfly Weed'
        cn.description = 'Butterflies love this stuff.'
        idx.name = 'Perennial Flower'
        cn.index = idx
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Butterfly Weed',
                                   description='Butterflies love this stuff.',
                                   index=idx.id,
                                   parent_cn=0),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_common_name_no_id(self, app, db):
        """Redirect to seeds.select_common_name given no cn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_common_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.edit_common_name',
                                      _external=True)

    def test_edit_common_name_renders_page(self, app, db):
        """Render the page to edit common name given valid cn_id."""
        cn = CommonName(name='Foxglove')
        cn.index = Index(name='Perennial')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_common_name', cn_id=cn.id),
                        follow_redirects=True)
        assert 'Edit Common Name' in str(rv.data)

    def test_edit_common_name_adds_parent(self, app, db):
        """Add parent if specified by form."""
        cn1 = CommonName(name='Dwarf Coleus')
        cn2 = CommonName(name='Coleus')
        idx = Index(name='Perennial Flower')
        cn1.index = idx
        cn2.index = idx
        db.session.add_all([cn1, cn2, idx])
        db.session.commit()
        assert not cn1.parent
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn1.id),
                         data=dict(name='Dwarf Coleus',
                                   index=idx.id,
                                   parent_cn=cn2.id),
                         follow_redirects=True)
        assert 'is now a subcategory of' in str(rv.data)
        assert cn1.parent == cn2

    def test_edit_common_name_changes_parent(self, app, db):
        """Replace parent if changed."""
        cn1 = CommonName(name='Dwarf Coleus')
        cn2 = CommonName(name='Plant')
        cn3 = CommonName(name='Coleus')
        idx = Index('Flower')
        cn1.index = idx
        cn2.index = idx
        cn3.index = idx
        cn1.parent = cn2
        db.session.add_all([cn1, cn2, cn3, idx])
        db.session.commit()
        assert cn1.parent == cn2
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn1.id),
                         data=dict(name='Dwarf Coleus',
                                   index=idx.id,
                                   parent_cn=cn3.id),
                         follow_redirects=True)
        assert 'is now a subcategory of' in str(rv.data)
        assert cn1.parent == cn3

    def test_edit_common_name_removes_parent(self, app, db):
        """Remove parent if 0 selected in parent_cn."""
        cn1 = CommonName(name='Dwarf Coleus')
        cn2 = CommonName(name='Coleus')
        idx = Index('Flower')
        cn1.index = idx
        cn2.index = idx
        cn1.parent = cn2
        db.session.add_all([cn1, cn2, idx])
        db.session.commit()
        assert cn1.parent == cn2
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn1.id),
                         data=dict(name='Dwarf Coleus',
                                   index=idx.id,
                                   parent_cn=0),
                         follow_redirects=True)
        assert 'is no longer a subcategory of any other' in str(rv.data)
        assert not cn1.parent

    def test_edit_common_name_recommends_redirects(self, app, db):
        """Flash messages recommending redirects be created if paths change."""
        cn = CommonName(name='Fauxglove')
        idx = Index(name='Perennial Flower')
        cv = Cultivar(name='Foxy')
        cn.index = idx
        cv.common_name = cn
        db.session.add_all([cn, idx, cv])
        db.session.commit()
        cn_slug = cn.slug
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Foxglove',
                                   index=idx.id,
                                   parent_cn=0),
                         follow_redirects=True)
        assert cn_slug != cn.slug
        assert url_for('seeds.common_name',
                       idx_slug=idx.slug,
                       cn_slug=cn_slug) in str(rv.data)
        assert url_for('seeds.common_name',
                       idx_slug=idx.slug,
                       cn_slug=cn.slug) in str(rv.data)
        assert url_for('seeds.cultivar',
                       idx_slug=idx.slug,
                       cn_slug=cn_slug,
                       cv_slug=cv.slug) in str(rv.data)
        assert url_for('seeds.cultivar',
                       idx_slug=idx.slug,
                       cn_slug=cn.slug,
                       cv_slug=cv.slug) in str(rv.data)

    def test_edit_common_name_adds_gw_common_names(self, app, db):
        """Add gw_common_names not already in common_name."""
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Butterfly Weed')
        cn3 = CommonName(name='Tomato')
        cn1.gw_common_names.append(cn2)
        idx = Index(name='Perennial Flower')
        idx.common_names = [cn1, cn2, cn3]
        db.session.add_all([cn1, cn2, cn3, idx])
        db.session.commit()
        assert cn2 in cn1.gw_common_names
        assert cn3 not in cn1.gw_common_names
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn1.id),
                         data=dict(name='Foxglove',
                                   index=idx.id,
                                   parent_cn=0,
                                   gw_common_names=[cn2.id, cn3.id]),
                         follow_redirects=True)
        assert 'added to Grows With' in str(rv.data)
        assert cn3 in cn1.gw_common_names

    def test_edit_common_name_removes_gw_common_names(self, app, db):
        """Remove gw_common_names not selected."""
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Butterfly Weed')
        cn3 = CommonName(name='Tomato')
        idx = Index(name='Perennial Flower')
        cn1.index = idx
        cn2.index = idx
        cn3.index = idx
        cn1.gw_common_names = [cn2, cn3]
        cn2.gw_common_names = [cn1, cn3]
        cn3.gw_common_names = [cn1, cn2]
        db.session.add_all([cn1, cn2, cn3, idx])
        db.session.commit()
        assert cn2 in cn1.gw_common_names
        assert cn3 in cn1.gw_common_names
        assert cn1 in cn3.gw_common_names
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn1.id),
                         data=dict(name='Foxglove',
                                   parent_cn=0,
                                   index=idx.id,
                                   gw_common_names=[cn2.id]),
                         follow_redirects=True)
        assert 'removed from Grows With' in str(rv.data)
        assert cn2 in cn1.gw_common_names
        assert cn3 not in cn1.gw_common_names
        assert cn1 not in cn3.gw_common_names

    def test_edit_common_name_adds_gw_cultivars(self, app, db):
        """Add selected gw_cultivars not already present."""
        cn = CommonName(name='Foxglove')
        cv1 = Cultivar(name='Soulmate')
        cv1.common_name = CommonName(name='Butterfly Weeed')
        cv2 = Cultivar(name='Tumbling Tom')
        cv2.common_name = CommonName(name='Tomato')
        idx = Index(name='Perennial Flower')
        cn.index = idx
        cn.gw_cultivars.append(cv1)
        db.session.add_all([cn, cv1, cv2, idx])
        db.session.commit()
        assert cv1 in cn.gw_cultivars
        assert cv2 not in cn.gw_cultivars
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Foxglove',
                                   parent_cn=0,
                                   index=idx.id,
                                   gw_cultivars=[cv1.id, cv2.id]),
                         follow_redirects=True)
        assert 'added to Grows With' in str(rv.data)
        assert cv1 in cn.gw_cultivars
        assert cv2 in cn.gw_cultivars

    def test_edit_common_name_removes_gw_cultivars(self, app, db):
        """Remove gw_cultivars not selected."""
        cn = CommonName(name='Foxglove')
        cv1 = Cultivar(name='Soulmate')
        cv1.common_name = CommonName(name='Butterfly Weed')
        cv2 = Cultivar(name='Tumbling Tom')
        cv2.common_name = CommonName(name='Tomato')
        idx = Index(name='PerennialFlower')
        cn.index = idx
        cn.gw_cultivars = [cv1, cv2]
        db.session.add_all([cn, cv1, cv2, idx])
        db.session.commit()
        assert cv1 in cn.gw_cultivars
        assert cv2 in cn.gw_cultivars
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Foxglove',
                                   parent_cn=0,
                                   index=idx.id,
                                   gw_cultivars=[cv1.id]),
                         follow_redirects=True)
        assert 'removed from Grows With' in str(rv.data)
        assert cv1 in cn.gw_cultivars
        assert cv2 not in cn.gw_cultivars

    def test_edit_common_name_successful_edit(self, app, db):
        """Change CommonName in database upon successful edit."""
        cn = CommonName()
        idx1 = Index()
        idx2 = Index()
        idx3 = Index()
        db.session.add_all([cn, idx1, idx2, idx3])
        cn.name = 'Butterfly Weed'
        cn.description = 'Butterflies _really_ like this.'
        cn.instructions = 'Put them in the ground.'
        idx1.name = 'Annual Flower'
        idx2.name = 'Vegetable'
        idx3.name = 'Herb'
        cn.index = idx1
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_common_name', cn_id=cn.id),
                         data=dict(name='Celery',
                                   description='Crunchy!',
                                   instructions='Do not eat.',
                                   parent_cn=0,
                                   index=idx2.id),
                         follow_redirects=True)
        assert cn.name == 'Celery'
        assert cn.index == idx2
        assert 'Common name \\\'Butterfly Weed\\\' changed' in str(rv.data)
        print(rv.data)
        assert 'Index for \\\'Celery\\\' and all of' in str(rv.data)
        assert 'Planting instructions for \\\'Celery\\\' changed'\
            in str(rv.data)
        assert 'Description for \\\'Celery\\\' changed' in str(rv.data)


class TestEditPacketRouteWithDB:
    """Test seeds.edit_packet."""
    def test_edit_packet_no_id(self, app, db):
        """Redirect to select_packet given no pkt_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_packet'))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.edit_packet',
                                      _external=True)

    def test_edit_packet_no_packet(self, app, db):
        """Redirect to select if no packet exists with pkt_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.edit_packet',
                                      _external=True)

    def test_edit_packet_renders_page(self, app, db):
        """Render form page with valid pkt_id and no post data."""
        cultivar = Cultivar()
        packet = Packet()
        db.session.add_all([packet, cultivar])
        packet.price = Decimal('2.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_packet', pkt_id=packet.id))
        assert 'Edit Packet' in str(rv.data)

    def test_edit_packet_submission_change_inputs(self, app, db):
        """Change packet and flash message if new values present in inputs."""
        packet = Packet()
        db.session.add(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
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
        cultivar = Cultivar()
        packet = Packet()
        db.session.add(packet, cultivar)
        packet.price = Decimal('2.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                         data=dict(price=packet.price,
                                   quantity=str(packet.quantity.value),
                                   units=packet.quantity.units,
                                   sku=packet.sku),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_edit_packet_uses_existing_quantity(self, app, db):
        """Use existing quantity if it has same values as form fields."""
        cv = foxy_cultivar()
        qty = Quantity(value=100, units='seeds')
        pkt = Packet(sku='8675309', price='3.50')
        pkt.cultivar = cv
        pkt.quantity = Quantity(value='1/2', units='grams')
        db.session.add_all([cv, qty, pkt])
        db.session.commit()
        assert pkt.quantity is not qty
        with app.test_client() as tc:
            tc.post(url_for('seeds.edit_packet', pkt_id=pkt.id),
                    data=dict(price='3.50',
                              sku='8675309',
                              quantity='100',
                              units='seeds'))
        assert pkt.quantity is qty


class TestEditCultivarRouteWithDB:
    """Test seeds.edit_cultivar."""
    def test_edit_cultivar_change_botanical_name(self, app, db):
        """Flash messages if botanical name is changed."""
        cultivar = Cultivar()
        bn = BotanicalName()
        bn2 = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, bn2, idx, cn])
        bn.name = 'Digitalis purpurea'
        bn2.name = 'Innagada davida'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names = [bn, bn2]
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn2.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed botanical name' in str(rv.data)
        assert bn2 is cultivar.botanical_name

    def test_edit_cultivar_change_common_name(self, app, db):
        """Flash message if common name changed."""
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        cn2 = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn, cn2])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        cn2.name = 'Vulpinemitten'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cn2.index = idx
        cn2.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
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
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description='Like a lady.',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert 'Changed description' in str(rv.data)
        assert cultivar.description == 'Like a lady.'

    def test_edit_cultivar_change_active(self, app, db):
        """Flash message if active status changed."""
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.in_stock = True
        cultivar.active = True
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   active='',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is no longer active.' in str(rv.data)
        assert not cultivar.active
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   active='y',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is now active' in str(rv.data)
        assert cultivar.active

    def test_edit_cultivar_change_in_stock(self, app, db):
        """Flash message if in_stock status changed."""
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.in_stock = False
        cultivar.active = True
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   active='y',
                                   in_stock='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is now in stock' in str(rv.data)
        assert cultivar.in_stock
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description='Like that Hendrix song.',
                                   Active='y',
                                   in_stock='',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is now out of stock' in str(rv.data)
        assert not cultivar.in_stock

    def test_edit_cultivar_change_name(self, app, db):
        """Flash message if name changed."""
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name='Fawksy',
                                   series='0'),
                         follow_redirects=True)
        print(rv.data)
        assert 'Changed cultivar name' in str(rv.data)
        assert cultivar.name == 'Fawksy'

    @mock.patch('werkzeug.FileStorage.save')
    def test_edit_cultivar_change_thumbnail(self,
                                            mock_save,
                                            app,
                                            db):
        """Flash message if thumbnail changed, and move old one to .images."""
        cultivar = Cultivar()
        bn = BotanicalName()
        idx = Index()
        cn = CommonName()
        thumb = Image()
        db.session.add_all([bn, idx, cn])
        bn.name = 'Digitalis purpurea'
        cn.name = 'Foxglove'
        idx.name = 'Perennial Flower'
        thumb.filename = 'foxy.jpg'
        cultivar.botanical_name = bn
        cn.index = idx
        cn.botanical_names.append(bn)
        cultivar.common_name = cn
        cultivar.name = 'Foxy'
        cultivar.description = 'Like that Hendrix song.'
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   index=str(idx.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   name=cultivar.name,
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'fawksy.jpg')),
                         follow_redirects=True)
        print(rv.data)
        assert 'New thumbnail' in str(rv.data)
        assert cultivar.thumbnail.filename == 'fawksy.jpg'
        assert thumb in cultivar.images
        mock_save.assert_called_with(os.path.join(current_app.config.
                                                  get('IMAGES_FOLDER'),
                                                  'fawksy.jpg'))

# TODO: Replace this with a form validator.
#    @mock.patch('werkzeug.FileStorage.save')
#    def test_edit_cultivar_existing_thumbnail(self, mock_save, app, db):
#        """Flash an error message if filename is used by other cult.."""
#        cv = Cultivar(name='Foxy')
#        cv2 = Cultivar(name='Fauxy')
#        idx = Index(name='Perennial')
#        cn = CommonName(name='Foxglove')
#        cn.index = idx
#        cv.common_name = cn
#        cv2.common_name = cn
#        thumb = Image()
#        thumb.filename = 'foxy.jpg'
#        cv2.thumbnail = thumb
#        db.session.add_all([cv, cv2, cn, idx, thumb])
#        db.session.commit()
#        with app.test_client() as tc:
#            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
#                         data=dict(name='Foxy',
#                                   botanical_name='0',
#                                   common_name=str(cn.id),
#                                   index=str(idx.id),
#                                   series='0',
#                                   thumbnail=(io.BytesIO(b'fawks'),
#                                              'foxy.jpg')),
#                         follow_redirects=True)
#        assert 'The filename \\\'foxy.jpg\\\' is already in use'\
#            in str(rv.data)
#        assert not mock_save.called

    @mock.patch('werkzeug.FileStorage.save')
    def test_edit_cultivar_reupload(self, mock_save, app, db):
        """Allow uploading thumbnail with same name as existing."""
        cv = Cultivar(name='Foxy')
        idx = Index(name='Perennial')
        cn = CommonName(name='Foxglove')
        cn.index = idx
        cv.common_name = cn
        thumb = Image()
        thumb.filename = 'foxy.jpg'
        cv.thumbnail = thumb
        db.session.add_all([cv, idx, cn, thumb])
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name='0',
                                   common_name=str(cn.id),
                                   index=str(idx.id),
                                   series='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert 'New thumbnail for' in str(rv.data)
        assert mock_save.called

    def test_edit_cultivar_change_gw_common_names(self, app, db):
        """Change grows with common names according to form data."""
        cv = Cultivar(name='Foxy')
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Plant')
        cn3 = CommonName(name='Butterfly Weed')
        idx = Index(name='Perennial')
        cn1.index = idx
        cn2.index = idx
        cn3.index = idx
        cv.common_name = cn1
        cv.gw_common_names.append(cn2)
        db.session.add_all([cv, cn2, cn3, idx])
        db.session.commit()
        assert cn2 in cv.gw_common_names
        assert cn3 not in cv.gw_common_names
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   common_name=cn1.id,
                                   index=idx.id,
                                   series='0',
                                   gw_common_names=[cn3.id]),
                         follow_redirects=True)
        assert 'added to Grows With for' in str(rv.data)
        assert 'removed from Grows With for' in str(rv.data)
        assert cn2 not in cv.gw_common_names
        assert cn3 in cv.gw_common_names

    def test_edit_cultivar_change_gw_cultivars(self, app, db):
        """Set gw_cultivars to ones in form select.

        This should also set the gw_cultivars for any cultivars added to or
        removed from cultivar.gw_cultivars.
        """
        cv1 = Cultivar(name='Foxy')
        cv2 = Cultivar(name='Soulmate')
        cv3 = Cultivar(name='Milkmaid')
        cn1 = CommonName(name='Foxglove')
        cn2 = CommonName(name='Butterfly Weed')
        cv1.common_name = cn1
        cv2.common_name = cn2
        cv3.common_name = cn2
        idx = Index(name='Perennial')
        cn1.index = idx
        cn2.index = idx
        cv2.gw_cultivars.append(cv1)
        cv1.gw_cultivars.append(cv2)
        db.session.add_all([cv1, cv2, cv3, cn1, cn2, idx])
        db.session.commit()
        assert cv2 in cv1.gw_cultivars
        assert cv1 in cv2.gw_cultivars
        assert cv3 not in cv1.gw_cultivars
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv1.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   common_name=cn1.id,
                                   index=idx.id,
                                   series=0,
                                   gw_cultivars=[cv3.id]),
                         follow_redirects=True)
        assert 'removed from Grows With for' in str(rv.data)
        assert 'added to Grows With for' in str(rv.data)
        assert cv2 not in cv1.gw_cultivars
        assert cv1 not in cv2.gw_cultivars
        assert cv3 in cv1.gw_cultivars
        assert cv1 in cv3.gw_cultivars

    def test_edit_cultivar_change_series(self, app, db):
        """Clear series if 0 selected, otherwise change series."""
        cv = Cultivar(name='Foxy')
        cn = CommonName(name='Foxglove')
        idx = Index(name='Perennial')
        sr1 = Series(name='Polkadot')
        sr2 = Series(name='Spotty')
        sr1.common_name = cn
        sr2.common_name = cn
        cn.index = idx
        cv.common_name = cn
        db.session.add_all([cv, cn, idx, sr1, sr2])
        db.session.commit()
        assert cv.series is None
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   index=idx.id,
                                   common_name=cn.id,
                                   series=sr1.id),
                         follow_redirects=True)
        assert 'Series for \\\'Polkadot Foxy Foxglove\\\' has been set to'\
            in str(rv.data)
        assert cv.series is sr1
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   index=idx.id,
                                   common_name=cn.id,
                                   series=sr2.id),
                         follow_redirects=True)
        print(rv.data)
        assert cv.series is sr2
        assert 'Series for \\\'Spotty Foxy Foxglove\\\' has been set to'\
            in str(rv.data)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   index=idx.id,
                                   common_name=cn.id,
                                   series=0),
                         follow_redirects=True)
        assert 'Series for \\\'Spotty Foxy Foxglove\\\' has been unset'\
            in str(rv.data)
        assert cv.series is None

    def test_edit_cultivar_changes_synonyms(self, app, db):
        """If synonyms in form are different, change them."""
        cv = Cultivar(name='Foxy')
        syn = Synonym(name='Fauxy')
        cv.synonyms.append(syn)
        cn = CommonName(name='Foxglove')
        idx = Index(name='Perennial')
        cn.index = idx
        cv.common_name = cn
        db.session.add_all([cv, syn, cn, idx])
        db.session.commit()
        assert syn in cv.synonyms
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   index=idx.id,
                                   common_name=cn.id,
                                   synonyms='Fawksy',
                                   series=0),
                         follow_redirects=True)
        assert 'Synonyms for \\\'Foxy Foxglove\\\' set to' in str(rv.data)
        assert syn not in cv.synonyms
        assert cv.synonyms_string == 'Fawksy'

    def test_edit_cultivar_clears_description(self, app, db):
        """Set description to none if form fields empty."""
        cv = Cultivar(name='Foxy')
        cv.description = 'Like Hendrix!'
        cn = CommonName(name='Foxglove')
        idx = Index(name='Perennial')
        cn.index = idx
        cv.common_name = cn
        db.session.add_all([cv, cn, idx])
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   common_name=cn.id,
                                   description='',
                                   series=0),
                         follow_redirects=True)
        assert 'Description for \\\'Foxy Foxglove\\\' has been cleared.'\
            in str(rv.data)
        assert cv.description is None

    def test_edit_cultivar_no_changes(self, app, db):
        """Submission with no changes flashes relevant message."""
        cultivar = Cultivar(name='Foxy')
        bn = BotanicalName(name='Digitalis purpurea')
        idx = Index(name='Perennial Flower')
        cn = CommonName(name='Foxglove')
        thumb = Image(filename='foxy.jpg')
        db.session.add_all([cultivar, bn, idx, cn, thumb])
        cn.botanical_names.append(bn)
        cultivar.botanical_name = bn
        cultivar.common_name = cn
        cn.index = idx
        cultivar.description = 'Like that Hendrix song.'
        cultivar.in_stock = True
        cultivar.active = True
        cultivar.invisible = False
        cultivar.thumbnail = thumb
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cultivar.id),
                         data=dict(botanical_name=str(bn.id),
                                   common_name=str(cn.id),
                                   description=cultivar.description,
                                   active='y',
                                   in_stock='y',
                                   visible='y',
                                   name=cultivar.name,
                                   series='0'),
                         follow_redirects=True)
        print(rv.data)
        assert 'No changes made' in str(rv.data)

    def test_edit_cultivar_no_cultivar(self, app, db):
        """Redirect to seeds.select_cultivar if no cultivar w/ given id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_cultivar', cv_id=42))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.edit_cultivar',
                                      _external=True)

    def test_edit_cultivar_no_cv_id(self, app, db):
        """Redirect to seeds.select_cultivar if no id given."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.edit_cultivar'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.edit_cultivar',
                                      _external=True)

    def test_edit_cultivar_removes_botanical_name(self, app, db):
        """Remove botanical name if form set to 0."""
        cv = Cultivar(name='Foxy')
        bn = BotanicalName(name='Digitalis purpurea')
        cn = CommonName(name='Foxglove')
        idx = Index(name='Perennial')
        cv.botanical_name = bn
        cv.common_name = cn
        cn.index = idx
        db.session.add_all([cv, bn, cn, idx])
        db.session.commit()
        assert cv.botanical_name == bn
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.edit_cultivar', cv_id=cv.id),
                         data=dict(name='Foxy',
                                   botanical_name=0,
                                   common_name=cn.id,
                                   series=0),
                         follow_redirects=True)
        assert cv.botanical_name is None
        assert 'Botanical name for \\\'Foxy Foxglove\\\' has been removed'\
            in str(rv.data)


class TestFlipDroppedRouteWithDB:
    """Test seeds.flip_dropped."""
    def test_flip_dropped_no_cultivar(self, app, db):
        """Return 404 if no cultivar exists with given id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=42))
        assert rv.status_code == 404

    def test_flip_dropped_no_cv_id(self, app, db):
        """Return 404 if no cv_id given."""
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped'))
        assert rv.status_code == 404

    def test_flip_dropped_success(self, app, db):
        """Set dropped to the opposite of its current value and redirect."""
        cultivar = foxy_cultivar()
        cultivar.dropped = False
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert cultivar.dropped
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped',
                                cv_id=cultivar.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not cultivar.dropped
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' has been dropped.' in str(rv.data)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_dropped', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' has been returned to active' in\
            str(rv.data)


class TestFlipInStockRouteWithDB:
    """Test seeds.flip_in_stock."""
    def test_flip_in_stock_no_cultivar(self, app, db):
        """Return 404 if no cultivar exists with given id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=42))
        assert rv.status_code == 404

    def test_flip_in_stock_no_cv_id(self, app, db):
        """Return 404 if no cv_id given."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock'))
        assert rv.status_code == 404

    def test_flip_in_stock_success(self, app, db):
        """Reverse value of in_stock and redirect on successful submit."""
        cultivar = foxy_cultivar()
        cultivar.in_stock = False
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id))
        assert rv.location == url_for('seeds.manage', _external=True)
        assert cultivar.in_stock
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock',
                                cv_id=cultivar.id,
                                next=url_for('seeds.index')))
        assert rv.location == url_for('seeds.index', _external=True)
        assert not cultivar.in_stock
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is now in stock' in str(rv.data)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.flip_in_stock', cv_id=cultivar.id),
                        follow_redirects=True)
        assert '\\\'Foxy Foxglove\\\' is now out of stock.' in str(rv.data)


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
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.manage'))
        assert rv.status_code == 200
        assert rv.location is None
        assert 'Manage Seeds' in str(rv.data)


class TestRemoveBotanicalNameRouteWithDB:
    """Test seeds.manage."""
    def test_remove_botanical_name_bad_id(self, app, db):
        """Redirect given a non-integer bn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id='frogs'))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

    def test_remove_botanical_name_does_not_exist(self, app, db):
        """Redirect if no BotanicalName corresponds to bn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=42))
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

    def test_remove_botanical_name_no_id(self, app, db):
        """Redirect to seeds.select_botanical_name given no bn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.select_botanical_name',
                                      dest='seeds.remove_botanical_name',
                                      _external=True)

    def test_remove_botanical_name_not_verified(self, app, db):
        """Redirect to self and flash message if verify_removal unchecked."""
        bn = BotanicalName()
        bn.name = 'Asclepias incarnata'
        db.session.add(bn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.remove_botanical_name',
                                      bn_id=bn.id,
                                      _external=True)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=''),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_botanical_name_renders_page(self, app, db):
        """Render seeds/remove_botanical_name.html with valid bn_id."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_botanical_name', bn_id=bn.id))
        assert 'Remove Botanical Name' in str(rv.data)

    def test_remove_botanical_name_verified(self, app, db):
        """Delete BotanicalName from db if verify_removal checked."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        assert BotanicalName.query.count() == 1
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert BotanicalName.query.count() == 0
        assert 'has been removed from the database' in str(rv.data)


class TestRemoveIndexRouteWithDB:
    """Test seeds.remove_index."""
    def test_remove_index_bad_id(self, app, db):
        """Redirect given a non-integer idx_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_index', idx_id='frogs'))
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.remove_index',
                                      _external=True)

    def test_remove_index_does_not_exist(self, app, db):
        """Redirect if no Index corresponds to idx_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_index', idx_id=42))
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.remove_index',
                                      _external=True)

    def test_remove_index_no_id(self, app, db):
        """Redirect to seeds.select_index if no idx_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_index'))
        assert rv.location == url_for('seeds.select_index',
                                      dest='seeds.remove_index',
                                      _external=True)

    def test_remove_index_not_verified(self, app, db):
        """Redirect to self if verify_removal not checked."""
        idx = Index()
        idx2 = Index()
        db.session.add_all([idx, idx2])
        idx.name = 'Annual Flower'
        idx2.name = 'Herb'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_index', idx_id=idx.id),
                         data=dict(verify_removal='', move_to=idx2.id))
        assert rv.location == url_for('seeds.remove_index',
                                      idx_id=idx.id,
                                      _external=True)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_index', idx_id=idx.id),
                         data=dict(verify_removal='', move_to=idx2.id),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_index_renders_page(self, app, db):
        """Render seeds/remove_index.html with valid idx_id."""
        idx1 = Index(name='Annual')
        idx2 = Index(name='Perennial')
        db.session.add_all([idx1, idx2])
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_index', idx_id=idx1.id))
        assert rv.status_code == 200
        assert 'Remove Index' in str(rv.data)

    def test_remove_index_verified(self, app, db):
        """Remove Index from db if verify_removal is checked."""
        idx = Index()
        idx2 = Index()
        db.session.add_all([idx, idx2])
        idx.name = 'Annual Flower'
        idx2.name = 'Herb'
        db.session.commit()
        assert idx in Index.query.all()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_index', idx_id=idx.id),
                         data=dict(verify_removal=True, move_to=idx2.id),
                         follow_redirects=True)
        assert idx not in Index.query.all()
        assert 'has been removed from the database' in str(rv.data)


class TestRemoveCommonNameRouteWithDB:
    """Test seeds.remove_common_name."""
    def test_remove_common_name_bad_id(self, app, db):
        """Redirect to select given a non-integer cn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_common_name', cn_id='frogs'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_does_not_exist(self, app, db):
        """Redirect to select if no CommonName corresponds to cn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_no_id(self, app, db):
        """Redirect to seeds.select_common_name with no cn_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_common_name'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.remove_common_name',
                                      _external=True)

    def test_remove_common_name_not_verified(self, app, db):
        """Redirect to self with flash if verify_removal not checked."""
        cn = CommonName()
        cn2 = CommonName()
        db.session.add_all([cn, cn2])
        cn.name = 'Coleus'
        cn2.name = 'Kingus'
        db.session.commit()
        assert cn in CommonName.query.all()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal='', move_to=cn2.id))
        assert rv.location == url_for('seeds.remove_common_name',
                                      cn_id=cn.id,
                                      _external=True)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal='', move_to=cn2.id),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)
        assert cn in CommonName.query.all()

    def test_remove_common_name_renders_page(self, app, db):
        """Render seeds/remove_common_name.html given valid cn_id."""
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Coleus'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_common_name', cn_id=cn.id))
        assert rv.status_code == 200
        assert 'Remove Common Name' in str(rv.data)

    def test_remove_common_name_verified(self, app, db):
        """Delete CommonName from db on successful submit."""
        cn = CommonName()
        cn2 = CommonName()
        idx = Index(name='Perennial')
        db.session.add_all([idx, cn, cn2])
        cn.name = 'Coleus'
        cn.index = idx
        cn2.name = 'Kingus'
        cn2.index = idx
        db.session.commit()
        assert cn in CommonName.query.all()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                         data=dict(verify_removal=True, move_to=cn2.id),
                         follow_redirects=True)
        assert 'has been removed from the database' in str(rv.data)
        assert cn not in CommonName.query.all()


class TestRemovePacketRouteWithDB:
    """Test seeds.remove_packet."""
    def test_remove_packet_no_id(self, app, db):
        """Redirect to select_packet given no pkt_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_packet',
                                dest='seeds.remove_packet'))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.remove_packet',
                                      _external=True)

    def test_remove_packet_no_packet(self, app, db):
        """Redirect back to select if no packet corresponds to pkt_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=42))
        assert rv.location == url_for('seeds.select_packet',
                                      dest='seeds.remove_packet',
                                      _external=True)

    def test_remove_packet_renders_page(self, app, db):
        """Render form page given a valid packet id."""
        packet = Packet()
        db.session.add(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_packet', pkt_id=packet.id))
        assert 'Remove Packet' in str(rv.data)

    def test_remove_packet_submission_no_changes(self, app, db):
        """Redirect and flash a message if verify_removal unchecked."""
        packet = Packet()
        db.session.add(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=None))
        assert rv.location in url_for('seeds.remove_packet',
                                      pkt_id=packet.id,
                                      _external=True)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                         data=dict(verify_removal=None),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_packet_submission_verified(self, app, db):
        """Delete packet and flash a message if verify_removal is checked."""
        packet = Packet()
        db.session.add(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
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
        cultivar = foxy_cultivar()
        img = Image()
        img.filename = 'foxee.jpg'
        thumb = Image()
        thumb.filename = 'foxy.jpg'
        cultivar.images.append(img)
        cultivar.thumbnail = thumb
        db.session.add_all([cultivar, img, thumb])
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=True, delete_images=True),
                         follow_redirects=True)
        assert 'Image file \\\'foxee.jpg\\\' deleted' in str(rv.data)
        assert 'Thumbnail image \\\'foxy.jpg\\\' has' in str(rv.data)
        assert Image.query.count() == 0
        assert mock_delete.called

    def test_remove_cultivar_deletes_cultivar(self, app, db):
        """Delete cultivar from the database on successful submission."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=True),
                         follow_redirects=True)
        assert 'The cultivar \\\'Foxy Foxglove\\\' has been deleted' in\
            str(rv.data)
        assert Cultivar.query.count() == 0

    def test_remove_cultivar_no_id(self, app, db):
        """Redirect to seeds.select_cultivar given no cv_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_cultivar'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.remove_cultivar',
                                      _external=True)

    def test_remove_cultivar_no_cultivar(self, app, db):
        """Redirect to seeds.select_cultivar if no cultivar w/ given id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_cultivar', cv_id=42))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.remove_cultivar',
                                      _external=True)

    def test_remove_cultivar_not_verified(self, app, db):
        """Redirect and flash message if verify_removal not checked."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=None))
        assert rv.location == url_for('seeds.remove_cultivar',
                                      cv_id=cultivar.id,
                                      _external=True)
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                         data=dict(verify_removal=None),
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_remove_cultivar_renders_page(self, app, db):
        """Render remove cultivar form page given valid cultivar id."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.remove_cultivar', cv_id=cultivar.id))
        assert 'Remove Cultivar' in str(rv.data)


class TestSelectBotanicalNameRouteWithDB:
    """Test seeds.select_botanical_name."""
    def test_select_botanical_name_no_dest(self, app, db):
        """Redirect to seeds.manage if no dest given."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_botanical_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_botanical_name'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_botanical_name_renders_page(self, app, db):
        """Render seeds/select_botanical_name.html given no form data."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
        assert rv.status_code == 200
        assert 'Select Botanical Name' in str(rv.data)

    def test_select_botanical_name_selected(self, app, db):
        """Redirect to dest if a botanical name is selected."""
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = 'Asclepias incarnata'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.select_botanical_name',
                                 dest='seeds.edit_botanical_name'),
                         data=dict(botanical_name=bn.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_botanical_name',
                                      bn_id=bn.id,
                                      _external=True)


class TestSelectIndexRouteWithDB:
    """Test seeds.select_index."""
    def test_select_index_no_dest(self, app, db):
        """Redirect to seeds.manage given no dest."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_index'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_index'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_index_renders_page(self, app, db):
        """Render seeds/select_index.html given no form data."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_index',
                                dest='seeds.edit_index'))
        assert rv.status_code == 200
        assert 'Select Index' in str(rv.data)

    def test_select_index_success(self, app, db):
        """Redirect to dest with idx_id selected by form."""
        idx = Index()
        db.session.add(idx)
        idx.name = 'Annual Flower'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.select_index',
                                 dest='seeds.edit_index'),
                         data=dict(index=idx.id))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.edit_index',
                                      idx_id=idx.id,
                                      _external=True)


class TestSelectCommonNameRouteWithDB:
    """Test seeds.select_common_name."""
    def test_select_common_name_no_dest(self, app, db):
        """Redirect to seeds.manage with an error if no dest given."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_common_name'))
        assert rv.status_code == 302
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_common_name'),
                        follow_redirects=True)
        assert 'Error: No destination' in str(rv.data)

    def test_select_common_name_renders_page(self, app, db):
        """Render seeds/select_common_name.html given a dest."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
        assert rv.status_code == 200
        assert 'Select Common Name' in str(rv.data)

    def test_select_common_name_success(self, app, db):
        """Redirect to dest with cn_id selected by form."""
        cn = CommonName()
        db.session.add(cn)
        cn.name = 'Coleus'
        db.session.commit()
        with app.test_client() as tc:
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
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_cultivar'))
        assert rv.location == url_for('seeds.manage', _external=True)

    def test_select_cultivar_renders_page(self, app, db):
        """Render form page given a dest."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_cultivar',
                                dest='seeds.add_packet'))
        assert 'Select Cultivar' in str(rv.data)

    def test_select_cultivar_successful_submission(self, app, db):
        """Redirect to dest on valid form submission."""
        cultivar = Cultivar(name='Foxy')
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.common_name.index = Index(name='Perennial')
        db.session.add(cultivar)
        db.session.commit()
        dest = 'seeds.add_packet'
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.select_cultivar', dest=dest),
                         data=dict(cultivar=cultivar.id))
        print(rv.data)
        assert rv.location == url_for(dest, cv_id=str(cultivar.id),
                                      _external=True)


class TestSelectPacketRouteWithDB:
    """Test seeds.select_packet."""
    def test_select_packet_no_dest(self, app, db):
        """Flash an error and redirect if no dest specified."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_packet'))
        assert rv.location == url_for('seeds.manage', _external=True)
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_packet'),
                        follow_redirects=True)
        assert 'No destination' in str(rv.data)

    def test_select_packet_renders_page(self, app, db):
        """Render form page if given a dest."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
        assert 'Select Packet' in str(rv.data)

    def test_select_packet_valid_submission(self, app, db):
        """Redirect to dest given valid selection."""
        cultivar = Cultivar()
        packet = Packet()
        db.session.add_all([cultivar, packet])
        cultivar.name = 'Foxy'
        cultivar.common_name = CommonName(name='Foxglove')
        cultivar.packets.append(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.select_packet',
                                 dest='seeds.edit_packet'),
                         data=dict(packet=packet.id))
        assert rv.location == url_for('seeds.edit_packet',
                                      pkt_id=packet.id,
                                      _external=True)

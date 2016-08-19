import io
from decimal import Decimal
from flask import url_for
from unittest import mock
from app.seeds.models import (
    BotanicalName,
    Index,
    CommonName,
    Cultivar,
    Image,
    Packet,
    Quantity
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


class TestAddSectionRouteWithDB:
    """Test add_section route."""
    def test_add_section_renders_page(self, app, db):
        """Load form page given a valid cn_id."""
        cn = CommonName(name='Foxglove')
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_section', cn_id=cn.id))
            assert 'Add Section' in str(rv.data)

    def test_add_section_bad_cn_id(self, app, db):
        """Redirect to select_common_name if cn_id is invalid."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_section'))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_section',
                                      _external=True)
        cn = CommonName(name='Foxglove')
        cn.id = 1
        db.session.add(cn)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_section', cn_id=42))
        assert rv.location == url_for('seeds.select_common_name',
                                      dest='seeds.add_section',
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
                                   section='0',
                                   thumbnail=(io.BytesIO(b'fawks'),
                                              'foxy.jpg')),
                         follow_redirects=True)
        assert '"Foxy Foxglove" is not in stock' in str(rv.data)
        assert '"Foxy Foxglove" is currently inactive' in\
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


class TestEditIndexRouteWithDB:
    """Test seeds.edit_index."""
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
        assert 'No changes to "Annual Flower" were made' in str(rv.data)

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
        packet.cultivar = Cultivar(name='Foxy')
        db.session.commit()
        with app.test_client() as tc:
            tc.post(url_for('seeds.edit_packet', pkt_id=packet.id),
                    data=dict(id=packet.id,
                              cultivar_id=packet.cultivar.id,
                              price='2.99',
                              qty_val='2.5',
                              units='grams',
                              sku='BOUT350'),
                    follow_redirects=True)
        assert packet.price == Decimal('2.99')
        assert packet.quantity.value == Decimal('2.5')
        assert packet.quantity.units == 'grams'
        assert packet.sku == 'BOUT350'

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
                         data=dict(id=packet.id,
                                   price=packet.price,
                                   qty_val=str(packet.quantity.value),
                                   units=packet.quantity.units,
                                   sku=packet.sku),
                         follow_redirects=True)
        assert 'No changes to' in str(rv.data)

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
                    data=dict(id=pkt.id,
                              price='3.50',
                              sku='8675309',
                              qty_val='100',
                              units='seeds'))
        assert pkt.quantity is qty


class TestFlipCultivarBoolWithDB:
    """Test seeds.flip_cultivar_bool."""
    def test_flip_cultivar_bool(self, app, db):
        """Return 404 if no cultivar exists with given id."""
        with app.test_client() as tc:
            rv = tc.get(
                url_for('seeds.flip_cultivar_bool', cv_id=42, attr='active')
            )
        assert rv.status_code == 404

    def test_flip_cultivar_bool_success(self, app, db):
        """Flip status of attr."""
        cv = foxy_cultivar()
        cv.active = False
        db.session.add(cv)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.get(
                url_for('seeds.flip_cultivar_bool', cv_id=cv.id, attr='active')
            )
        assert cv.active
        with app.test_client() as tc:
            rv = tc.get(
                url_for('seeds.flip_cultivar_bool', cv_id=cv.id, attr='active')
            )
        assert not cv.active


class TestHomeRouteWithDB:
    """Test seeds.home."""
    def test_home_renders_page(self, app, db):
        """seeds.index should render a page with no redirects."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.home'))
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
        assert 'Botanical name was not removed' in str(rv.data)

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
            tc.post(url_for('seeds.remove_botanical_name', bn_id=bn.id),
                    data=dict(verify_removal=True),
                    follow_redirects=True)
        assert BotanicalName.query.count() == 0


class TestRemoveIndexRouteWithDB:
    """Test seeds.remove_index."""
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
        assert 'Index was not removed' in str(rv.data)

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
            tc.post(url_for('seeds.remove_index', idx_id=idx.id),
                    data=dict(verify_removal=True, move_to=idx2.id),
                    follow_redirects=True)
        assert idx not in Index.query.all()


class TestRemoveCommonNameRouteWithDB:
    """Test seeds.remove_common_name."""
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
        assert 'Common name was not removed' in str(rv.data)
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
            tc.post(url_for('seeds.remove_common_name', cn_id=cn.id),
                    data=dict(verify_removal=True, move_to=cn2.id),
                    follow_redirects=True)
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
        assert 'Packet was not removed' in str(rv.data)

    def test_remove_packet_submission_verified(self, app, db):
        """Delete packet and flash a message if verify_removal is checked."""
        packet = Packet()
        db.session.add(packet)
        packet.price = Decimal('1.99')
        packet.quantity = Quantity(value=100, units='seeds')
        packet.sku = '8675309'
        db.session.commit()
        with app.test_client() as tc:
            tc.post(url_for('seeds.remove_packet', pkt_id=packet.id),
                    data=dict(verify_removal=True),
                    follow_redirects=True)
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
            tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                    data=dict(verify_removal=True, delete_images=True),
                    follow_redirects=True)
        assert Image.query.count() == 0
        assert mock_delete.called

    def test_remove_cultivar_deletes_cultivar(self, app, db):
        """Delete cultivar from the database on successful submission."""
        cultivar = foxy_cultivar()
        db.session.add(cultivar)
        db.session.commit()
        with app.test_client() as tc:
            tc.post(url_for('seeds.remove_cultivar', cv_id=cultivar.id),
                    data=dict(verify_removal=True),
                    follow_redirects=True)
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
        assert 'Cultivar was not removed' in str(rv.data)

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

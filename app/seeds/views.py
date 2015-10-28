# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


import os
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for
)
from werkzeug import secure_filename
from flask.ext.login import login_required
from app import db, make_breadcrumbs
from app.decorators import permission_required
from app.auth.models import Permission
from . import seeds
from .models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Price,
    Packet,
    Seed,
    Unit
)
from .forms import (
    AddBotanicalNameForm,
    AddCategoryForm,
    AddCommonNameForm,
    AddPacketForm,
    AddSeedForm,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    EditPacketForm,
    EditSeedForm,
    RemoveBotanicalNameForm,
    RemoveCategoryForm,
    RemoveCommonNameForm,
    RemovePacketForm,
    RemoveSeedForm,
    SelectBotanicalNameForm,
    SelectCategoryForm,
    SelectCommonNameForm,
    SelectPacketForm,
    SelectSeedForm
)


@seeds.context_processor
def make_permissions_available():  # pragma: no cover
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@seeds.context_processor
def make_categories_available():  # pragma: no cover
    """Make categories available to Jinja templates.

    Returns:
        dict: A list of all Category objects loaded from the database.
    """
    if not current_app.config.get('TESTING'):
        categories = Category.query.all()
    else:
        categories = None
    return dict(categories=categories)


@seeds.route('/add_botanical_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_botanical_name():
    """Add a botanical name to the database."""
    form = AddBotanicalNameForm()
    form.set_common_names()
    if form.validate_on_submit():
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = form.name.data
        if len(form.common_names.data) > 0:
            for cn_id in form.common_names.data:
                cn = CommonName.query.get(cn_id)
                flash('\'{0}\' added to common names associated with \'{1}\'.'.
                      format(cn.name, bn.name))
                bn.common_names.append(cn)
        db.session.commit()
        flash('Botanical name \'{0}\' has been added to the database.'.
              format(bn.name))
        return redirect(url_for('seeds.manage'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_botanical_name'), 'Add Botanical Name')
    )
    return render_template('seeds/add_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_category', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_category():
    """Add a category to the database."""
    form = AddCategoryForm()
    if form.validate_on_submit():
        category = Category()
        db.session.add(category)
        category.category = form.category.data.title()
        if len(form.description.data) > 0:
            category.description = form.description.data
        db.session.commit()
        flash('New category \'{0}\' has been added to the database.'.
              format(category.category))
        return redirect(url_for('seeds.manage'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category')
    )
    return render_template('seeds/add_category.html', crumbs=crumbs, form=form)


@seeds.route('/add_common_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_common_name():
    """Add a common name to the database."""
    form = AddCommonNameForm()
    form.set_categories()
    if form.validate_on_submit():
        cn = CommonName()
        db.session.add(cn)
        cn.name = form.name.data.title()
        if len(form.categories.data) > 0:
            for cat_id in form.categories.data:
                category = Category.query.get(cat_id)
                flash('{0} added to categories associated with {1}.'.
                      format(category.category, cn.name))
                cn.categories.append(category)
        if len(form.description.data) > 0:
            cn.description = form.description.data
        db.session.commit()
        flash('The common name \'{0}\' has been added to the database.'.
              format(cn.name))
        return redirect(url_for('seeds.manage'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_common_name'), 'Add Common Name')
    )
    return render_template('seeds/add_common_name.html', crumbs=crumbs,
                           form=form)


@seeds.route('/add_packet', methods=['GET', 'POST'])
@seeds.route('/add_packet/<seed_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_packet(seed_id=None):
    """Add a packet to the database."""
    if seed_id is None:
        return redirect(url_for('seeds.select_seed', dest='seeds.add_packet'))
    form = AddPacketForm()
    form.set_selects()
    seed = Seed.query.get(seed_id)
    if form.validate_on_submit():
        packet = Packet()
        db.session.add(packet)
        packet.seed = seed
        if form.price.data:
            packet.price = form.price.data
        else:
            packet._price = Price.query.get(form.prices.data)
        if form.quantity.data:
            packet.quantity = form.quantity.data
        else:
            packet.quantity = form.quantities.data
        if form.unit.data:
            packet.unit = form.unit.data
        else:
            packet._unit = Unit.query.get(form.units.data)
        packet.sku = form.sku.data
        flash('Packet SKU {0}: ${1} for {2} {3} added to {4} {5}.'.
              format(packet.sku,
                     packet.price,
                     packet.quantity,
                     packet.unit,
                     seed.name,
                     seed.common_name.name))
        db.session.commit()
        if form.again.data:
            return redirect(url_for('seeds.add_packet', seed_id=seed_id))
        else:
            return redirect(url_for('seeds.manage'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_packet'), 'Add Packet')
        )
    return render_template('seeds/add_packet.html',
                           crumbs=crumbs,
                           form=form,
                           seed=seed)


@seeds.route('/add_seed', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_seed():
    """Add a seed to the database."""
    form = AddSeedForm()
    form.set_selects()
    if form.validate_on_submit():
        seed = Seed()
        db.session.add(seed)
        if form.botanical_names.data:
            for bn_id in form.botanical_names.data:
                bn = BotanicalName.query.get(bn_id)
                flash('\'{0}\' added to botanical names for {1}.'.
                      format(bn.name, form.name.data))
                seed.botanical_names.append(bn)
        for cat_id in form.categories.data:
            cat = Category.query.get(cat_id)
            flash('\'{0}\' added to categories for {1}.'.
                  format(cat.category, form.name.data))
            seed.categories.append(cat)
        cn = CommonName.query.get(form.common_names.data)
        seed.common_name = cn
        seed.name = form.name.data.title()
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                       thumb_name)
            seed.thumbnail = Image(filename=thumb_name)
            flash('Thumbnail uploaded as: {0}'.format(thumb_name))
            form.thumbnail.data.save(upload_path)
        seed.description = form.description.data
        if form.in_stock.data:
            seed.in_stock = True
            flash('\'{0}\' is in stock.'.format(seed.fullname))
        else:
            flash('\'{0}\' is not in stock.'.format(seed.fullname))
            seed.in_stock = False
        if form.dropped.data:
            flash('\'{0}\' is currently dropped/inactive.'.
                  format(seed.fullname))
            seed.dropped = True
        else:
            flash('\'{0}\' is currently active.'.
                  format(seed.fullname))
            seed.dropped = False
        flash('New seed \'{0}\' has been added to the database.'.
              format(seed.fullname))
        db.session.commit()
        return redirect(url_for('seeds.add_packet', seed_id=seed.id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_seed'), 'Add Seed')
    )
    return render_template('seeds/add_seed.html', crumbs=crumbs, form=form)


@seeds.route('/<cat_slug>')
def category(cat_slug=None):
    """Display a category."""
    category = Category.query.filter_by(slug=cat_slug).first()
    if category is not None:
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.category', cat_slug=category.slug),
             category.header)
        )
        return render_template('seeds/category.html',
                               crumbs=crumbs,
                               category=category)
    else:
        abort(404)


@seeds.route('/<cat_slug>/<cn_slug>')
def common_name(cat_slug=None, cn_slug=None):
    """Display page for a common name."""
    cat = Category.query.filter_by(slug=cat_slug).first()
    cn = CommonName.query.filter_by(slug=cn_slug).first()
    if cn is not None and cat is not None:
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.category', cat_slug=cat_slug), cat.header),
            (url_for('seeds.common_name', cat_slug=cat_slug, cn_slug=cn_slug),
             cn.name)
        )
        return render_template('seeds/common_name.html',
                               cat=cat,
                               cn=cn,
                               crumbs=crumbs)
    else:
        abort(404)


@seeds.route('/edit_botanical_name', methods=['GET', 'POST'])
@seeds.route('/edit_botanical_name/<bn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_botanical_name(bn_id=None):
    if bn_id is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
    if not bn_id.isdigit():
        flash('Error: Botanical name id must be an integer!'
              ' Please select a botanical name:')
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
    bn = BotanicalName.query.get(bn_id)
    if bn is None:
        flash('Error: No botanical name exists with that id!'
              ' Please select one from the list:')
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
    form = EditBotanicalNameForm()
    form.set_common_names()
    if form.validate_on_submit():
        edited = False
        if form.name.data != bn.name:
            edited = True
            flash('Botanical name \'{0}\' changed to \'{1}\'.'.
                  format(bn.name, form.name.data))
            bn.name = form.name.data
        for cn in bn.common_names:
            if cn.id not in form.common_names.data:
                edited = True
                flash('\'{0}\' removed from common names associated with '
                      '\'{1}\'.'.format(cn.name, bn.name))
                bn.common_names.remove(cn)
        cn_ids = [cn.id for cn in bn.common_names]
        for cn_id in form.common_names.data:
            if cn_id not in cn_ids:
                edited = True
                cn = CommonName.query.get(cn_id)
                flash('\'{0}\' added to common names associated with '
                      '\'{1}\'.'.format(cn.name, bn.name))
                bn.common_names.append(cn)
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to botanical name: \'{0}\'.'.
                  format(bn.name))
            return redirect(url_for('seeds.edit_botanical_name', bn_id=bn_id))
    form.populate(bn)
    current_common_names = ', '.join([cname.name for cname in bn.common_names])
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_botanical_name', bn_id=bn_id),
         'Edit Botanical Name')
    )
    return render_template('/seeds/edit_botanical_name.html',
                           crumbs=crumbs,
                           current_common_names=current_common_names,
                           form=form)


@seeds.route('/edit_category', methods=['GET', 'POST'])
@seeds.route('/edit_category/<category_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_category(category_id=None):
    if category_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
    if not category_id.isdigit():
        flash('Error: Category id must be an integer!'
              ' Please select a category:')
        return redirect(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
    category = Category.query.get(category_id)
    if category is None:
        flash('Error: No category exists with that id!'
              ' Please select one from the list:')
        return redirect(url_for('seeds.select_category',
                        dest='seeds.edit_category'))
    form = EditCategoryForm()
    if form.validate_on_submit():
        edited = False
        if form.category.data.title() != category.category:
            flash('Category changed from \'{0}\' to \'{1}\'.'
                  .format(category.category, form.category.data.title()))
            category.category = form.category.data.title()
            edited = True
        if form.description.data != category.description:
            flash('{0} description changed to \'{1}\'.'
                  .format(form.category.data.title(), form.description.data))
            category.description = form.description.data
            edited = True
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to category: {0}'.format(category.category))
            return redirect(url_for('seeds.manage'))
    form.populate(category)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category', category_id=category_id),
         'Edit Category')
    )
    return render_template('seeds/edit_category.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_common_name', methods=['GET', 'POST'])
@seeds.route('/edit_common_name/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_common_name(cn_id=None):
    """"Edit a common name stored in the database.

    Args:
        cn_id (int): The id number of the common name to edit.
    """
    if cn_id is None:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
    if not cn_id.isdigit():
        flash('Error: Common name id must be an integer! '
              'Please select a common name:')
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
    form = EditCommonNameForm()
    form.set_categories()
    cn = CommonName.query.get(cn_id)
    if form.validate_on_submit():
        edited = False
        if form.name.data.title() != cn.name:
            edited = True
            flash('Common name \'{0}\' changed to \'{1}\'.'.
                  format(cn.name, form.name.data.title()))
            cn.name = form.name.data.title()
        for cat in cn.categories:
            if cat.id not in form.categories.data:
                edited = True
                flash('{0} removed from categories associated with {1}.'.
                      format(cat.category, cn.name))
                cn.categories.remove(cat)
        cat_ids = [cat.id for cat in cn.categories]
        for cat_id in form.categories.data:
            if cat_id not in cat_ids:
                edited = True
                cat = Category.query.get(cat_id)
                flash('{0} added to categories associated with {1}.'.
                      format(cat.category, cn.name))
                cn.categories.append(cat)
        if form.description.data != cn.description:
            edited = True
            flash('Description changed to: \'{0}\''
                  .format(form.description.data))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to common name: \'{0}\''.format(cn.name))
            return redirect(url_for('seeds.edit_common_name', cn_id=cn.id))
    form.populate(cn)
    current_categories = ', '.join([category.category for category in
                                    cn.categories])
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_common_name', cn_id=cn_id),
         'Edit Common Name')
    )
    return render_template('seeds/edit_common_name.html',
                           crumbs=crumbs,
                           form=form,
                           current_categories=current_categories)


@seeds.route('/edit_packet', methods=['GET', 'POST'])
@seeds.route('/edit_packet/<pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_packet(pkt_id=None):
    if pkt_id is None:
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
    packet = Packet.query.get(pkt_id)
    if packet is None:
        flash('Error: Specified packet was not found! Please select one:')
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
    form = EditPacketForm()
    form.set_selects()
    if form.validate_on_submit():
        edited = False
        if form.price.data is not None and form.price.data != '':
            packet.price = form.price.data
            edited = True
        elif form.prices.data != packet._price.id:
            packet._price = Price.query.get(form.prices.data)
            edited = True
        if form.quantity.data is not None and form.quantity.data != '':
            packet.quantity = form.quantity.data
            edited = True
        elif form.quantities.data != str(packet.quantity):
            packet.quantity = form.quantities.data
            edited = True
        if form.unit.data is not None and form.unit.data != '':
            packet.unit = form.unit.data
            edited = True
        elif form.units.data != packet._unit.id:
            packet._unit = Unit.query.get(form.units.data)
            edited = True
        if form.sku.data != packet.sku:
            packet.sku = form.sku.data
            edited = True
        if edited:
            flash('Packet changed to: SKU {0} - ${1} for {2} {3}'.
                  format(packet.sku,
                         packet.price,
                         packet.quantity,
                         packet.unit))
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to packet: SKU {0} - ${1} for {2} {3}'.
                  format(packet.sku,
                         packet.price,
                         packet.quantity,
                         packet.unit))
            return redirect(url_for('seeds.edit_packet', pkt_id=pkt_id))
    form.populate(packet)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_packet', pkt_id=pkt_id), 'Edit Packet')
    )
    return render_template('seeds/edit_packet.html',
                           crumbs=crumbs,
                           form=form,
                           packet=packet)


@seeds.route('/edit_seed', methods=['GET', 'POST'])
@seeds.route('/edit_seed/<seed_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_seed(seed_id=None):
    """Edit a seed stored in the database."""
    if seed_id is None:
        return redirect(url_for('seeds.select_seed', dest='seeds.edit_seed'))
    seed = Seed.query.get(seed_id)
    if seed is None:
        flash('Error: invalid seed number! Please select a seed:')
        return redirect(url_for('seeds.select_seed', dest='seeds.edit_seed'))
    form = EditSeedForm()
    form.set_selects()
    if form.validate_on_submit():
        edited = False
        if seed.botanical_names:
            for bn in seed.botanical_names:
                if bn.id not in form.botanical_names.data:
                    edited = True
                    flash('Removed botanical name \'{0}\' from: {1}'.
                          format(bn.name, seed.fullname))
                    seed.botanical_names.remove(bn)
        if form.botanical_names.data:
            for bn_id in form.botanical_names.data:
                if bn_id not in [bn.id for bn in seed.botanical_names]:
                    edited = True
                    bn = BotanicalName.query.get(bn_id)
                    flash('Added botanical name \'{0}\' to: {1}'.
                          format(bn.name, seed.fullname))
                    seed.botanical_names.append(bn)
        for cat in seed.categories:
            if cat.id not in form.categories.data:
                edited = True
                flash('Removed category \'{0}\' from: {1}'.
                      format(cat.category, seed.fullname))
                seed.categories.remove(cat)
        for cat_id in form.categories.data:
            if cat_id not in [cat.id for cat in seed.categories]:
                edited = True
                cat = Category.query.get(cat_id)
                flash('Added category \'{0}\' to: {1}'.
                      format(cat.category, seed.fullname))
                seed.categories.append(cat)
        if form.common_name.data != seed.common_name.id:
            edited = True
            cn = CommonName.query.get(form.common_name.data)
            flash('Changed common name to \'{0}\' for: {1}'.
                  format(cn.name, seed.fullname))
            seed.common_name = CommonName.query.get(form.common_name.data)
        if form.description.data != seed.description:
            edited = True
            flash('Changed description for \'{0}\' to: \'{1}\''.
                  format(seed.fullname, form.description.data))
            seed.description = form.description.data
        if form.name.data.title() != seed.name:
            edited = True
            flash('Changed seed name from \'{0}\' to \'{1}\''.
                  format(seed.name, form.name.data.title()))
            seed.name = form.name.data.title()
        if form.in_stock.data:
            if not seed.in_stock:
                edited = True
                flash('\'{0}\' is now in stock.'.format(seed.fullname))
                seed.in_stock = True
        else:
            if seed.in_stock:
                edited = True
                flash('\'{0}\' is now out of stock.'.format(seed.fullname))
                seed.in_stock = False
        if form.dropped.data:
            if not seed.dropped:
                edited = True
                flash('\'{0}\' has been dropped.'.format(seed.fullname))
                seed.dropped = True
        else:
            if seed.dropped:
                edited = True
                flash('\'{0}\' is now active/no longer dropped.'.
                      format(seed.fullname))
                seed.dropped = False
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            if seed.thumbnail is None or thumb_name != seed.thumbnail.filename:
                edited = True
                flash('New thumbnail for \'{0}\' uploaded as: \'{1}\''.
                      format(seed.fullname, thumb_name))
                upload_path = os.path.join(current_app.config.
                                           get('IMAGES_FOLDER'),
                                           thumb_name)
                if seed.thumbnail is not None:
                    # Do not delete or orphan thumbnail, move to images.
                    # Do not directly add seed.thumbnail to seed.images, as
                    # that will cause a CircularDependencyError.
                    tb = seed.thumbnail
                    seed.thumbnail = None
                    seed.images.append(tb)
                seed.thumbnail = Image(filename=thumb_name)
                form.thumbnail.data.save(upload_path)
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to \'{0}\'.'.format(seed.fullname))
            return redirect(url_for('seeds.edit_seed', seed_id=seed_id))

    form.populate(seed)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_seed', seed_id=seed_id), 'Edit Seed')
    )
    return render_template('seeds/edit_seed.html',
                           crumbs=crumbs,
                           form=form,
                           seed=seed)


@seeds.route('/flip_dropped/<seed_id>')
@seeds.route('/flip_dropped')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_dropped(seed_id=None):
    """Reverse dropped status of given seed."""
    if seed_id is None:
        abort(404)
    seed = Seed.query.get(seed_id)
    if seed is None:
        abort(404)
    if seed.dropped:
        flash('\'{0}\' has been returned to active status.'.
              format(seed.fullname))
        seed.dropped = False
    else:
        flash('\'{0}\' has been dropped.'.
              format(seed.fullname))
        seed.dropped = True
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))


@seeds.route('/flip_in_stock/<seed_id>')
@seeds.route('/flip_in_stock')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_in_stock(seed_id=None):
    if seed_id is None:
        abort(404)
    seed = Seed.query.get(seed_id)
    if seed is None:
        abort(404)
    if seed.in_stock:
        flash('\'{0}\' is now out of stock.'.format(seed.fullname))
        seed.in_stock = False
    else:
        flash('\'{0}\' is now in stock.'.format(seed.fullname))
        seed.in_stock = True
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))


@seeds.route('/')
def index():
    """Index page for seeds section."""
    categories = Category.query.all()
    return render_template('seeds/index.html', categories=categories)


@seeds.route('/manage')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def manage():
    return render_template('seeds/manage.html')


@seeds.route('/remove_botanical_name', methods=['GET', 'POST'])
@seeds.route('/remove_botanical_name/<bn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_botanical_name(bn_id=None):
    """Remove a botanical name from the database."""
    if bn_id is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    if not bn_id.isdigit():
        flash('Error: Botanical name id must be an integer!'
              ' Please select a botanical name from the list:')
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    bn = BotanicalName.query.get(bn_id)
    if bn is None:
        flash('Error: No such botanical name exists!'
              ' Please select one from the list:')
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    form = RemoveBotanicalNameForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Botanical name {0}: \'{1}\' has been removed from the '
                  'database.'.format(bn.id, bn.name))
            db.session.delete(bn)
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if '
                  'you want to remove this botanical name.')
            return redirect(url_for('seeds.remove_botanical_name',
                                    bn_id=bn_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_botanical_name', bn_id=bn_id),
         'Remove Botanical Name')
    )
    return render_template('seeds/remove_botanical_name.html',
                           bn=bn,
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_category', methods=['GET', 'POST'])
@seeds.route('/remove_category/<category_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_category(category_id=None):
    """Remove a category from the database."""
    if category_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    if not category_id.isdigit():
        flash('Error: Category id must be an integer! '
              'Please select a category from the list:')
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    category = Category.query.get(category_id)
    if category is None:
        flash('Error: No such category exists. '
              'Please select one from the list:')
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    form = RemoveCategoryForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Category {0}: \'{1}\' has been removed from the database.'.
                  format(category.id, category.category))
            db.session.delete(category)
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\''
                  ' if you want to remove this category.')
            return redirect(url_for('seeds.remove_category',
                                    category_id=category_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category', category_id=category_id),
         'Remove Category')
    )
    return render_template('seeds/remove_category.html',
                           crumbs=crumbs,
                           form=form,
                           category=category)


@seeds.route('/remove_common_name', methods=['GET', 'POST'])
@seeds.route('/remove_common_name/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_common_name(cn_id=None):
    """Remove a common name from the database."""
    if cn_id is None:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.remove_common_name'))
    if not cn_id.isdigit():
        flash('Error: Common name id must be an integer! Please '
              'select a common name from the list:')
        return redirect(url_for('seeds.select_common_name',
                        dest='seeds.remove_common_name'))
    cn = CommonName.query.get(cn_id)
    if cn is None:
        flash('Error: No such common name exists. '
              'Please select one from the list:')
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.remove_common_name'))
    form = RemoveCommonNameForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Common name {0}: \'{1}\' has been removed from the '
                  'database.'.format(cn.id, cn.name))
            db.session.delete(cn)
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if '
                  'you want to remve this common name.')
            return redirect(url_for('seeds.remove_common_name', cn_id=cn_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_common_name', cn_id=cn_id),
         'Remove Common Name')
    )
    return render_template('seeds/remove_common_name.html',
                           crumbs=crumbs,
                           form=form,
                           cn=cn)


@seeds.route('/remove_packet', methods=['GET', 'POST'])
@seeds.route('/remove_packet/<pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_packet(pkt_id=None):
    """Remove a packet from the database."""
    if pkt_id is None:
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.remove_packet'))
    packet = Packet.query.get(pkt_id)
    if packet is None:
        flash('Error: No packet exists with given id! Please select one:')
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.remove_packet'))
    form = RemovePacketForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Packet SKU {0}: ${1} for {2} {3} has been removed from '
                  'the database.'.format(packet.sku,
                                         packet.price,
                                         packet.quantity,
                                         packet.unit))
            db.session.delete(packet)
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if you '
                  'want to remove this packet.')
            return redirect(url_for('seeds.remove_packet', pkt_id=pkt_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_packet', pkt_id=pkt_id), 'Remove Packet')
    )
    return render_template('seeds/remove_packet.html',
                           crumbs=crumbs,
                           form=form,
                           packet=packet)


@seeds.route('/remove_seed', methods=['GET', 'POST'])
@seeds.route('/remove_seed/<seed_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_seed(seed_id=None):
    if seed_id is None:
        return redirect(url_for('seeds.select_seed', dest='seeds.remove_seed'))
    seed = Seed.query.get(seed_id)
    if seed is None:
        flash('Error: No seed exists with that id! Please select one:')
        return redirect(url_for('seeds.select_seed', dest='seeds.remove_seed'))
    form = RemoveSeedForm()
    if form.validate_on_submit():
        if not form.verify_removal.data:
            flash('No changes made. Check the box labeled \'Yes\' if you '
                  'would like to remove this seed.')
            return redirect(url_for('seeds.remove_seed', seed_id=seed_id))
        if form.delete_images:
            rollback = False
            if seed.images:
                for image in seed.images:
                    try:
                        image.delete_file()
                        flash('Image file \'{0}\' deleted.'.
                              format(image.filename))
                        db.session.delete(image)
                    except OSError as e:
                        rollback = True
                        flash('Error: Attempting to delete \'{0}\' raised an '
                              'exception: {1}'.format(image.filename, e))
            if seed.thumbnail:
                try:
                    seed.thumbnail.delete_file()
                    flash('Thumbnail image \'{0}\' has been deleted.'.
                          format(seed.thumbnail.filename))
                    db.session.delete(seed.thumbnail)
                except OSError as e:
                    rollback = True
                    flash('Error: Attempting to delete \'{0}\' raised an '
                          'exception: {1}'.format(seed.thumbnail.filename, e))
        if rollback:
            flash('Error: Seed could not be deleted due to problems deleting '
                  'associated images.')
            db.session.rollback()
            return redirect(url_for('seeds.remove_seed', seed_id=seed_id))
        else:
            flash('The seed \'{0}\' has been deleted. Forever. I hope you\'re '
                  'happy with yourself.'.format(seed.fullname))
            db.session.delete(seed)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
    form.delete_images.data = True
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_seed', seed_id=seed_id), 'Remove Seed')
    )
    return render_template('seeds/remove_seed.html',
                           crumbs=crumbs,
                           form=form,
                           seed=seed)


@seeds.route('/<cat_slug>/<cn_slug>/<seed_slug>')
def seed(cat_slug=None, cn_slug=None, seed_slug=None):
    """Display a page for a given seed."""
    cat = Category.query.filter_by(slug=cat_slug).first()
    cn = CommonName.query.filter_by(slug=cn_slug).first()
    seed = Seed.query.filter_by(slug=seed_slug).first()
    if (cat is not None and cn is not None and seed is not None) and \
            (cat in seed.categories and cn is seed.common_name):
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.category', cat_slug=cat_slug), cat.header),
            (url_for('seeds.common_name', cat_slug=cat_slug, cn_slug=cn_slug),
             cn.name),
            (url_for('seeds.seed',
                     cat_slug=cat_slug,
                     cn_slug=cn_slug,
                     seed_slug=seed_slug),
             seed.name)
        )
        return render_template('seeds/seed.html',
                               cat_slug=cat_slug,
                               cn_slug=cn_slug,
                               crumbs=crumbs,
                               seed=seed)
    else:
        abort(404)


@seeds.route('/select_botanical_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_botanical_name():
    """Select a botanical name to load on another page.

    Request Args:
        dest (str): The route to redirect to once botanical name is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectBotanicalNameForm()
    form.set_names()
    if form.validate_on_submit():
        return redirect(url_for(dest, bn_id=form.names.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_botanical_name', dest=dest),
         'Select Botanical Name')
    )
    return render_template('seeds/select_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_category', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_category():
    """Select a category to load on another page.

    Request Args:
        dest (str): The route to redirect to once category is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCategoryForm()
    form.set_categories()
    if form.validate_on_submit():
        return redirect(url_for(dest, category_id=form.categories.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_category', dest=dest), 'Select Category')
    )
    return render_template('seeds/select_category.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_common_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_common_name():
    """Select a common name to load on another page.

    Request Args:
        dest (str): The route to redirect to once category is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCommonNameForm()
    form.set_names()
    if form.validate_on_submit():
        return redirect(url_for(dest, cn_id=form.names.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_common_name', dest=dest), 'Select Common Name')
    )
    return render_template('seeds/select_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_packet', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_packet():
    """Select a packet to load on another page.

    Request Args:
        dest (str): The route to redirect to with selected packet id.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectPacketForm()
    form.set_packets()
    if form.validate_on_submit():
        return redirect(url_for(dest, pkt_id=form.packets.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_packet', dest=dest), 'Select Packet')
    )
    return render_template('seeds/select_packet.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_seed', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_seed():
    """Select a seed to load on another page.

    Request Args:
        dest (str): The route to redirect to once seed is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectSeedForm()
    form.set_seeds()
    if form.validate_on_submit():
        return redirect(url_for(dest, seed_id=form.seeds.data))
    crumbs = make_breadcrumbs(
            (url_for('seeds.manage'), 'Manage Seeds'),
            (url_for('seeds.select_seed', dest=dest), 'Select Seed')
    )
    return render_template('seeds/select_seed.html',
                           crumbs=crumbs,
                           form=form)

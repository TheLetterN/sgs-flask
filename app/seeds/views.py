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
from flask import abort, current_app, flash, redirect, render_template, \
    request, url_for
from werkzeug import secure_filename
from flask.ext.login import login_required
from . import seeds
from .models import BotanicalName, Category, CommonName, Image, Packet, Seed, \
    Unit
from .forms import AddBotanicalNameForm, AddCategoryForm, AddCommonNameForm, \
    AddPacketForm, AddSeedForm, EditBotanicalNameForm, \
    EditCategoryForm, EditCommonNameForm, RemoveBotanicalNameForm, \
    RemoveCategoryForm, RemoveCommonNameForm, SelectBotanicalNameForm, \
    SelectCategoryForm, SelectCommonNameForm, SelectSeedForm
from app import db, make_breadcrumbs
from app.decorators import permission_required
from app.auth.models import Permission


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
        if len(form.additional_categories.data) > 0:
            for category in form.additional_categories.data.split(','):
                cat = Category.query.filter_by(category=category.
                                               strip().title()).first()
                if cat is None:
                    cat = Category(category=category.strip().title())
                flash('{0} added to categories associated with {1}.'.
                      format(cat.category, cn.name))
                cn.categories.append(cat)
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
        flash('Packet SKU {0}: ${1} for {2} {3} added to {4}'.
              format(packet.sku,
                     packet.price,
                     packet.quantity, 
                     packet.unit,
                     seed.name))
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
        for cn_id in form.common_names.data:
            cn = CommonName.query.get(cn_id)
            flash('\'{0}\' added to common names for {1}.'.
                  format(cn.name, form.name.data))
            seed.common_names.append(cn)
        seed.name = form.name.data.title()
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                       thumb_name)
            seed.thumbnail = Image(filename=thumb_name)
            flash('Thumbnail uploaded to: {0}'.format(upload_path))
            form.thumbnail.data.save(upload_path)
        seed.description = form.description.data
        flash('New seed \'{0}\' has been added to the database.'.
              format(seed.name))
        db.session.commit()
        return redirect(url_for('seeds.add_packet', seed_id=seed.id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_seed'), 'Add Seed')
    )
    return render_template('seeds/add_seed.html', crumbs=crumbs, form=form)


@seeds.route('/<category_slug>')
def category(category_slug=None):
    """Display a category."""
    category = Category.query.filter_by(slug=category_slug).first()
    if category is not None:
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.category', category_slug=category.slug),
             '{0} Seeds'.format(category.category))
        )
        return render_template('seeds/category.html',
                               crumbs=crumbs,
                               category=category)
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
        if len(form.add_common_names.data) > 0:
            for cn_id in form.add_common_names.data:
                cn = CommonName.query.get(cn_id)
                if cn not in bn.common_names:
                    edited = True
                    flash('\'{0}\' added to common names associated with '
                          '\'{1}\'.'.format(cn.name, bn.name))
                    bn.common_names.append(cn)
        if len(form.remove_common_names.data) > 0:
            for cn_id in form.remove_common_names.data:
                cn = CommonName.query.get(cn_id)
                if cn in bn.common_names:
                    edited = True
                    flash('\'{0}\' removed from common names associated with '
                          '\'{1}\'.'.format(cn.name, bn.name))
                    bn.common_names.remove(cn)
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
        if len(form.add_categories.data) > 0:
            for cat_id in form.add_categories.data:
                cat = Category.query.get(cat_id)
                if cat not in cn.categories:
                    edited = True
                    flash('{0} added to categories associated with {1}.'.
                          format(cat.category, cn.name))
                    cn.categories.append(cat)
        if len(form.remove_categories.data) > 0:
            for cat_id in form.remove_categories.data:
                cat = Category.query.get(cat_id)
                if cat in cn.categories:
                    edited = True
                    flash('{0} removed from categories associated with {1}.'.
                          format(cat.category, cn.name))
                    cn.categories.remove(cat)
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

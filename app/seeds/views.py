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
    Markup,
    redirect,
    render_template,
    request,
    url_for
)
from werkzeug import secure_filename
from flask.ext.login import login_required
from app import db, dbify, make_breadcrumbs
from app.decorators import permission_required
from app.pending import Pending
from app.redirects import Redirect, RedirectsFile
from app.auth.models import Permission
from . import seeds
from ..lastcommit import LastCommit
from .models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Packet,
    Quantity,
    Cultivar,
    Series,
    USDInt
)
from .forms import (
    AddBotanicalNameForm,
    AddCategoryForm,
    AddCommonNameForm,
    AddPacketForm,
    AddRedirectForm,
    AddCultivarForm,
    AddSeriesForm,
    EditBotanicalNameForm,
    EditCategoryForm,
    EditCommonNameForm,
    EditPacketForm,
    EditCultivarForm,
    EditSeriesForm,
    RemoveBotanicalNameForm,
    RemoveCategoryForm,
    RemoveCommonNameForm,
    RemovePacketForm,
    RemoveSeriesForm,
    RemoveCultivarForm,
    SelectBotanicalNameForm,
    SelectCategoryForm,
    SelectCommonNameForm,
    SelectPacketForm,
    SelectCultivarForm,
    SelectSeriesForm,
    syn_parents_links
)


def list_to_or_string(lst):
    """Return a comma-separated list with 'or' before the last element.

    Args:
        lst (list): A list of strings to convert to a single string.

    Examples:
        >>> list_to_or_string(['frogs'])
        'frogs'

        >>> list_to_or_string(['frogs', 'toads'])
        'frogs or toads'

        >>> list_to_or_string(['frogs', 'toads', 'salamanders'])
        'frogs, toads, or salamanders'
    """
    if len(lst) > 1:
        if len(lst) == 2:
            return ' or '.join(lst)
        else:
            lstc = list(lst)  # Don't change values of original list
            lstc[-1] = 'or ' + lstc[-1]
            return ', '.join(lstc)
    else:
        return lst[0]


def redirect_warning(old_path, links):
    """Generate a message warning that a redirect should be created.

    Args:
        old_path (str): The path that has been rendered invalid.
        links (str): A link or links to forms to add possible redirects.

    Returns:
        Markup: A string containing a warning that a redirect should be added.
    """
    return Markup('Warning: the path \'{0}\' is no longer valid. You may wish '
                  'to redirect it to {1}.'.format(old_path, links))


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
    """Handle web interface for adding BotanicalName objects to database."""
    form = AddBotanicalNameForm()
    form.set_common_name()
    if form.validate_on_submit():
        bn = BotanicalName()
        db.session.add(bn)
        bn.name = form.name.data
        cn = CommonName.query.get(form.common_name.data)
        bn.common_name = cn
        if form.synonyms.data:
            bn.set_synonyms_from_string_list(form.synonyms.data)
            flash('Synonyms for \'{0}\' set to: {1}'
                  .format(bn.name, bn.list_synonyms_as_string()))
        db.session.commit()
        flash('Botanical name \'{0}\' belonging to \'{1}\' has been added.'.
              format(bn.name, cn.name))
        return redirect(url_for('seeds.{0}'.format(form.next_page.data)))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category'),
        (url_for('seeds.add_common_name'), 'Add Common Name'),
        (url_for('seeds.add_botanical_name'), 'Add Botanical Name')
    )
    return render_template('seeds/add_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_category', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_category():
    """Handle web interface for adding Category objects to the database."""
    form = AddCategoryForm()
    if form.validate_on_submit():
        category = Category()
        db.session.add(category)
        category.name = dbify(form.category.data)
        if form.description.data:
            category.description = form.description.data
            flash('Description for \'{0}\' set to: {1}'
                  .format(category.name, category.description))
        db.session.commit()
        flash('New category \'{0}\' has been added to the database.'.
              format(category.name))
        return redirect(url_for('seeds.add_common_name'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category')
    )
    return render_template('seeds/add_category.html', crumbs=crumbs, form=form)


@seeds.route('/add_common_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_common_name():
    """Handle web interface for adding CommonName objects to the database."""
    form = AddCommonNameForm()
    form.set_selects()
    if form.validate_on_submit():
        cn = CommonName()
        db.session.add(cn)
        cn.name = dbify(form.name.data)
        for cat_id in form.categories.data:
            category = Category.query.get(cat_id)
            cn.categories.append(category)
            flash('The common name \'{0}\' has been added to the category '
                  '\'{1}\'.'.format(cn.name, category.name))
        if form.description.data:
            cn.description = form.description.data
            flash('Description for \'{0}\' set to: {1}'
                  .format(cn.name, cn.description))
        else:
            cn.description = None
        if form.instructions.data:
            cn.instructions = form.instructions.data
            flash('Planting instructions for \'{0}\' set to: {1}'
                  .format(cn.name, cn.instructions))
        else:
            cn.instructions = None
        if form.synonyms.data:
            cn.set_synonyms_from_string_list(form.synonyms.data)
            flash('Synonyms for \'{0}\' set to: {1}'
                  .format(cn.name, cn.list_synonyms_as_string()))
        if form.gw_common_names.data:
            for cn_id in form.gw_common_names.data:
                gw_cn = CommonName.query.get(cn_id)
                cn.gw_common_names.append(gw_cn)
                gw_cn.gw_common_names.append(cn)
                flash('\'{0}\' added to Grows With for \'{1}\', and vice '
                      'versa.'.format(gw_cn.name, cn.name))
        if form.gw_cultivars.data:
            for cv_id in form.gw_cultivars.data:
                gw_cv = Cultivar.query.get(cv_id)
                cn.gw_cultivars.append(gw_cv)
                flash('\'{0}\' added to Grows With for \'{1}\', and vice '
                      'versa.'.format(gw_cv.fullname, cn.name))
        if form.parent_cn.data:
            cn.parent = CommonName.query.get(form.parent_cn.data)
            flash('\'{0}\' has been set as a subcategory of \'{1}\'.'
                  .format(cn.name, cn.parent.name))
        db.session.commit()
        flash('The common name \'{0}\' has been added to the database.'.
              format(cn.name, category.plural))
        return redirect(url_for('seeds.{0}'.format(form.next_page.data)))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category'),
        (url_for('seeds.add_common_name'), 'Add Common Name')
    )
    return render_template('seeds/add_common_name.html', crumbs=crumbs,
                           form=form)


@seeds.route('/add_packet', methods=['GET', 'POST'])
@seeds.route('/add_packet/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_packet(cv_id=None):
    """Add a packet to the database."""
    if cv_id is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.add_packet'))
    cv = Cultivar.query.get(cv_id)
    if not cv:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.add_packet'))
    form = AddPacketForm()
    if form.validate_on_submit():
        packet = Packet()
        db.session.add(packet)
        packet.cultivar = cv
        packet.price = form.price.data.strip()
        fq = Quantity.for_cmp(form.quantity.data)
        fu = form.units.data.strip()
        qty = Quantity.query.filter(Quantity.value == fq,
                                    Quantity.units == fu).first()
        if qty:
            packet.quantity = qty
        else:
            packet.quantity = Quantity(value=fq, units=fu)
        packet.sku = form.sku.data.strip()
        db.session.commit()
        flash('Packet {0} added to {1}.'.format(packet.info, cv.fullname))
        if form.again.data:
            return redirect(url_for('seeds.add_packet', cv_id=cv_id))
        else:
            return redirect(url_for('seeds.manage'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category'),
        (url_for('seeds.add_common_name'), 'Add Common Name'),
        (url_for('seeds.add_botanical_name'), 'Add Botanical Name'),
        (url_for('seeds.add_series'), 'Add Series'),
        (url_for('seeds.add_cultivar'), 'Add Cultivar'),
        (url_for('seeds.add_packet'), 'Add Packet')
    )
    return render_template('seeds/add_packet.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/add_redirect', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_redirect():
    """Add a redirect from an old path to a new one."""
    form = AddRedirectForm()
    if form.validate_on_submit():
        rdf = RedirectsFile(current_app.config.get('REDIRECTS_FILE'))
        if rdf.exists():
            rdf.load()
        rd = Redirect(form.old_path.data,
                      form.new_path.data,
                      form.status_code.data)
        pending = Pending(current_app.config.get('PENDING_FILE'))
        if pending.exists():
            pending.load()
        pending.add_message(rd.message() + '<br>')
        rdf.add_redirect(rd)
        pending.save()
        rdf.save()
        flash('{0} added. It will take effect on next restart of Flask app.'
              .format(rd.message()))
        return redirect(url_for('seeds.manage'))
    op = request.args.get('old_path')
    if op:
        form.old_path.data = op
    np = request.args.get('new_path')
    if np:
        form.new_path.data = np
    sc = request.args.get('status_code')
    if sc:
        form.status_code.data = int(sc)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_redirect'), 'Add Redirect')
    )
    return render_template('seeds/add_redirect.html', crumbs=crumbs, form=form)


@seeds.route('/add_cultivar', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_cultivar():
    """Add a cultivar to the database."""
    form = AddCultivarForm()
    form.set_selects()
    if form.validate_on_submit():
        cv = Cultivar()
        db.session.add(cv)
        cv.name = dbify(form.name.data)
        cv.common_name = CommonName.query.get(form.common_name.data)
        if form.botanical_name.data:
            cv.botanical_name = BotanicalName.query\
                .get(form.botanical_name.data)
            flash('Botanical name for \'{0}\' set to: {1}'
                  .format(cv.fullname, cv.botanical_name.name))
        if form.categories.data:
            for cat_id in form.categories.data:
                cat = Category.query.get(cat_id)
                flash('\'{0}\' added to categories for {1}.'.
                      format(cat.name, form.name.data))
                cv.categories.append(cat)
        else:
            flash('No categories specified, will use categories from common '
                  ' name \'{0}\''.format(cv.common_name.name))
            for cat in cv.common_name.categories:
                cv.categories.append(cat)
        if form.gw_common_names.data:
            for cn_id in form.gw_common_names.data:
                gw_cn = CommonName.query.get(cn_id)
                cv.gw_common_names.append(gw_cn)
                flash('\'{0}\' added to Grows With for \'{1}\', and vice '
                      'versa.'.format(gw_cn.name, cv.name))
        if form.gw_cultivars.data:
            for cv_id in form.gw_cultivars.data:
                gw_cv = Cultivar.query.get(cv_id)
                cv.gw_cultivars.append(gw_cv)
                gw_cv.gw_cultivars.append(cv)
                flash('\'{0}\' added to Grows With for \'{1}\', and vice '
                      'versa.'.format(gw_cv.fullname, cv.name))
        if form.series.data:
            cv.series = Series.query.get(form.series.data)
            flash('Series set to: {0}'.format(cv.series.name))
        if form.synonyms.data:
            cv.set_synonyms_from_string_list(form.synonyms.data)
            flash('Synonyms for \'{0}\' set to: {1}'
                  .format(cv.fullname, cv.list_synonyms_as_string()))
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                       thumb_name)
            cv.thumbnail = Image(filename=thumb_name)
            flash('Thumbnail uploaded as: {0}'.format(thumb_name))
            form.thumbnail.data.save(upload_path)
        if form.description.data:
            cv.description = form.description.data
            flash('Description set to: {0}'.format(cv.description))
        if form.in_stock.data:
            cv.in_stock = True
            flash('\'{0}\' is in stock.'.format(cv.fullname))
        else:
            flash('\'{0}\' is not in stock.'.format(cv.fullname))
            cv.in_stock = False
        if form.dropped.data:
            flash('\'{0}\' is currently dropped/inactive.'.
                  format(cv.fullname))
            cv.dropped = True
        else:
            flash('\'{0}\' is currently active.'.
                  format(cv.fullname))
            cv.dropped = False
        flash('New cultivar \'{0}\' has been added to the database.'.
              format(cv.fullname))
        db.session.commit()
        return redirect(url_for('seeds.add_packet', cv_id=cv.id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category'),
        (url_for('seeds.add_common_name'), 'Add Common Name'),
        (url_for('seeds.add_botanical_name'), 'Add Botanical Name'),
        (url_for('seeds.add_series'), 'Add Series'),
        (url_for('seeds.add_cultivar'), 'Add Cultivar')
    )
    return render_template('seeds/add_cultivar.html', crumbs=crumbs, form=form)


@seeds.route('/add_series', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_series():
    """Add a series to the database."""
    form = AddSeriesForm()
    form.set_common_name()
    if form.validate_on_submit():
        series = Series()
        db.session.add(series)
        series.common_name = CommonName.query.get(form.common_name.data)
        series.name = dbify(form.name.data)
        series.description = form.description.data
        flash('New series \'{0}\' added to: {1}.'.
              format(series.name, series.common_name.name))
        db.session.commit()
        return redirect(url_for('seeds.add_cultivar'))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.add_category'), 'Add Category'),
        (url_for('seeds.add_common_name'), 'Add Common Name'),
        (url_for('seeds.add_botanical_name'), 'Add Botanical Name'),
        (url_for('seeds.add_series'), 'Add Series')
    )
    return render_template('seeds/add_series.html', crumbs=crumbs, form=form)


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
    bn = BotanicalName.query.get(bn_id)
    if bn is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
    form = EditBotanicalNameForm()
    form.set_common_name()
    if form.validate_on_submit():
        edited = False
        if form.name.data != bn.name:
            bn2 = BotanicalName.query.filter_by(_name=form.name.data).first()
            if bn2 and bn2 not in bn.synonyms:
                if not bn2.syn_only:
                    bn2_url = url_for('seeds.edit_botanical_name',
                                      bn_id=bn2.id)
                    flash(Markup(('Error: Botanical name \'{0}\' is already '
                                  'in use! <a href="{1}">Click here</a> if '
                                  'you wish to edit it.'
                                  .format(bn2.name, bn2_url))))
                else:
                    flash(Markup('Error: The botanical name \'{0}\' already '
                                 'exists as a synonym of: {1}. You will '
                                 'need to remove it as a synonym before '
                                 'adding it here.'
                                 .format(bn2.name, syn_parents_links(bn2))))
                return redirect(url_for('seeds.edit_botanical_name',
                                        bn_id=bn_id))
            else:
                edited = True
                flash('Botanical name \'{0}\' changed to \'{1}\'.'.
                      format(bn.name, form.name.data))
                if bn2 in bn.synonyms:
                    bn.clear_synonyms()
                    db.session.commit()
                bn.name = form.name.data
        if form.common_name.data != bn.common_name.id:
            edited = True
            cn = CommonName.query.get(form.common_name.data)
            flash('Common name associated with botanical name \'{0}\' changed'
                  ' from \'{1}\' to: \'{2}\'.'.format(bn.name,
                                                      bn.common_name.name,
                                                      cn.name))
            bn.common_name = cn
        if form.synonyms.data != bn.list_synonyms_as_string():
            edited = True
            if form.synonyms.data:
                bn.set_synonyms_from_string_list(form.synonyms.data)
                flash('Synonyms for \'{0}\' set to: {1}'
                      .format(bn.name, bn.list_synonyms_as_string()))
            else:
                bn.clear_synonyms()
                flash('Synonyms for \'{0}\' cleared.'.format(bn.name))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to the botanical name: \'{0}\'.'.
                  format(bn.name))
            return redirect(url_for('seeds.edit_botanical_name', bn_id=bn_id))
    form.populate(bn)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'),
         'Edit Botanical Name')
    )
    return render_template('/seeds/edit_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_category', methods=['GET', 'POST'])
@seeds.route('/edit_category/<cat_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_category(cat_id=None):
    if cat_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
    category = Category.query.get(cat_id)
    if category is None:
        return redirect(url_for('seeds.select_category',
                        dest='seeds.edit_category'))
    form = EditCategoryForm()
    if form.validate_on_submit():
        edited = False
        form_cat = dbify(form.category.data)
        if form_cat != category.name:
            cat2 = Category.query.filter_by(name=form_cat).first()
            if cat2:
                cat2_url = url_for('seeds.edit_category', cat_id=cat2.id)
                flash(Markup('Error: Category \'{0}\' already exists. <a '
                             'href="{1}">Click here</a> if you wish to edit '
                             'it.'.format(cat2.name, cat2_url)))
                return redirect(url_for('seeds.edit_category', cat_id=cat_id))
            else:
                edited = True
                flash('Category changed from \'{0}\' to \'{1}\'.'
                      .format(category.name, form_cat))
                old_slug = category.slug
                category.name = form_cat
                new_slug = category.slug
                old_path = url_for('seeds.category', cat_slug=old_slug)
                new_path = url_for('seeds.category', cat_slug=new_slug)
                flash(redirect_warning(
                    old_path,
                    '<a href="{0}" target="_blank">{1}</a>'
                    .format(url_for('seeds.add_redirect',
                                    old_path=old_path,
                                    new_path=new_path,
                                    status_code=301),
                            new_path)
                ))
                for cn in category.common_names:
                    old_path = url_for('seeds.common_name',
                                       cat_slug=old_slug,
                                       cn_slug=cn.slug)
                    new_path = url_for('seeds.common_name',
                                       cat_slug=new_slug,
                                       cn_slug=cn.slug)
                    flash(redirect_warning(
                        old_path,
                        '<a href="{0}" target="_blank">{1}</a>'
                        .format(url_for('seeds.add_redirect',
                                        old_path=old_path,
                                        new_path=new_path,
                                        status_code=301),
                                new_path)
                    ))
                for cv in category.cultivars:
                    old_path = url_for('seeds.cultivar',
                                       cat_slug=old_slug,
                                       cn_slug=cv.common_name.slug,
                                       cv_slug=cv.slug)
                    new_path = url_for('seeds.cultivar',
                                       cat_slug=new_slug,
                                       cn_slug=cv.common_name.slug,
                                       cv_slug=cv.slug)
                    flash(redirect_warning(
                        old_path,
                        '<a href="{0}" target="_blank">{1}</a>'
                        .format(url_for('seeds.add_redirect',
                                        old_path=old_path,
                                        new_path=new_path,
                                        status_code=301),
                                new_path)
                    ))
        if form.description.data != category.description:
            edited = True
            if form.description.data:
                category.description = form.description.data
                flash('Description for \'{0}\' changed to: {1}'
                      .format(category.name, category.description))
            else:
                category.description = None
                flash('Description for \'{0}\' has been cleared.'
                      .format(category.name))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to category: {0}'.format(category.name))
            return redirect(url_for('seeds.edit_category', cat_id=cat_id))
    form.populate(category)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category')
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
    cn = CommonName.query.get(cn_id)
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
    form = EditCommonNameForm()
    form.set_selects()
    if form.validate_on_submit():
        edited = False
        form_name = dbify(form.name.data)
        old_cn_slug = cn.slug
        new_cn_slug = ''
        if form_name != cn.name:
            cn2 = CommonName.query.filter_by(_name=form_name).first()
            if cn2 and cn2 not in cn.synonyms:
                if not cn2.syn_only:
                    cn2_url = url_for('seeds.edit_common_name', cn_id=cn2.id)
                    flash(Markup('Error: the common name \'{0}\' is already '
                                 'in use. <a href="{1}">Click here</a> if you '
                                 'wish to edit it.'
                                 .format(cn2.name, cn2_url)))
                else:
                    flash(Markup('Error: The common name \'{0}\' already '
                                 'exists as a synonym of: {1}. You will need '
                                 'to remove it as a synonym if you wish to '
                                 'add it here.'
                                 .format(cn2.name, syn_parents_links(cn2))))
                return redirect(url_for('seeds.edit_common_name', cn_id=cn_id))
            else:
                if cn2 in cn.synonyms:
                    # Safe to clear synonyms because from will replace them
                    cn.clear_synonyms()
                    db.session.commit()
                edited = True
                flash('Common name \'{0}\' changed to \'{1}\'.'.
                      format(cn.name, form_name))
                cn.name = form_name
        new_cn_slug = cn.slug
        cats_removed = []
        for cat in list(cn.categories):
            if cat.id not in form.categories.data:
                cats_removed.append(cat)
                edited = True
                flash('\'{0}\' removed from categories associated with {1}.'.
                      format(cat.name, cn.name))
                cn.categories.remove(cat)
                for cv in cn.cultivars:
                    if cat in cv.categories:
                        cv.categories.remove(cat)
                        flash(Markup(
                            'Warning: the category \'{0}\' has also been '
                            'removed from the cultivar \'{1}\'. You may wish '
                            'to <a href="{2}" target="_blank">edit {1}</a> to '
                            'ensure it is in the correct categories.'
                            .format(cat.name,
                                    cv.fullname,
                                    url_for('seeds.edit_cultivar',
                                            cv_id=cv.id))
                        ))
        cat_ids = [cat.id for cat in cn.categories]
        cats_added = []
        for cat_id in form.categories.data:
            if cat_id not in cat_ids:
                edited = True
                cat = Category.query.get(cat_id)
                flash('\'{0}\' added to categories associated with {1}.'
                      .format(cat.name, cn.name))
                cn.categories.append(cat)
                cats_added.append(cat)
                for cv in cn.cultivars:
                    if not cv.categories:
                        cv.categories.append(cat)
                        flash(Markup(
                            'Warning: the cultivar \'{0}\' had no categories '
                            'associated with it, so \'{1}\' has been added to '
                            'it to ensure it is not orphaned. You may wish to '
                            '<a href="{2}" target="_blank">edit {0}</a> to '
                            'ensure it is in the correct categories.'
                            .format(cv.fullname,
                                    cat.name,
                                    url_for('seeds.edit_cultivar',
                                            cv_id=cv.id))
                        ))
        if cats_removed:
            for cat in cats_removed:
                urllist = []
                old_path = url_for('seeds.common_name',
                                   cat_slug=cat.slug,
                                   cn_slug=old_cn_slug)
                for cn_cat in cn.categories:
                    new_path = url_for('seeds.common_name',
                                       cat_slug=cn_cat.slug,
                                       cn_slug=new_cn_slug)
                    urllist.append('<a href="{0}" target="_blank">{1}</a>'
                                   .format(url_for('seeds.add_redirect',
                                                   old_path=old_path,
                                                   new_path=new_path,
                                                   status_code=301),
                                           new_path))
                flash(redirect_warning(old_path, list_to_or_string(urllist)))
                for cv in cn.cultivars:
                    old_path = url_for('seeds.cultivar',
                                       cat_slug=cat.slug,
                                       cn_slug=old_cn_slug,
                                       cv_slug=cv.slug)
                    urllist = []
                    for cn_cat in cn.categories:
                        new_path = url_for('seeds.cultivar',
                                           cat_slug=cn_cat.slug,
                                           cn_slug=new_cn_slug,
                                           cv_slug=cv.slug)
                        urllist.append('<a href="{0}" target="_blank">{1}</a>'
                                       .format(url_for('seeds.add_redirect',
                                                       old_path=old_path,
                                                       new_path=new_path,
                                                       status_code=301),
                                               new_path))
                    flash(redirect_warning(old_path,
                                           list_to_or_string(urllist)))
        if new_cn_slug != old_cn_slug:
            for cat in cn.categories:
                if cat not in cats_added:
                    old_path = url_for('seeds.common_name',
                                       cat_slug=cat.slug,
                                       cn_slug=old_cn_slug)
                    new_path = url_for('seeds.common_name',
                                       cat_slug=cat.slug,
                                       cn_slug=new_cn_slug)
                    flash(redirect_warning(
                        old_path,
                        '<a href="{0}" target="_blank">{1}</a>'
                        .format(url_for('seeds.add_redirect',
                                        old_path=old_path,
                                        new_path=new_path,
                                        status_code=301),
                                new_path)
                    ))
                    for cv in cn.cultivars:
                        old_path = url_for('seeds.cultivar',
                                           cat_slug=cat.slug,
                                           cn_slug=old_cn_slug,
                                           cv_slug=cv.slug)
                        new_path = url_for('seeds.cultivar',
                                           cat_slug=cat.slug,
                                           cn_slug=new_cn_slug,
                                           cv_slug=cv.slug)
                        flash(redirect_warning(
                            old_path,
                            '<a href="{0}" target="_blank">{1}</a>'
                            .format(url_for('seeds.add_redirect',
                                            old_path=old_path,
                                            new_path=new_path,
                                            status_code=301),
                                    new_path)
                        ))
        if not form.description.data:
            form.description.data = None
        if form.description.data != cn.description:
            edited = True
            if form.description.data:
                cn.description = form.description.data
                flash('Description for \'{0}\' changed to: {1}'
                      .format(cn.name, cn.description))
            else:
                cn.description = None
                flash('Description for \'{0}\' has been cleared.'
                      .format(cn.name))
        if cn.gw_common_names:
            for gw_cn in list(cn.gw_common_names):
                if gw_cn.id not in form.gw_common_names.data:
                    edited = True
                    flash('\'{0}\' removed from Grows With for \'{1}\', and '
                          'vice versa.'.format(gw_cn.name, cn.name))
                    if cn in gw_cn.gw_common_names:
                        gw_cn.gw_common_names.remove(cn)
                    cn.gw_common_names.remove(gw_cn)
        if form.gw_common_names.data:
            for gw_cn_id in form.gw_common_names.data:
                if gw_cn_id != 0 and gw_cn_id != cn.id:
                    gw_cn = CommonName.query.get(gw_cn_id)
                    if gw_cn not in cn.gw_common_names:
                        edited = True
                        flash('\'{0}\' added to Grows With for \'{1}\', and '
                              'vice versa.'.format(gw_cn.name, cn.name))
                        cn.gw_common_names.append(gw_cn)
                        gw_cn.gw_common_names.append(cn)
        if cn.gw_cultivars:
            for gw_cv in list(cn.gw_cultivars):
                if gw_cv.id not in form.gw_cultivars.data:
                    edited = True
                    flash('\'{0}\' removed from Grows With for \'{1}\', and '
                          'vice versa'.format(gw_cv.name, cn.name))
                    cn.gw_cultivars.remove(gw_cv)
        if form.gw_cultivars.data:
            for gw_cv_id in form.gw_cultivars.data:
                if gw_cv_id != 0:
                    gw_cv = Cultivar.query.get(gw_cv_id)
                    if gw_cv not in cn.gw_cultivars:
                        edited = True
                        flash('\'{0}\' added to Grows With for \'{1}\', and '
                              'vice versa.'.format(gw_cv.fullname, cn.name))
                        cn.gw_cultivars.append(gw_cv)
        if not form.instructions.data:
            form.instructions.data = None
        if form.instructions.data != cn.instructions:
            edited = True
            if form.instructions.data:
                cn.instructions = form.instructions.data
                flash('Planting instructions for \'{0}\' changed to: {1}'
                      .format(cn.name, cn.instructions))
            else:
                cn.instructions = None
                flash('Planting instructions for \'{0}\' have been cleared.'
                      .format(cn.name))
        if form.parent_cn.data == 0:
            if cn.parent:
                edited = True
                flash('\'{0}\' is no longer a subcategory of any other common '
                      'name.'.format(cn.name))
                cn.parent = None
        else:
            if form.parent_cn.data != cn.id and\
                    (not cn.parent or form.parent_cn.data != cn.parent.id):
                edited = True
                cn.parent = CommonName.query.get(form.parent_cn.data)
                flash('\'{0}\' is now a subcategory of \'{1}\''
                      .format(cn.name, cn.parent.name))
        if form.synonyms.data != cn.list_synonyms_as_string():
            edited = True
            if form.synonyms.data:
                flash('Synonyms for \'{0}\' changed to: {1}'
                      .format(cn.name, form.synonyms.data))
                cn.set_synonyms_from_string_list(form.synonyms.data)
            else:
                cn.clear_synonyms()
                flash('Synonyms for \'{0}\' cleared.'.format(cn.name))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to common name: \'{0}\''.format(cn.name))
            return redirect(url_for('seeds.edit_common_name', cn_id=cn.id))
    form.populate(cn)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name')
    )
    return render_template('seeds/edit_common_name.html',
                           crumbs=crumbs,
                           form=form)


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
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
    form = EditPacketForm()
    if form.validate_on_submit():
        edited = False
        if form.sku.data.strip() != packet.sku:
            pkt2 = Packet.query.filter_by(sku=form.sku.data.strip()).first()
            if pkt2:
                flash(Markup('Error: SKU already in use by {0} in packet {1}. '
                             '<a href="{2}">Click here</a> if you would like '
                             'to edit it.'
                             .format(pkt2.cultivar.fullname,
                                     pkt2.info,
                                     url_for('seeds.edit_packet',
                                             pkt_id=pkt2.id))))
                return redirect(url_for('seeds.edit_packet', pkt_id=packet.id))
            edited = True
            packet.sku = form.sku.data.strip()
        dec_p = USDInt.usd_to_decimal(form.price.data)
        if dec_p != packet.price:
            edited = True
            packet.price = dec_p
        fq = Quantity.for_cmp(form.quantity.data)
        fu = form.units.data.strip()
        if fq != packet.quantity.value or fu != packet.quantity.units:
            edited = True
            oldqty = packet.quantity
            qty = Quantity.query.filter(Quantity.value == fq,
                                        Quantity.units == fu).first()
            if qty:
                packet.quantity = qty
            else:
                if fu != packet.quantity.units:
                    packet.quantity.units = fu
                if fq != packet.quantity.value:
                    packet.quantity.value = fq
            if not oldqty.packets:
                db.session.delete(oldqty)
        if edited:
            db.session.commit()
            flash('Packet changed to: {0}'.format(packet.info))
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to packet: {0}'.format(packet.info))
            return redirect(url_for('seeds.edit_packet', pkt_id=pkt_id))
    form.populate(packet)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series'),
        (url_for('seeds.edit_cultivar'), 'Edit Cultivar'),
        (url_for('seeds.edit_packet'), 'Edit Packet')
    )
    return render_template('seeds/edit_packet.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_cultivar', methods=['GET', 'POST'])
@seeds.route('/edit_cultivar/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_cultivar(cv_id=None):
    """Edit a cultivar stored in the database."""
    if cv_id is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.edit_cultivar'))
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.edit_cultivar'))
    form = EditCultivarForm()
    form.set_selects()
    if form.validate_on_submit():
        edited = False
        form_name = dbify(form.name.data)
        cvs = Cultivar.query.filter_by(_name=form_name).all()
        old_cv_slug = cv.slug
        for cult in cvs:
                if cult.syn_only:
                    flash('Error: \'{0}\' is already being used as a synonym '
                          'for: \'{1}\'. If you wish to rename this cultivar '
                          'to it, you will need to remove it from synonyms '
                          'for \'{1}\' first.'
                          .format(cult.name,
                                  cult.list_syn_parents_as_string()))
                    return redirect(url_for('seeds.edit_cultivar',
                                            cv_id=cv_id))
                elif cult.id != cv.id and cult.name == form_name and\
                        cult.common_name.id == form.common_name.data:
                    flash('Error: There is already another \'{0}\'!'
                          .format(cv.fullname))
                    return redirect(url_for('seeds.edit_cultivar',
                                            cv_id=cv_id))
        if cv.name != form_name:
            edited = True
            flash('Changed cultivar name from \'{0}\' to \'{1}\''.
                  format(cv.name, form_name))
            cv.name = form_name
        new_cv_slug = cv.slug
        old_cn_slug = cv.common_name.slug
        if not cv.common_name or \
                form.common_name.data != cv.common_name.id:
            edited = True
            cn = CommonName.query.get(form.common_name.data)
            flash('Changed common name to \'{0}\' for: {1}'.
                  format(cn.name, cv.fullname))
            cv.common_name = CommonName.query.get(form.common_name.data)
        new_cn_slug = cv.common_name.slug
        if form.botanical_name.data:
            if not cv.botanical_name or\
                    form.botanical_name.data != cv.botanical_name.id:
                edited = True
                cv.botanical_name = BotanicalName.query\
                    .get(form.botanical_name.data)
                flash('Changed botanical name for \'{0}\' to \'{1}\''
                      .format(cv.fullname, cv.botanical_name.name))
        elif cv.botanical_name:
            edited = True
            cv.botanical_name = None
            flash('Botanical name for \'{0}\' has been removed.'
                  .format(cv.fullname))
        cats_removed = []
        for cat in list(cv.categories):
            if cat.id not in form.categories.data:
                edited = True
                flash('Removed category \'{0}\' from: {1}'.
                      format(cat.name, cv.fullname))
                cv.categories.remove(cat)
                cats_removed.append(cat)
        cats_added = []
        for cat_id in form.categories.data:
            if cat_id not in [cat.id for cat in cv.categories]:
                edited = True
                cat = Category.query.get(cat_id)
                flash('Added category \'{0}\' to: {1}'.
                      format(cat.name, cv.fullname))
                cv.categories.append(cat)
                cats_added.append(cat)
        if cats_removed:
            for cat in cats_removed:
                old_path = url_for('seeds.cultivar',
                                   cat_slug=cat.slug,
                                   cn_slug=old_cn_slug,
                                   cv_slug=old_cv_slug)
                urllist = []
                for ct in cv.categories:
                    new_path = url_for('seeds.cultivar',
                                       cat_slug=ct.slug,
                                       cn_slug=new_cn_slug,
                                       cv_slug=new_cv_slug)
                    urllist.append('<a href="{0}" target="_blank">{1}</a>'
                                   .format(url_for('seeds.add_redirect',
                                                   old_path=old_path,
                                                   new_path=new_path,
                                                   status_code=301),
                                           new_path))
                flash(redirect_warning(old_path, list_to_or_string(urllist)))
        if old_cv_slug != new_cv_slug or old_cn_slug != new_cn_slug:
            for cat in cv.categories:
                if cat not in cats_added:
                    old_path = url_for('seeds.cultivar',
                                       cat_slug=cat.slug,
                                       cn_slug=old_cn_slug,
                                       cv_slug=old_cv_slug)
                    new_path = url_for('seeds.cultivar',
                                       cat_slug=cat.slug,
                                       cn_slug=new_cn_slug,
                                       cv_slug=new_cv_slug)
                    flash(redirect_warning(
                        old_path,
                        '<a href="{0} target="_blank">{1}</a>'
                        .format(url_for('seeds.add_redirect',
                                        old_path=old_path,
                                        new_path=new_path,
                                        status_code=301),
                                new_path)
                    ))
        if not form.description.data:
            form.description.data = None
        if form.description.data != cv.description:
            edited = True
            if form.description.data:
                cv.description = form.description.data
                flash('Changed description for \'{0}\' to: {1}'.
                      format(cv.fullname, cv.description))
            else:
                cv.description = None
                flash('Description for \'{0}\' has been cleared.'
                      .format(cv.fullname))
        if cv.gw_common_names:
            for gw_cn in list(cv.gw_common_names):
                if gw_cn.id not in form.gw_common_names.data:
                    edited = True
                    flash('\'{0}\' removed from Grows With for \'{1}\', and '
                          'vice versa.'.format(gw_cn.name, cv.fullname))
                    cv.gw_common_names.remove(gw_cn)
        if form.gw_common_names.data:
            for gw_cn_id in form.gw_common_names.data:
                if gw_cn_id != 0:
                    gw_cn = CommonName.query.get(gw_cn_id)
                    if gw_cn not in cv.gw_common_names:
                        edited = True
                        flash('\'{0}\' added to Grows With for \'{1}\', and '
                              'vice versa.'.format(gw_cn.name, cv.fullname))
                        cv.gw_common_names.append(gw_cn)
        if cv.gw_cultivars:
            for gw_cv in list(cv.gw_cultivars):
                if gw_cv.id not in form.gw_cultivars.data:
                    edited = True
                    flash('\'{0}\' removed from Grows With for \'{1}\', and '
                          'vice versa'.format(gw_cv.fullname, cv.fullname))
                    if cv in gw_cv.gw_cultivars:
                        gw_cv.gw_cultivars.remove(cv)
                    cv.gw_cultivars.remove(gw_cv)
        if form.gw_cultivars.data:
            for gw_cv_id in form.gw_cultivars.data:
                if gw_cv_id != 0 and gw_cv_id != cv.id:
                    gw_cv = Cultivar.query.get(gw_cv_id)
                    if gw_cv not in cv.gw_cultivars:
                        edited = True
                        flash('\'{0}\' added to Grows With for \'{1}\', and '
                              'vice versa.'.format(gw_cv.fullname,
                                                   cv.fullname))
                        cv.gw_cultivars.append(gw_cv)
                        gw_cv.gw_cultivars.append(cv)
        if cv.series:
            if form.series.data != cv.series.id:
                edited = True
                if form.series.data == 0:
                    flash('Series for \'{0}\' has been unset.'
                          .format(cv.fullname))
                    cv.series = None
                else:
                    series = Series.query.get(form.series.data)
                    cv.series = series
                    flash('Series for \'{0}\' has been set to: {1}'
                          .format(cv.fullname, cv.series.name))
        else:
            if form.series.data != 0:
                edited = True
                series = Series.query.get(form.series.data)
                cv.series = series
                flash('Series for \'{0}\' has been set to: {1}'
                      .format(cv.fullname, cv.series.name))
        if form.in_stock.data:
            if not cv.in_stock:
                edited = True
                flash('\'{0}\' is now in stock.'.format(cv.fullname))
                cv.in_stock = True
        else:
            if cv.in_stock:
                edited = True
                flash('\'{0}\' is now out of stock.'.format(cv.fullname))
                cv.in_stock = False
        if form.dropped.data:
            if not cv.dropped:
                edited = True
                flash('\'{0}\' has been dropped.'.format(cv.fullname))
                cv.dropped = True
        else:
            if cv.dropped:
                edited = True
                flash('\'{0}\' is now active/no longer dropped.'.
                      format(cv.fullname))
                cv.dropped = False
        if form.synonyms.data != cv.list_synonyms_as_string():
            edited = True
            cv.set_synonyms_from_string_list(form.synonyms.data)
            flash('Synonyms for \'{0}\' set to: {1}'
                  .format(cv.fullname, cv.list_synonyms_as_string()))
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            img = Image.query.filter_by(filename=thumb_name).first()
            if img and img != cv.thumbnail and img not in cv.images:
                flash('Error: The filename \'{0}\' is already in use by '
                      'another cultivar. Please rename it and try again.'
                      .format(thumb_name))
                db.session.rollback()
                return redirect(url_for('seeds.edit_cultivar', cv_id=cv.id))
            else:
                edited = True
                flash('New thumbnail for \'{0}\' uploaded as: \'{1}\''.
                      format(cv.fullname, thumb_name))
                upload_path = os.path.join(current_app.config.
                                           get('IMAGES_FOLDER'),
                                           thumb_name)
                if cv.thumbnail is not None:
                    # Do not delete or orphan thumbnail, move to images.
                    # Do not directly add cultivar.thumbnail to
                    # cultivar.images, as that will cause a
                    # CircularDependencyError.
                    tb = cv.thumbnail
                    cv.thumbnail = None
                    cv.images.append(tb)
                if img in cv.images:
                    cv.thumbnail = img
                    cv.images.remove(img)
                if not img:
                    cv.thumbnail = Image(filename=thumb_name)
                form.thumbnail.data.save(upload_path)
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to \'{0}\'.'.format(cv.fullname))
            return redirect(url_for('seeds.edit_cultivar', cv_id=cv_id))
    form.populate(cv)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series'),
        (url_for('seeds.edit_cultivar'), 'Edit Cultivar')
    )
    return render_template('seeds/edit_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/edit_series', methods=['GET', 'POST'])
@seeds.route('/edit_series/<series_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_series(series_id=None):
    """Display page for editing a Series from the database."""
    if series_id is None:
        return redirect(url_for('seeds.select_series',
                                dest='seeds.edit_series'))
    series = Series.query.get(series_id)
    if series is None:
        return redirect(url_for('seeds.select_series',
                                dest='seeds.edit_series'))
    form = EditSeriesForm()
    form.set_common_name()
    if form.validate_on_submit():
        edited = False
        if dbify(form.name.data) != series.name:
            s2 = Series.query.filter_by(name=dbify(form.name.data)).first()
            if s2 is not None:
                flash('Error: Another series named \'{0}\' already exists!'.
                      format(s2.name))
                return redirect(url_for('seeds.edit_series',
                                        series_id=series_id))
            else:
                edited = True
                series.name = dbify(form.name.data)
                flash('Series name changed to: {0}'.format(series.name))
        if not form.description.data:
            form.description.data = None
        if form.description.data != series.description:
            edited = True
            if form.description.data:
                flash('Description for series \'{0}\' changed to: {1}'
                      .format(series.fullname, form.description.data))
                series.description = form.description.data
            else:
                flash('Description for series \'{0}\' has been cleared.'
                      .format(series.fullname))
                series.description = None
        if form.common_name.data != series.common_name.id:
            edited = True
            series.common_name = CommonName.query.get(form.common_name.data)
            flash('Common name for \'{0}\' changed to: {1}'.
                  format(series.fullname, series.common_name.name))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to series \'{0}\'.'.
                  format(series.fullname))
    form.populate(series)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_category'), 'Edit Category'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series')
    )
    return render_template('seeds/edit_series.html',
                           crumbs=crumbs,
                           form=form,
                           series=series)


@seeds.route('/flip_dropped/<cv_id>')
@seeds.route('/flip_dropped')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_dropped(cv_id=None):
    """Reverse dropped status of given cultivar."""
    if cv_id is None:
        abort(404)
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    if cv.dropped:
        flash('\'{0}\' has been returned to active status.'.
              format(cv.fullname))
        cv.dropped = False
    else:
        flash('\'{0}\' has been dropped.'.
              format(cv.fullname))
        cv.dropped = True
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))


@seeds.route('/flip_in_stock/<cv_id>')
@seeds.route('/flip_in_stock')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_in_stock(cv_id=None):
    if cv_id is None:
        abort(404)
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    if cv.in_stock:
        flash('\'{0}\' is now out of stock.'.format(cv.fullname))
        cv.in_stock = False
    else:
        flash('\'{0}\' is now in stock.'.format(cv.fullname))
        cv.in_stock = True
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
    pending = Pending(current_app.config.get('PENDING_FILE'))
    lc = LastCommit()
    if pending.exists():
        pending.load()
    return render_template('seeds/manage.html', pending=pending, lc=lc)


@seeds.route('/remove_botanical_name', methods=['GET', 'POST'])
@seeds.route('/remove_botanical_name/<bn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_botanical_name(bn_id=None):
    """Remove a botanical name from the database."""
    if bn_id is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    bn = BotanicalName.query.get(bn_id)
    if bn is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    form = RemoveBotanicalNameForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            if bn.synonyms:
                flash('Synonyms for \'{0}\' cleared and orphaned synonyms '
                      'have been deleted.'.format(bn.name))
                bn.clear_synonyms()
            flash('The botanical name \'{1}\' has been removed from '
                  'the database.'.format(bn.id, bn.name))
            db.session.delete(bn)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if '
                  'you want to remove this botanical name.')
            return redirect(url_for('seeds.remove_botanical_name',
                                    bn_id=bn_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name')
    )
    return render_template('seeds/remove_botanical_name.html',
                           bn=bn,
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_category', methods=['GET', 'POST'])
@seeds.route('/remove_category/<cat_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_category(cat_id=None):
    """Remove a category from the database."""
    if cat_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    category = Category.query.get(cat_id)
    if category is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    form = RemoveCategoryForm()
    form.set_move_to(cat_id)
    if form.validate_on_submit():
        if form.verify_removal.data:
            old_cat_slug = category.slug
            cat2 = Category.query.get(form.move_to.data)
            new_cat_slug = cat2.slug
            flash('Common names and seeds formerly associated with \'{0}\' '
                  'are now associated with \'{1}\'.'
                  .format(category.name, cat2.name))
            old_path = url_for('seeds.category',
                               cat_slug=old_cat_slug)
            new_path = url_for('seeds.category',
                               cat_slug=new_cat_slug)
            flash(redirect_warning(
                old_path,
                '<a href="{0}">{1}</a>'
                .format(url_for('seeds.add_redirect',
                                old_path=old_path,
                                new_path=new_path,
                                status_code=301),
                        new_path)
            ))
            for cn in category.common_names:
                if cn not in cat2.common_names:
                    cat2.common_names.append(cn)
                old_path = url_for('seeds.common_name',
                                   cat_slug=old_cat_slug,
                                   cn_slug=cn.slug)
                new_path = url_for('seeds.common_name',
                                   cat_slug=new_cat_slug,
                                   cn_slug=cn.slug)
                flash(redirect_warning(
                    old_path,
                    '<a href="{0}" target="_blank">{1}</a>'
                    .format(url_for('seeds.add_redirect',
                                    old_path=old_path,
                                    new_path=new_path,
                                    status_code=302),
                            new_path)
                ))
            for cv in category.cultivars:
                if cv not in cat2.cultivars:
                    cat2.cultivars.append(cv)
                    old_path = url_for('seeds.cultivar',
                                       cat_slug=old_cat_slug,
                                       cn_slug=cv.common_name.slug,
                                       cv_slug=cv.slug)
                    new_path = url_for('seeds.cultivar',
                                       cat_slug=new_cat_slug,
                                       cn_slug=cv.common_name.slug,
                                       cv_slug=cv.slug)
                    flash(redirect_warning(
                        old_path,
                        '<a href="{0}" target="_blank">{1}</a>'
                        .format(url_for('seeds.add_redirect',
                                        old_path=old_path,
                                        new_path=new_path,
                                        status_code=301),
                                new_path)
                    ))
            flash('The category \'{1}\' has been removed from the database.'.
                  format(category.id, category.name))
            db.session.delete(category)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\''
                  ' if you want to remove this category.')
            return redirect(url_for('seeds.remove_category',
                                    cat_id=cat_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category')
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
    cn = CommonName.query.get(cn_id)
    if cn is None:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.remove_common_name'))
    form = RemoveCommonNameForm()
    form.set_move_to(cn_id)
    if form.validate_on_submit():
        if form.verify_removal.data:
            old_cn_slug = cn.slug
            if cn.synonyms:
                cn.clear_synonyms()
                flash('Synonyms for \'{0}\' cleared, and orphaned synonyms '
                      'have been deleted.'.format(cn.name))
            cn2 = CommonName.query.get(form.move_to.data)
            new_cn_slug = cn2.slug
            for cat in cn.categories:
                old_path = url_for('seeds.common_name',
                                   cat_slug=cat.slug,
                                   cn_slug=old_cn_slug)
                urllist = []
                for cat2 in cn2.categories:
                    new_path = url_for('seeds.common_name',
                                       cat_slug=cat2.slug,
                                       cn_slug=new_cn_slug)
                    urllist.append('<a href="{0}" target="_blank">{1}</a>'
                                   .format(url_for('seeds.add_redirect',
                                                   old_path=old_path,
                                                   new_path=new_path,
                                                   status_code=301),
                                           new_path))
                flash(redirect_warning(old_path, list_to_or_string(urllist)))
            flash('Botanical names and seeds formerly associated with \'{0}\' '
                  'are now associated with \'{1}\'.'.format(cn.name, cn2.name))
            for bn in cn.botanical_names:
                if bn not in cn2.botanical_names:
                    cn2.botanical_names.append(bn)
            for cv in list(cn.cultivars):
                if cv not in cn2.cultivars:
                    new_fullname = '{0} {1}'.format(cv.name, cn2.name)
                    fns = [cv.fullname for cv in cn2.cultivars]
                    if new_fullname in fns:
                        ed_url = url_for('seeds.edit_cultivar', cv_id=cv.id)
                        rem_url = url_for('seeds.remove_cultivar', cv_id=cv.id)
                        flash(
                            Markup('Warning: \'{0}\' could not be changed to '
                                   '\'{1}\' because \'{1}\' already exists! '
                                   '<a href="{2}">Click here</a> to edit the '
                                   'orphaned cultivar, or <a href="{3}">click '
                                   'here</a> to remove it from the database.'
                                   .format(cv.fullname,
                                           new_fullname,
                                           ed_url,
                                           rem_url)))
                    else:
                        cn2.cultivars.append(cv)
                        for cat in cn.categories:
                            old_path = url_for('seeds.cultivar',
                                               cat_slug=cat.slug,
                                               cn_slug=old_cn_slug,
                                               cv_slug=cv.slug)
                            urllist = []
                            for cat2 in cn2.categories:
                                new_path = url_for('seeds.cultivar',
                                                   cat_slug=cat2.slug,
                                                   cn_slug=new_cn_slug,
                                                   cv_slug=cv.slug)
                                urllist.append(
                                    '<a href="{0}" target="_blank">{1}</a>'
                                    .format(url_for('seeds.add_redirect',
                                                    old_path=old_path,
                                                    new_path=new_path,
                                                    status_code=301),
                                            new_path)
                                )
                            flash(redirect_warning(old_path,
                                                   list_to_or_string(urllist)))
            flash('The common name \'{0}\' has been removed from the '
                  'database.'.format(cn.name))
            db.session.delete(cn)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if '
                  'you want to remove this common name.')
            return redirect(url_for('seeds.remove_common_name', cn_id=cn_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name')
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
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.remove_packet'))
    form = RemovePacketForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Packet {0} has been removed from the database.'
                  .format(packet.info))
            oldqty = packet.quantity
            db.session.delete(packet)
            if not oldqty.packets:
                db.session.delete(oldqty)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\' if you '
                  'want to remove this packet.')
            return redirect(url_for('seeds.remove_packet', pkt_id=pkt_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name'),
        (url_for('seeds.remove_series'), 'Remove Series'),
        (url_for('seeds.remove_cultivar'), 'Remove Cultivar'),
        (url_for('seeds.remove_packet'), 'Remove Packet')
    )
    return render_template('seeds/remove_packet.html',
                           crumbs=crumbs,
                           form=form,
                           packet=packet)


@seeds.route('/remove_cultivar', methods=['GET', 'POST'])
@seeds.route('/remove_cultivar/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_cultivar(cv_id=None):
    if cv_id is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.remove_cultivar'))
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.remove_cultivar'))
    form = RemoveCultivarForm()
    if form.validate_on_submit():
        if not form.verify_removal.data:
            flash('No changes made. Check the box labeled \'Yes\' if you '
                  'would like to remove this cultivar.')
            return redirect(url_for('seeds.remove_cultivar', cv_id=cv_id))
        if form.delete_images:
            rollback = False
            if cv.images:
                for image in cv.images:
                    try:
                        image.delete_file()
                        flash('Image file \'{0}\' deleted.'.
                              format(image.filename))
                        db.session.delete(image)
                    except OSError as e:
                        if e.errno == 2:    # No such file or directory
                            db.session.delete(image)
                        else:
                            rollback = True
                            flash('Error: Attempting to delete image \'{0}\' '
                                  'raised an exception: {1}'
                                  .format(image.filename, e))
            if cv.thumbnail:
                try:
                    cv.thumbnail.delete_file()
                    flash('Thumbnail image \'{0}\' has been deleted.'.
                          format(cv.thumbnail.filename))
                    db.session.delete(cv.thumbnail)
                except OSError as e:
                    if e.errno == 2:    # No such file or directory
                        db.session.delete(cv.thumbnail)
                    else:
                        rollback = True
                        flash('Error: Attempting to delete thumbnail \'{0}\' '
                              'raised an exception: {1}'
                              .format(cv.thumbnail.filename, e))
        if rollback:
            flash('Error: Cultivar could not be deleted due to problems '
                  'deleting associated images.')
            db.session.rollback()
            return redirect(url_for('seeds.remove_cultivar', cv_id=cv_id))
        else:
            if cv.synonyms:
                flash('Synonyms for \'{0}\' cleared, and orphaned synonyms '
                      'have been deleted.'.format(cv.fullname))
                cv.clear_synonyms()
            flash('The cultivar \'{0}\' has been deleted. Forever. I hope '
                  'you\'re happy with yourself.'.format(cv.fullname))
            for cat in cv.categories:
                old_path = url_for('seeds.cultivar',
                                   cat_slug=cat.slug,
                                   cn_slug=cv.common_name.slug,
                                   cv_slug=cv.slug)
                flash(Markup(
                    'Warning: the path \'{0}\' is no longer valid. <a '
                    'href="{1}" target="_blank">Click here</a> if you wish to'
                    'add a redirect for it.'
                    .format(old_path,
                            url_for('seeds.add_redirect',
                                    old_path=old_path,
                                    status_code=301))
                ))
            db.session.delete(cv)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
    form.delete_images.data = True
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_series'), 'Remove Series'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name'),
        (url_for('seeds.remove_cultivar'), 'Remove Cultivar')
    )
    return render_template('seeds/remove_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/remove_series', methods=['GET', 'POST'])
@seeds.route('/remove_series/<series_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_series(series_id=None):
    """Display page for removing series from database."""
    if series_id is None:
        return redirect(url_for('seeds.select_series',
                                dest='seeds.remove_series'))
    series = Series.query.get(series_id)
    if series is None:
        return redirect(url_for('seeds.select_series',
                                dest='seed.remove_series'))
    form = RemoveSeriesForm()
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('The series \'{0}\' has been removed from the database.'.
                  format(series.fullname))
            db.session.delete(series)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labled \'Yes\' if you would'
                  ' like to remove this series.')
            return redirect(url_for('seeds.remove_series',
                                    series_id=series_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_category'), 'Remove Category'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name'),
        (url_for('seeds.remove_series'), 'Remove Series')
    )
    return render_template('seeds/remove_series.html',
                           crumbs=crumbs,
                           form=form,
                           series=series)


@seeds.route('/<cat_slug>/<cn_slug>/<cv_slug>')
def cultivar(cat_slug=None, cn_slug=None, cv_slug=None):
    """Display a page for a given cultivar."""
    cat = Category.query.filter_by(slug=cat_slug).first()
    cn = CommonName.query.filter_by(slug=cn_slug).first()
    cv = Cultivar.query.filter(Cultivar.slug == cv_slug,
                               Cultivar.common_name == cn).first()
    if (cat is not None and cn is not None and cv is not None) and \
            (cat in cv.categories and cn is cv.common_name):
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.category', cat_slug=cat_slug), cat.header),
            (url_for('seeds.common_name', cat_slug=cat_slug, cn_slug=cn_slug),
             cn.name),
            (url_for('seeds.cultivar',
                     cat_slug=cat_slug,
                     cn_slug=cn_slug,
                     cv_slug=cv_slug),
             cv.name)
        )
        return render_template('seeds/cultivar.html',
                               cat_slug=cat_slug,
                               cn_slug=cn_slug,
                               crumbs=crumbs,
                               cultivar=cv)
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
    form.set_botanical_name()
    if form.validate_on_submit():
        return redirect(url_for(dest, bn_id=form.botanical_name.data))
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
    form.set_category()
    if form.validate_on_submit():
        return redirect(url_for(dest, cat_id=form.category.data))
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
    form.set_common_name()
    if form.validate_on_submit():
        return redirect(url_for(dest, cn_id=form.common_name.data))
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
    form.set_packet()
    if form.validate_on_submit():
        return redirect(url_for(dest, pkt_id=form.packet.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_packet', dest=dest), 'Select Packet')
    )
    return render_template('seeds/select_packet.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_cultivar', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_cultivar():
    """Select a cultivar to load on another page.

    Request Args:
        dest (str): The route to redirect to once cultivar is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCultivarForm()
    form.set_cultivar()
    if form.validate_on_submit():
        return redirect(url_for(dest, cv_id=form.cultivar.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_cultivar', dest=dest), 'Select Cultivar')
    )
    return render_template('seeds/select_cultivar.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_series', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_series():
    """Select a series to load on another page.

    Request Args:
        dest (str): The route to redirect to once series is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectSeriesForm()
    form.set_series()
    if form.validate_on_submit():
        return redirect(url_for(dest, series_id=form.series.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_series', dest=dest), 'Select Series')
    )
    return render_template('seeds/select_series.html',
                           crumbs=crumbs,
                           form=form)

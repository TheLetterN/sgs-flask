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


import datetime
import os
from copy import deepcopy
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
from app import db, Permission
from app.breadcrumbs import Crumbler
from app.decorators import permission_required
from app.pending import Pending
from app.redirects import Redirect, RedirectsFile
from . import seeds
from ..lastcommit import LastCommit
from .models import (
    BotanicalName,
    dbify,
    Index,
    CommonName,
    Cultivar,
    Image,
    Packet,
    Quantity,
    Series,
    USDollar
)
from .forms import (
    AddBotanicalNameForm,
    AddIndexForm,
    AddCommonNameForm,
    AddPacketForm,
    AddRedirectForm,
    AddCultivarForm,
    AddSeriesForm,
    EditBotanicalNameForm,
    EditIndexForm,
    EditCommonNameForm,
    EditPacketForm,
    EditCultivarForm,
    EditSeriesForm,
    RemoveBotanicalNameForm,
    RemoveIndexForm,
    RemoveCommonNameForm,
    RemovePacketForm,
    RemoveSeriesForm,
    RemoveCultivarForm,
    SelectBotanicalNameForm,
    SelectIndexForm,
    SelectCommonNameForm,
    SelectPacketForm,
    SelectCultivarForm,
    SelectSeriesForm
)


cblr = Crumbler('seeds')


ADD_ROUTES = (
    ('manage', 'Manage Seeds'),
    'add_index',
    'add_common_name',
    'add_botanical_name',
    'add_series',
    'add_cultivar',
    'add_packet'
)


EDIT_ROUTES = (
    ('manage', 'Manage Seeds'),
    'edit_index',
    'edit_common_name',
    'edit_botanical_name',
    'edit_series',
    'edit_cultivar',
    'edit_packet'
)


def make_breadcrumbs(*args):
    """Create a 'trail of breadcrumbs' to include in pages.

    Args:
        args (tuple): A tuple containing tuples in the format (route, title)

    Returns:
        list: A list containing
    """
    if all(isinstance(arg, tuple) and len(arg) == 2 for arg in args):
        trail = list()
        for arg in args:
            trail.append('<a href="{0}">{1}</a>'.
                         format(arg[0], arg[1]))
        return trail
    else:
        raise ValueError('Could not parse arguments. Please make sure your '
                         'arguments are tuples formatted (route, page title)!')


def flash_all(messages, category='message'):
    if category == 'message':
        if len(messages) > 2:
            message = messages[0] + '\n<ul class="flashed_list">\n'
            for msg in messages[1:-1]:
                message += '    <li>' + msg + '</li>\n'
            message += '</ul>\n' + messages[-1]
            flash(message, category)
        else:
            for message in messages:
                flash(message, category)
    else:
        for message in messages:
            flash(message, category)


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
        old_path: The path that has been rendered invalid.
        links: A link or links to forms to add possible redirects.

    Returns:
        Markup: A string containing a warning that a redirect should be added.
    """
    return ('Warning: the path \'{0}\' is no longer valid. You may wish to '
            'redirect it to {1}.'.format(old_path, links))


def redirect_index_warnings(index,
                            old_idx_slug=None,
                            new_idx_slug=None):
    """Generate redirect warnings for a changed `Index`.

    Args:
        old_idx_slug: Optional `Index.slug` to redirect from.
        new_idx_slug: Optional `Index.slug` to redirect to.

    Raises:
        ValueError: If no slugs were passed.

    Returns:
        list: A list of redirect warnings generated by this function.
    """
    if not old_idx_slug and new_idx_slug:
        raise ValueError('At least one slug must be passed!')

    if not old_idx_slug:
        old_idx_slug = index.slug

    if not new_idx_slug:
        new_idx_slug = index.slug

    old_path = url_for('seeds.index_page', idx_slug=old_idx_slug)
    new_path = url_for('seeds.index_page', idx_slug=new_idx_slug)

    warnings = []
    if index.common_names:
        for cn in index.common_names:
            try:
                warnings += redirect_common_name_warnings(
                    common_name=cn,
                    old_idx_slug=old_idx_slug,
                    new_idx_slug=new_idx_slug
                )
            except ValueError:
                pass
    warnings.append(redirect_warning(
        old_path,
        '<a href="{0}" target="_blank">{1}</a>'
        .format(url_for('seeds.add_redirect',
                        old_path=old_path,
                        new_path=new_path,
                        status_code=301),
                new_path)
    ))
    return warnings


def redirect_common_name_warnings(common_name,
                                  old_idx_slug=None,
                                  old_cn_slug=None,
                                  new_idx_slug=None,
                                  new_cn_slug=None):
    """Generate redirect warnings for a changed `CommonName`.

    All slugs are optional, and any not passed will be set to the relevant
    slug belonging to `common_name`. At least one slug should be passed,
    though, otherwise there is no need to make a redirect.

    Args:
        old_idx_slug: Optional `Index.slug` to redirect from.
        old_cn_slug: Optional `CommonName.slug` to redirect from.
        new_idx_slug: Optional `Index.slug` to redirect to.
        new_cn_slug: Optional `CommonName.slug` to redirect to.

    Raises:
        ValueError: If no slugs were passed.

    Returns:
        list: A list of redirect warnings generated by this function.
    """
    if (not old_idx_slug and not old_cn_slug and
            not new_idx_slug and not new_cn_slug):
        raise ValueError('At least one slug must be passed!')

    if not old_idx_slug:
        old_idx_slug = common_name.index.slug
    if not old_cn_slug:
        old_cn_slug = common_name.slug

    if not new_idx_slug:
        new_idx_slug = common_name.index.slug
    if not new_cn_slug:
        new_cn_slug = common_name.slug

    old_path = url_for('seeds.common_name',
                       idx_slug=old_idx_slug,
                       cn_slug=old_cn_slug)
    new_path = url_for('seeds.common_name',
                       idx_slug=new_idx_slug,
                       cn_slug=new_cn_slug)

    warnings = []
    if common_name.cultivars:
        for cv in common_name.cultivars:
            try:
                warnings.append(redirect_cultivar_warning(
                    cultivar=cv,
                    old_idx_slug=old_idx_slug,
                    old_cn_slug=old_cn_slug,
                    new_idx_slug=new_idx_slug,
                    new_cn_slug=new_cn_slug
                ))
            except ValueError:
                pass
    warnings.append(redirect_warning(
        old_path,
        '<a href="{0}" target="_blank">{1}</a>'
        .format(url_for('seeds.add_redirect',
                        old_path=old_path,
                        new_path=new_path,
                        status_code=301),
                new_path)
    ))
    return warnings


def redirect_cultivar_warning(cultivar,
                              old_idx_slug=None,
                              old_cn_slug=None,
                              old_cv_slug=None,
                              new_idx_slug=None,
                              new_cn_slug=None,
                              new_cv_slug=None):
    """Generate a redirect warning for a cultivar.

    All slugs are optional, and any not passed will be set to the relevant
    slug belinging to `cultivar`. At least one slug should be passed, though,
    otherwise there is no need to make a redirect.

    Args:
        old_idx_slug: Optional `Index.slug` to redirect from.
        old_cn_slug: Optional `CommonName.slug` to redirect from.
        old_cv_slug: Optional `Cultivar.slug` to redirect from.
        new_idx_slug: Optional `Index.slug` to redirect to.
        new_cn_slug: Optional `CommonName.slug` to redirect to.
        new_cv_slug: Optional `Cultivar.slug` to redirect to.

    Raises:
        ValueError: If no slugs were passed.

    Returns:
        str: The redirect warning message.
    """
    if (not old_idx_slug and not old_cn_slug and not old_cv_slug and
            not new_idx_slug and not new_cn_slug and not new_cv_slug):
        raise ValueError('At least one slug must be passed!')

    if not old_idx_slug:
        old_idx_slug = cultivar.common_name.index.slug
    if not old_cn_slug:
        old_cn_slug = cultivar.common_name.slug
    if not old_cv_slug:
        old_cv_slug = cultivar.slug

    if not new_idx_slug:
        new_idx_slug = cultivar.common_name.index.slug
    if not new_cn_slug:
        new_cn_slug = cultivar.common_name.slug
    if not new_cv_slug:
        new_cv_slug = cultivar.slug

    old_path = url_for('seeds.cultivar',
                       idx_slug=old_idx_slug,
                       cn_slug=old_cn_slug,
                       cv_slug=old_cv_slug)
    new_path = url_for('seeds.cultivar',
                       idx_slug=new_idx_slug,
                       cn_slug=new_cn_slug,
                       cv_slug=new_cv_slug)
    return redirect_warning(
        old_path,
        '<a href="{0}" target="_blank">{1}</a>'
        .format(url_for('seeds.add_redirect',
                        old_path=old_path,
                        new_path=new_path,
                        status_code=301),
                new_path)
    )


@seeds.route('/add_index', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_index():
    """Handle web interface for adding Index objects to the database."""
    form = AddIndexForm()
    if form.validate_on_submit():
        messages = []
        index = Index(name=form.name.data)
        db.session.add(index)
        messages.append('Creating new index \'{0}\':'
                        .format(index.name))
        if form.description.data:
            index.description = form.description.data
            messages.append('Description set to: \'{0}\''
                            .format(index.description))
        db.session.commit()
        messages.append('New index \'{0}\' added to the database.'
                        .format(index.name))
        flash_all(messages)
        return redirect(url_for('seeds.add_common_name', idx_id=index.id))
    crumbs = cblr.crumble_route_group('add_index', ADD_ROUTES)
    return render_template('seeds/add_index.html', crumbs=crumbs, form=form)


@seeds.route('/add_common_name', methods=['GET', 'POST'])
@seeds.route('/add_common_name/<idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_common_name(idx_id=None):
    """Handle web interface for adding CommonName objects to the database."""
    idx = Index.query.get(idx_id) if idx_id else None
    if not idx:
        return redirect(url_for('seeds.select_index',
                                dest='seeds.add_common_name'))

    form = AddCommonNameForm(index=idx)
    if form.validate_on_submit():
        messages = []
        cn = CommonName(name=form.name.data, index=idx)
        db.session.add(cn)
        messages.append('Creating new common name \'{0}\' and adding it to '
                        'index \'{1}\':'.format(cn.name, idx.name))
        if form.parent_cn.data:
            cn.parent = CommonName.query.get(form.parent_cn.data)
            messages.append('\'{0}\' is a subcategory of \'{1}\''
                            .format(cn.name, cn.parent.name))
        if form.description.data:
            cn.description = form.description.data
            messages.append('Description set to: \'{0}\''
                            .format(cn.description))
        if form.instructions.data:
            cn.instructions = form.instructions.data
            messages.append('Planting instructions set to: \'{0}\''
                            .format(cn.instructions))
        if form.synonyms.data:
            cn.synonyms_string = form.synonyms.data
            messages.append('Synonyms set to: \'{0}\'.'
                            .format(cn.synonyms_string))
        db.session.commit()
        messages.append('New common name \'{0}\' added to the database.'
                        .format(cn.name))
        flash_all(messages)
        return redirect(url_for('seeds.{0}'.format(form.next_page.data),
                                cn_id=cn.id))
    crumbs = cblr.crumble_route_group('add_common_name', ADD_ROUTES)
    return render_template('seeds/add_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_botanical_name', methods=['GET', 'POST'])
@seeds.route('/add_botanical_name/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_botanical_name(cn_id=None):
    """Handle web interface for adding BotanicalName objects to database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.add_botanical_name'))

    form = AddBotanicalNameForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        bn = BotanicalName(name=form.name.data.strip())
        db.session.add(bn)
        bn.common_names.append(cn)
        messages.append('Creating botanical name \'{0}\' for common name '
                        '\'{1}\':'.format(bn.name, cn.name))
        if form.synonyms.data:
            bn.synonyms_string = form.synonyms.data
            messages.append('Synonyms set to: \'{0}\'.'
                            .format(bn.synonyms_string))
        db.session.commit()
        messages.append('New botanical name \'{0}\' added to the database.'
                        .format(bn.name))
        flash_all(messages)
        return redirect(url_for('seeds.{0}'.format(form.next_page.data),
                        cn_id=cn.id))

    crumbs = cblr.crumble_route_group('add_botanical_name', ADD_ROUTES)
    return render_template('seeds/add_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_series', methods=['GET', 'POST'])
@seeds.route('/add_series/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_series(cn_id=None):
    """Add a series to the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.add_series'))

    form = AddSeriesForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        series = Series(name=form.name.data, common_name=cn)
        db.session.add(series)
        messages.append('Creating series \'{0}\' for common name \'{1}\':'
                        .format(series.name, cn.name))
        if form.description.data:
            series.description = form.description.data
            messages.append('Description set to: \'{0}\'.'
                            .format(series.description))
        if form.position.data == Series.AFTER_CULTIVAR:
            messages.append('\'{0}\' will be used after the cultivar\'s '
                            'individual name in the full names of any '
                            'cultivars in the series.'.format(series.name))
        else:
            messages.append('\'{0}\' will be used before the cultivar\'s '
                            'individual name in the full names of any '
                            'cultivars in the series.'.format(series.name))
        series.position = form.position.data
        db.session.commit()
        messages.append('New series \'{0}\' added to the database.'
                        .format(series.fullname))
        flash_all(messages)
        return redirect(url_for('seeds.add_cultivar', cn_id=cn.id))
    crumbs = cblr.crumble_route_group('add_series', ADD_ROUTES)
    return render_template('seeds/add_series.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_cultivar', methods=['GET', 'POST'])
@seeds.route('/add_cultivar/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_cultivar(cn_id=None):
    """Add a cultivar to the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.add_cultivar'))

    form = AddCultivarForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        cv = Cultivar(name=form.name.data, common_name=cn)
        db.session.add(cv)
        messages.append('Creating cultivar with short name \'{0}\' for common '
                        'name \'{1}\':'.format(cv.name, cn.name))
        if form.botanical_name.data:
            cv.botanical_name = BotanicalName.query\
                .get(form.botanical_name.data)
            messages.append('Botanical name set to: \'{0}\'.'
                            .format(cv.botanical_name.name))
        if form.series.data:
            cv.series = Series.query.get(form.series.data)
            messages.append('Series set to: \'{0}\'.'.format(cv.series.name))
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                       thumb_name)
            cv.thumbnail = Image(filename=thumb_name)
            form.thumbnail.data.save(upload_path)
            messages.append('Thumbnail uploaded as: {0}'.format(thumb_name))
        if form.description.data:
            cv.description = form.description.data
            messages.append('Description set to: {0}'.format(cv.description))
        if form.synonyms.data:
            cv.synonyms_string = form.synonyms.data
            messages.append('Synonyms set to: \'{0}\'.'
                            .format(cv.synonyms_string))
        if form.new_until.data and form.new_until.data > datetime.date.today():
            cv.new_until = form.new_until.data
            messages.append('\'{0}\' will be marked as new until: {1}'
                            .format(cv.fullname,
                                    cv.new_until.strftime('%m/%d/%Y')))
        if form.in_stock.data:
            cv.in_stock = True
            messages.append('\'{0}\' is in stock.'.format(cv.fullname))
        else:
            cv.in_stock = False
            messages.append('\'{0}\' is not in stock.'.format(cv.fullname))
        if form.active.data:
            cv.active = True
            messages.append('\'{0}\' is currently active.'.format(cv.fullname))
        else:
            cv.active = False
            messages.append('\'{0}\' is currently inactive.'
                            .format(cv.fullname))
        if form.visible.data:
            cv.invisible = False
            messages.append('\'{0}\' will be visible in auto-generated pages.'
                            .format(cv.fullname))
        else:
            cv.invisible = True
            messages.append('\'{0}\' will not be visible in auto-generated '
                            'pages, but it can still be used in custom pages.'
                            .format(cv.fullname))
        db.session.commit()
        messages.append('New cultivar \'{0}\' added to the database.'
                        .format(cv.fullname))
        flash_all(messages)
        return redirect(url_for('seeds.add_packet', cv_id=cv.id))
    crumbs = cblr.crumble_route_group('add_cultivar', ADD_ROUTES)
    return render_template('seeds/add_cultivar.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_packet', methods=['GET', 'POST'])
@seeds.route('/add_packet/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_packet(cv_id=None):
    """Add a packet to the database."""
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if not cv:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.add_packet'))
    form = AddPacketForm(cultivar=cv)
    if form.validate_on_submit():
        messages = []
        packet = Packet(sku=form.sku.data.strip(), cultivar=cv)
        db.session.add(packet)
        messages.append('Creating packet with SKU #{0} for cultivar \'{1}\':'
                        .format(packet.sku, cv.fullname))
        packet.price = form.price.data
        messages.append('Price set to: ${0}.'.format(packet.price))
        fu = form.units.data.strip()
        fq = form.quantity.data
        qty = Quantity.query.filter(
            Quantity.value == fq,
            Quantity.units == fu,
            Quantity.is_decimal == Quantity.dec_check(fq)
        ).one_or_none()
        if qty:
            packet.quantity = qty
        else:
            packet.quantity = Quantity(value=fq, units=fu)
        messages.append('Quantity set to: \'{0} {1}\'.'
                        .format(packet.quantity.value, packet.quantity.units))
        db.session.commit()
        messages.append('New packet with SKU #{0} added to the database.'
                        .format(packet.sku))
        flash_all(messages)
        if form.again.data:
            return redirect(url_for('seeds.add_packet', cv_id=cv_id))
        else:
            return redirect(url_for('seeds.manage'))
    crumbs = cblr.crumble_route_group('add_packet', ADD_ROUTES)
    return render_template('seeds/add_packet.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_redirect', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_redirect():
    """Add a redirect from an old path to a new one."""
    op = request.args.get('old_path')
    np = request.args.get('new_path')
    sc = request.args.get('status_code')
    form = AddRedirectForm(old_path=op, new_path=np, status_code=sc)
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
    crumbs = (cblr.crumble('manage', 'Manage Seeds'),
              cblr.crumble('add_redirect'))
    return render_template('seeds/add_redirect.html', crumbs=crumbs, form=form)


@seeds.route('/edit_index', methods=['GET', 'POST'])
@seeds.route('/edit_index/<idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_index(idx_id=None):
    index = Index.query.get(idx_id) if idx_id else None
    if index is None:
        return redirect(url_for('seeds.select_index',
                        dest='seeds.edit_index'))

    form = EditIndexForm(obj=index)
    if form.validate_on_submit():
        edited = False
        messages = []
        old_index = None
        messages.append('Editing index \'{0}\':'.format(index.name))
        if form.name.data != index.name:
            edited = True
            old_index = deepcopy(index)
            index.name = form.name.data
            messages.append('Name changed to: \'{0}\'.'.format(index.name))
        if form.description.data != index.description:
            edited = True
            if form.description.data:
                index.description = form.description.data
                messages.append('Description set to: \'{0}\'.'
                                .format(index.description))
            else:
                index.description = None
                messages.append('Description cleared.')
        if edited:
            db.session.commit()
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(index.name))
            flash_all(messages)
            if old_index.slug != index.slug:
                warnings = None
                try:
                    warnings = redirect_index_warnings(
                        index,
                        old_idx_slug=old_index.slug,
                        new_idx_slug=index.slug
                    )
                except ValueError:
                    pass
                if warnings:
                    flash_all(warnings, 'warning')
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made.'
                            .format(index.name))
            flash_all(messages)
            return redirect(url_for('seeds.edit_index', idx_id=idx_id))
    crumbs = cblr.crumble_route_group('edit_index', EDIT_ROUTES)
    return render_template('seeds/edit_index.html',
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
    form.cn_id = cn.id
    if form.validate_on_submit():
        edited = False
        form.name.data = dbify(form.name.data)
        old_cn_slug = cn.slug
        if form.name.data != cn.name:
            edited = True
            flash('Common name \'{0}\' changed to \'{1}\'.'.
                  format(cn.name, form.name.data))
            cn.name = form.name.data
        old_idx = cn.index
        if form.index.data != cn.index.id:
            cn.index = Index.query.get(form.index.data)
            flash('Index for \'{0}\' and all of its cultivars has been '
                  'changed to: {1}'.format(cn.name, cn.index.name))
        if cn.generate_slug() != old_cn_slug or old_idx is not cn.index:
            old_path = url_for('seeds.common_name',
                               idx_slug=old_idx.slug,
                               cn_slug=old_cn_slug)
            new_path = url_for('seeds.common_name',
                               idx_slug=cn.index.slug,
                               cn_slug=cn.generate_slug())
            flash(redirect_warning(old_path,
                                   '<a href="{0}" target="_blank">{1}</a>'
                                   .format(url_for('seeds.add_redirect',
                                                   old_path=old_path,
                                                   new_path=new_path,
                                                   status_code=301),
                                           new_path)))
            for cv in cn.cultivars:
                if old_idx is not cn.index:
                    cv.common_name.index = cn.index
                old_path = url_for('seeds.cultivar',
                                   idx_slug=old_idx.slug,
                                   cn_slug=old_cn_slug,
                                   cv_slug=cv.slug)
                new_path = url_for('seeds.cultivar',
                                   idx_slug=cn.index.slug,
                                   cn_slug=cn.generate_slug(),
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
        if form.synonyms.data != cn.synonyms_string:
            edited = True
            if form.synonyms.data:
                flash('Synonyms for \'{0}\' changed to: {1}'
                      .format(cn.name, form.synonyms.data))
                cn.synonyms_string = form.synonyms.data
            else:
                cn.synonyms_string = None
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
        (url_for('seeds.edit_index'), 'Edit Index'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name')
    )
    return render_template('seeds/edit_common_name.html',
                           crumbs=crumbs,
                           form=form)


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
    form.set_common_names()
    form.bn = bn
    if form.validate_on_submit():
        edited = False
        form.name.data = form.name.data.strip()
        if form.name.data != bn.name:
                edited = True
                flash('Botanical name \'{0}\' changed to \'{1}\'.'.
                      format(bn.name, form.name.data))
                bn.name = form.name.data
        for cn in list(bn.common_names):
            if cn.id not in form.common_names.data:
                edited = True
                flash('Removed common name \'{0}\' from \'{1}\'.'
                      .format(cn.name, bn.name))
                bn.common_names.remove(cn)
        cnids = [cona.id for cona in bn.common_names]
        for cnid in form.common_names.data:
            if cnid not in cnids:
                edited = True
                cn = CommonName.query.get(cnid)
                flash('Added common name \'{0}\' to \'{1}\'.'
                      .format(cn.name, bn.name))
                bn.common_names.append(cn)
        if form.synonyms.data != bn.synonyms_string:
            edited = True
            if form.synonyms.data:
                bn.synonyms_string = form.synonyms.data
                flash('Synonyms for \'{0}\' set to: {1}'
                      .format(bn.name, bn.synonyms_string))
            else:
                bn.synonyms_string = None
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
        (url_for('seeds.edit_index'), 'Edit Index'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'),
         'Edit Botanical Name')
    )
    return render_template('/seeds/edit_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


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
    form.sr_id = series.id
    if form.validate_on_submit():
        edited = False
        old_cn = series.common_name
        if form.common_name.data != series.common_name.id:
            edited = True
            series.common_name = CommonName.query.get(form.common_name.data)
            flash('Common name for \'{0}\' changed to: {1}'.
                  format(series.fullname, series.common_name.name))
        form.name.data = dbify(form.name.data)
        old_name = series.name
        if form.name.data != series.name:
            edited = True
            series.name = dbify(form.name.data)
            flash('Series name changed to: {0}'.format(series.name))
        if old_name != series.name or old_cn is not series.common_name:
            for cv in series.cultivars:
                old_path = url_for('seeds.cultivar',
                                   idx_slug=series.common_name.index.slug,
                                   cn_slug=old_cn.slug,
                                   cv_slug=cv.slug)
                if cv.common_name is not series.common_name:
                    flash(Markup(
                        'Warning: the common name of the cultivar \'{0}\' is '
                        'not \'{1}\'. You should probably <a href="{2}" '
                        'target="_blank">edit {0}</a> to use the same common '
                        'name as the series it belongs to.'
                        .format(cv.fullname,
                                series.common_name.name,
                                url_for('seeds.edit_cultivar', cv_id=cv.id))
                    ))
                new_path = url_for('seeds.cultivar',
                                   idx_slug=series.common_name.index.slug,
                                   cn_slug=series.common_name.slug,
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
        if form.position.data != series.position:
            edited = True
            series.position = form.position.data
            if form.position.data == Series.BEFORE_CULTIVAR:
                flash('Series name will now be placed before cultivar name in '
                      'cultivars in the {0} series.'.format(series.name))
            elif form.position.data == Series.AFTER_CULTIVAR:
                flash('Series name will now be placed after cultivar name in '
                      'cultivars in the {0} series.'.format(series.name))
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to series \'{0}\'.'.
                  format(series.fullname))
    form.populate(series)
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.edit_index'), 'Edit Index'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series')
    )
    return render_template('seeds/edit_series.html',
                           crumbs=crumbs,
                           form=form,
                           series=series)


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
    form.cv_id = cv.id
    if form.validate_on_submit():
        edited = False
        form.name.data = dbify(form.name.data)
        old_cv_slug = cv.slug
        old_cn = cv.common_name
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
        if cv.name != form.name.data:
            edited = True
            flash('Changed cultivar name from \'{0}\' to \'{1}\''.
                  format(cv.name, form.name.data))
            cv.name = form.name.data
        if not cv.common_name or \
                form.common_name.data != cv.common_name.id:
            edited = True
            cn = CommonName.query.get(form.common_name.data)
            flash('Changed common name to \'{0}\' for: {1}'.
                  format(cn.name, cv.fullname))
            cv.common_name = CommonName.query.get(form.common_name.data)
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
        if current_app.config.get('SHOW_CULTIVAR_PAGES') and (
                old_cv_slug != cv.slug or
                old_cn is not cv.common_name):
            old_path = url_for('seeds.cultivar',
                               idx_slug=old_cn.index.slug,
                               cn_slug=old_cn.slug,
                               cv_slug=old_cv_slug)
            new_path = url_for('seeds.cultivar',
                               idx_slug=cv.common_name.index.slug,
                               cn_slug=cv.common_name.slug,
                               cv_slug=cv.slug)
            flash(redirect_warning(old_path,
                                   '<a href="{0}" target="_blank">{1}</a>'
                                   .format(url_for('seeds.add_redirect',
                                                   old_path=old_path,
                                                   new_path=new_path,
                                                   status_code=301),
                                           new_path)))
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
        if form.active.data:
            if not cv.active:
                edited = True
                flash('\'{0}\' is now active.'.format(cv.fullname))
                cv.active = True
        else:
            if cv.active:
                edited = True
                flash('\'{0}\' is no longer active.'.
                      format(cv.fullname))
                cv.active = False
        if form.visible.data:
            if cv.invisible:
                edited = True
                flash('\'{0}\' will now be visible on auto-generated pages.'
                      .format(cv.fullname))
                cv.invisible = False
        else:
            if not cv.invisible:
                edited = True
                flash('\'{0}\' will no longer be visible on auto-generated '
                      'pages.'.format(cv.fullname))
                cv.invisible = True
        if not form.synonyms.data and cv.synonyms:
            edited = True
            cv.synonyms_string = None
            flash('Synonyms for \'{0}\' have been cleared.'
                  .format(cv.fullname))
        elif form.synonyms.data != cv.synonyms_string:
            edited = True
            cv.synonyms_string = form.synonyms.data
            flash('Synonyms for \'{0}\' set to: {1}'
                  .format(cv.fullname, cv.synonyms_string))
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
        (url_for('seeds.edit_index'), 'Edit Index'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series'),
        (url_for('seeds.edit_cultivar'), 'Edit Cultivar')
    )
    return render_template('seeds/edit_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


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
    form.pkt = packet
    if form.validate_on_submit():
        edited = False
        form.sku.data = form.sku.data.strip()
        if form.sku.data != packet.sku:
            edited = True
            packet.sku = form.sku.data.strip()
        dec_p = USDollar.usd_to_decimal(form.price.data)
        if dec_p != packet.price:
            edited = True
            packet.price = dec_p
        fq = form.quantity.data
        fu = form.units.data.strip()
        if (str(fq) != str(packet.quantity.value)
                or fu != packet.quantity.units):
            edited = True
            oldqty = packet.quantity
            qty = Quantity.query.filter(
                Quantity.value == fq,
                Quantity.units == fu,
                Quantity.is_decimal == Quantity.dec_check(fq)
            ).one_or_none()
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
        (url_for('seeds.edit_index'), 'Edit Index'),
        (url_for('seeds.edit_common_name'), 'Edit Common Name'),
        (url_for('seeds.edit_botanical_name'), 'Edit Botanical Name'),
        (url_for('seeds.edit_series'), 'Edit Series'),
        (url_for('seeds.edit_cultivar'), 'Edit Cultivar'),
        (url_for('seeds.edit_packet'), 'Edit Packet')
    )
    return render_template('seeds/edit_packet.html',
                           crumbs=crumbs,
                           form=form)


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
                bn.synonyms_string = None
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
        (url_for('seeds.remove_index'), 'Remove Index'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name')
    )
    return render_template('seeds/remove_botanical_name.html',
                           bn=bn,
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_index', methods=['GET', 'POST'])
@seeds.route('/remove_index/<idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_index(idx_id=None):
    """Remove an index from the database."""
    if idx_id is None:
        return redirect(url_for('seeds.select_index',
                                dest='seeds.remove_index'))
    index = Index.query.get(idx_id)
    if index is None:
        return redirect(url_for('seeds.select_index',
                                dest='seeds.remove_index'))
    form = RemoveIndexForm()
    form.idx = index
    try:
        form.set_move_to()
    except ValueError as e:
        flash('Error: {0}'.format(e))
        return redirect(url_for('seeds.add_index'))
    if form.validate_on_submit():
        if form.verify_removal.data:
            old_idx_slug = index.slug
            idx2 = Index.query.get(form.move_to.data)
            new_idx_slug = idx2.slug
            flash('Common names and cultivars formerly associated with '
                  '\'{0}\' are now associated with \'{1}\'.'
                  .format(index.name, idx2.name))
            old_path = url_for('seeds.index_page',
                               idx_slug=old_idx_slug)
            new_path = url_for('seeds.index_page',
                               idx_slug=new_idx_slug)
            flash(redirect_warning(
                old_path,
                '<a href="{0}">{1}</a>'
                .format(url_for('seeds.add_redirect',
                                old_path=old_path,
                                new_path=new_path,
                                status_code=301),
                        new_path)
            ))
            for cn in index.common_names:
                if cn.name not in [cona.name for cona in idx2.common_names]:
                    idx2.common_names.append(cn)
                    old_path = url_for('seeds.common_name',
                                       idx_slug=old_idx_slug,
                                       cn_slug=cn.slug)
                    new_path = url_for('seeds.common_name',
                                       idx_slug=new_idx_slug,
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
                else:
                    flash('Warning: A common name \'{0}\' already exists '
                          'under the index \'{1}\'. All cultivars belonging '
                          'to {3} &gt; {0} have been moved to {1} &gt; {0}.'
                          .format(cn.name, idx2.name, index.name))
                    for cn2 in idx2.common_names:
                        if cn2.name == cn.name:
                            for cv in cn.cultivars:
                                if cv not in [cv2.fullname for cv2 in
                                              cn2.cultivars]:
                                    cn2.cultivars.append(cv)
                                else:
                                    # TODO: Handle cultivar conflicts.
                                    flash('Error: The cultivar \'{0}\' was '
                                          'not moved because it already '
                                          'exists under the new common name!')
                if current_app.config.get('SHOW_CULTIVAR_PAGES'):
                    for cv in cn.cultivars:
                        old_path = url_for('seeds.cultivar',
                                           idx_slug=old_idx_slug,
                                           cn_slug=cv.common_name.slug,
                                           cv_slug=cv.slug)
                        new_path = url_for('seeds.cultivar',
                                           idx_slug=new_idx_slug,
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
            flash('The index \'{1}\' has been removed from the database.'.
                  format(index.id, index.name))
            db.session.delete(index)
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\''
                  ' if you want to remove this index.')
            return redirect(url_for('seeds.remove_index',
                                    idx_id=idx_id))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.remove_index'), 'Remove Index')
    )
    return render_template('seeds/remove_index.html',
                           crumbs=crumbs,
                           form=form,
                           index=index)


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
                cn.synonyms_string = None
                flash('Synonyms for \'{0}\' cleared, and orphaned synonyms '
                      'have been deleted.'.format(cn.name))
            cn2 = CommonName.query.get(form.move_to.data)
            new_cn_slug = cn2.slug
            old_path = url_for('seeds.common_name',
                               idx_slug=cn.index.slug,
                               cn_slug=old_cn_slug)
            urllist = []
            new_path = url_for('seeds.common_name',
                               idx_slug=cn2.index.slug,
                               cn_slug=new_cn_slug)
            urllist.append('<a href="{0}" target="_blank">{1}</a>'
                           .format(url_for('seeds.add_redirect',
                                           old_path=old_path,
                                           new_path=new_path,
                                           status_code=301),
                                   new_path))
            flash(redirect_warning(old_path, list_to_or_string(urllist)))
            flash('Botanical names and cultivars formerly associated with '
                  '\'{0}\' are now associated with \'{1}\'.'
                  .format(cn.name, cn2.name))
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
                        for idx in cn.indexes:
                            old_path = url_for('seeds.cultivar',
                                               idx_slug=idx.slug,
                                               cn_slug=old_cn_slug,
                                               cv_slug=cv.slug)
                            urllist = []
                            for idx2 in cn2.indexes:
                                new_path = url_for('seeds.cultivar',
                                                   idx_slug=idx2.slug,
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
        (url_for('seeds.remove_index'), 'Remove Index'),
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
        (url_for('seeds.remove_index'), 'Remove Index'),
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
                cv.synonyms_string = None
            flash('The cultivar \'{0}\' has been deleted. Forever. I hope '
                  'you\'re happy with yourself.'.format(cv.fullname))
            old_path = url_for('seeds.cultivar',
                               idx_slug=cv.common_name.index.slug,
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
        (url_for('seeds.remove_index'), 'Remove Index'),
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
        (url_for('seeds.remove_index'), 'Remove Index'),
        (url_for('seeds.remove_common_name'), 'Remove Common Name'),
        (url_for('seeds.remove_botanical_name'), 'Remove Botanical Name'),
        (url_for('seeds.remove_series'), 'Remove Series')
    )
    return render_template('seeds/remove_series.html',
                           crumbs=crumbs,
                           form=form,
                           series=series)


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


@seeds.route('/select_index', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_index():
    """Select an index to load on another page.

    Request Args:
        dest (str): The route to redirect to once index is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectIndexForm()
    form.set_index()
    if form.validate_on_submit():
        return redirect(url_for(dest, idx_id=form.index.data))
    crumbs = make_breadcrumbs(
        (url_for('seeds.manage'), 'Manage Seeds'),
        (url_for('seeds.select_index', dest=dest), 'Select Index')
    )
    return render_template('seeds/select_index.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_common_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_common_name():
    """Select a common name to load on another page.

    Request Args:
        dest (str): The route to redirect to once index is selected.
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


@seeds.route('/manage')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def manage():
    pending = Pending(current_app.config.get('PENDING_FILE'))
    lc = LastCommit()
    if pending.exists():
        pending.load()
    return render_template('seeds/manage.html', pending=pending, lc=lc)


@seeds.route('/')
def index():
    """Index page for seeds section."""
    indexes = Index.query.all()
    return render_template('seeds/index.html', indexes=indexes)


@seeds.route('/<idx_slug>')
def index_page(idx_slug=None):
    """Display an index."""
    index = Index.query.filter_by(slug=idx_slug).first()
    if index is not None:
        crumbs = make_breadcrumbs(
            (url_for('seeds.index'), 'All Seeds'),
            (url_for('seeds.index_page', idx_slug=index.slug),
             index.header)
        )
        return render_template('seeds/indexes.html',
                               crumbs=crumbs,
                               index=index)
    else:
        abort(404)


@seeds.route('/<idx_slug>/<cn_slug>')
def common_name(idx_slug=None, cn_slug=None):
    """Display page for a common name."""
    cn = CommonName.query\
        .join(Index, Index.id == CommonName.index_id)\
        .filter(CommonName.slug == cn_slug, Index.slug == idx_slug)\
        .one_or_none()
    if cn is not None:
        individuals = [cv for cv in cn.cultivars if not cv.series and
                       not cv.common_name.parent]
        crumbs = (
            cblr.crumble('index', 'All seeds'),
            cblr.crumble('index_page', cn.index.header, idx_slug=idx_slug),
            cblr.crumble('common_name', idx_slug=idx_slug, cn_slug=cn_slug)
        )

        return render_template('seeds/common_name.html',
                               individuals=individuals,
                               cn=cn,
                               crumbs=crumbs)
    else:
        abort(404)


@seeds.route('/<idx_slug>/<cn_slug>/<cv_slug>')
def cultivar(idx_slug=None, cn_slug=None, cv_slug=None):
    """Display a page for a given cultivar."""
    if idx_slug and cn_slug and cv_slug:
        cv = Cultivar.query\
            .join(CommonName, CommonName.id == Cultivar.common_name_id)\
            .join(Index, Index.id == CommonName.index_id)\
            .filter(Index.slug == idx_slug,
                    CommonName.slug == cn_slug,
                    Cultivar.slug == cv_slug)\
            .one_or_none()
        if cv and current_app.config.get('SHOW_CULTIVAR_PAGES'):
            crumbs = make_breadcrumbs(
                (url_for('seeds.index'), 'All Seeds'),
                (url_for('seeds.index_page',
                         idx_slug=idx_slug),
                 cv.common_name.index.header),
                (url_for('seeds.common_name',
                         idx_slug=idx_slug,
                         cn_slug=cn_slug),
                 cv.common_name.name),
                (url_for('seeds.cultivar',
                         idx_slug=idx_slug,
                         cn_slug=cn_slug,
                         cv_slug=cv_slug),
                 cv.name)
            )
            return render_template('seeds/cultivar.html',
                                   idx_slug=idx_slug,
                                   cn_slug=cn_slug,
                                   crumbs=crumbs,
                                   cultivar=cv)
    abort(404)


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

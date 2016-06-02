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
from app import db, Permission
from app.breadcrumbs import Crumbler
from app.decorators import permission_required
from app.pending import Pending
from app.redirects import Redirect, RedirectsFile
from . import seeds
from ..lastcommit import LastCommit
from .models import (
    auto_position,
    BotanicalName,
    Section,
    CommonName,
    Cultivar,
    get_previous_instance,
    Image,
    Index,
    Packet,
    Quantity,
    set_position,
    USDollar
)
from .forms import (
    AddBotanicalNameForm,
    AddIndexForm,
    AddCommonNameForm,
    AddPacketForm,
    AddRedirectForm,
    AddCultivarForm,
    AddSectionForm,
    EditBotanicalNameForm,
    EditIndexForm,
    EditCommonNameForm,
    EditPacketForm,
    EditCultivarForm,
    EditSectionForm,
    RemoveBotanicalNameForm,
    RemoveIndexForm,
    RemoveCommonNameForm,
    RemovePacketForm,
    RemoveSectionForm,
    RemoveCultivarForm,
    SelectBotanicalNameForm,
    SelectIndexForm,
    SelectCommonNameForm,
    SelectPacketForm,
    SelectCultivarForm,
    SelectSectionForm
)


cblr = Crumbler('seeds')


ADD_ROUTES = (
    ('manage', 'Manage Seeds'),
    'add_index',
    'add_common_name',
    'add_botanical_name',
    'add_section',
    'add_cultivar',
    'add_packet'
)


EDIT_ROUTES = (
    ('manage', 'Manage Seeds'),
    'edit_index',
    'edit_common_name',
    'edit_botanical_name',
    'edit_section',
    'edit_cultivar',
    'edit_packet'
)


REMOVE_ROUTES = (
    ('manage', 'Manage Seeds'),
    'remove_index',
    'remove_common_name',
    'remove_botanical_name',
    'remove_section',
    'remove_cultivar',
    'remove_packet'
)


class NotEnabledError(RuntimeError):
    """Exception for trying to run a disabled feature.

    Attributes:
        message: The message to display when the error is raised.
    """
    def __init__(self, message):
        self.message = message


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
        index: The `Index` being redirected from.
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

    old_path = url_for('seeds.index', idx_slug=old_idx_slug)
    new_path = url_for('seeds.index', idx_slug=new_idx_slug)

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
        common_name: The `CommonName` being redirected from.
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
            except NotEnabledError:
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
        cultivar: The `Cultivar` being redirected from.
        old_idx_slug: Optional `Index.slug` to redirect from.
        old_cn_slug: Optional `CommonName.slug` to redirect from.
        old_cv_slug: Optional `Cultivar.slug` to redirect from.
        new_idx_slug: Optional `Index.slug` to redirect to.
        new_cn_slug: Optional `CommonName.slug` to redirect to.
        new_cv_slug: Optional `Cultivar.slug` to redirect to.

    Raises:
        ValueError: If no slugs were passed.
        NotEnabledError: If ``SHOW_CULTIVAR_PAGES`` is not enabled in config.

    Returns:
        str: The redirect warning message.
    """
    if not current_app.config.get('SHOW_CULTIVAR_PAGES'):
        raise NotEnabledError('This function cannot be run without '
                              'SHOW_CULTIVAR_PAGES enabled in config!')
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
            messages.append('Description set to: <p>{0}</p>'
                            .format(index.description))
        if form.pos.data is -1:
            set_position(index, 1)
            messages.append('Will be listed before other indexes.')
        else:
            other = Index.query.get(form.pos.data)
            if other.position is None:
                auto_position(other)
            set_position(index, other.position + 1)
            messages.append('Will be listed after \'{0}\''.format(other.name))
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
        if form.description.data:
            cn.description = form.description.data
            messages.append('Description set to: <p>{0}</p>'
                            .format(cn.description))
        if form.instructions.data:
            cn.instructions = form.instructions.data
            messages.append('Planting instructions set to: <p>{0}</p>'
                            .format(cn.instructions))
        if form.synonyms.data:
            cn.synonyms_string = form.synonyms.data
            messages.append('Synonyms set to: \'{0}\'.'
                            .format(cn.synonyms_string))
        if form.visible.data:
            cn.visible = True
            messages.append('\'{0}\' is visible on auto-generated pages.'
                            .format(cn.name))
        else:
            cn.visible = False
            messages.append('\'{0}\' is not visible on auto-generated pages.'
                            .format(cn.name))
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


@seeds.route('/add_section', methods=['GET', 'POST'])
@seeds.route('/add_section/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_section(cn_id=None):
    """Add a section to the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.add_section'))

    form = AddSectionForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        section = Section(name=form.name.data, common_name=cn)
        db.session.add(section)
        messages.append('Creating section \'{0}\' for common name \'{1}\':'
                        .format(section.name, cn.name))
        if form.description.data:
            section.description = form.description.data
            messages.append('Description set to: <p>{0}</p>.'
                            .format(section.description))
        db.session.commit()
        messages.append('New section \'{0}\' added to the database.'
                        .format(section.fullname))
        flash_all(messages)
        return redirect(url_for('seeds.add_cultivar', cn_id=cn.id))
    crumbs = cblr.crumble_route_group('add_section', ADD_ROUTES)
    return render_template('seeds/add_section.html',
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
        if form.subtitle.data:
            cv.subtitle = form.subtitle.data
            messages.append('Subtitle for \'{0}\' set to: {1}'
                            .format(cv.fullname, cv.subtitle))
        if form.botanical_name.data:
            cv.botanical_name = BotanicalName.query\
                .get(form.botanical_name.data)
            messages.append('Botanical name set to: \'{0}\'.'
                            .format(cv.botanical_name.name))
        if form.section.data:
            cv.section = Section.query.get(form.section.data)
            messages.append('Section set to: \'{0}\'.'
                            .format(cv.section.name))
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            upload_path = os.path.join(current_app.config.get('IMAGES_FOLDER'),
                                       thumb_name)
            cv.thumbnail = Image(filename=thumb_name)
            form.thumbnail.data.save(upload_path)
            messages.append('Thumbnail uploaded as: {0}'.format(thumb_name))
        if form.description.data:
            cv.description = form.description.data
            messages.append('Description set to: <p>{0}</p>'
                            .format(cv.description))
        if form.synonyms.data:
            cv.synonyms_string = form.synonyms.data
            messages.append('Synonyms set to: \'{0}\'.'
                            .format(cv.synonyms_string))
        if form.new_until.data and form.new_until.data > datetime.date.today():
            cv.new_until = form.new_until.data
            messages.append('\'{0}\' will be marked as new until: {1}'
                            .format(cv.fullname,
                                    cv.new_until.strftime('%m/%d/%Y')))
        if form.featured.data:
            cv.featured = True
            messages.append('\'{0}\' will be featured on its common '
                            'name\'s page.'.format(cv.fullname))
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
            cv.visible = True
            messages.append('\'{0}\' will be visible in auto-generated pages.'
                            .format(cv.fullname))
        else:
            cv.visible = False
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
        old_slug = index.slug
        messages.append('Editing index \'{0}\':'.format(index.name))
        if form.name.data != index.name:
            edited = True
            index.name = form.name.data
            messages.append('Name changed to: \'{0}\'.'.format(index.name))
        if form.description.data != index.description:
            edited = True
            if form.description.data:
                index.description = form.description.data
                messages.append('Description set to: <p>{0}</p>.'
                                .format(index.description))
            else:
                index.description = None
                messages.append('Description cleared.')
        prev = get_previous_instance(index)
        if prev and form.pos.data == -1:  # Moving to first position.
            edited = True
            set_position(index, 1)
            messages.append('Will be listed before all other indexes.')
        elif (not prev and form.pos.data != -1) or (prev and prev.id != form.pos.data):
            edited = True
            other = Index.query.get(form.pos.data)
            set_position(index, other.position + 1)
            messages.append('Will be listed after \'{0}\'.'.format(other.name))
        if edited:
            db.session.commit()
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(index.name))
            flash_all(messages)

            if old_slug != index.slug:
                warnings = None
                warnings = redirect_index_warnings(
                    index,
                    old_idx_slug=old_slug,
                    new_idx_slug=index.slug
                )
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
        cn_id: The id number of the common name to edit.
    """
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.edit_common_name'))
    form = EditCommonNameForm(obj=cn)
    if form.validate_on_submit():
        edited = False
        messages = []
        old_slugs = {'cn': cn.slug, 'idx': cn.index.slug}
        messages.append('Editing common name \'{0}\':'.format(cn.name))
        if form.index_id.data != cn.index.id:
            edited = True
            cn.index = Index.query.get(form.index_id.data)
            messages.append('Index changed to: \'{0}\'.'.format(cn.index.name))
        if form.name.data != cn.name:
            edited = True
            cn.name = form.name.data
            messages.append('Name changed to: \'{0}\'.'.format(cn.name))
        if not form.description.data:
            form.description.data = None
        if form.description.data != cn.description:
            edited = True
            if form.description.data:
                cn.description = form.description.data
                messages.append('Description changed to: <p>{0}</p>'
                                .format(cn.description))
            else:
                cn.description = None
                messages.append('Description cleared.')
        if not form.instructions.data:
            form.instructions.data = None
        if form.instructions.data != cn.instructions:
            edited = True
            if form.instructions.data:
                cn.instructions = form.instructions.data
                messages.append('Planting instructions set to: <p>{0}</p>'
                                .format(cn.instructions))
            else:
                cn.instructions = None
                messages.append('Planting instructions cleared.')
        if form.synonyms_string.data != cn.synonyms_string:
            edited = True
            if form.synonyms_string.data:
                cn.synonyms_string = form.synonyms_string.data
                messages.append('Synonyms changed to: \'{0}\'.'
                                .format(cn.synonyms_string))
            else:
                cn.synonyms_string = None
                messages.append('Synonyms cleared.')
        if edited:
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(cn.name))
            db.session.commit()
            flash_all(messages)

            if old_slugs['cn'] != cn.slug or old_slugs['idx'] != cn.index.slug:
                warnings = None
                warnings = redirect_common_name_warnings(
                    cn,
                    old_idx_slug=old_slugs['idx'],
                    old_cn_slug=old_slugs['cn'],
                    new_idx_slug=cn.index.slug,
                    new_cn_slug=cn.slug
                )
                if warnings:
                    flash_all(warnings, 'warning')

            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made.'.format(cn.name))
            flash_all(messages)
            return redirect(url_for('seeds.edit_common_name', cn_id=cn.id))
    crumbs = cblr.crumble_route_group('edit_common_name', EDIT_ROUTES)
    return render_template('seeds/edit_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_botanical_name', methods=['GET', 'POST'])
@seeds.route('/edit_botanical_name/<bn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_botanical_name(bn_id=None):
    bn = BotanicalName.query.get(bn_id) if bn_id else None
    if bn is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.edit_botanical_name'))
    form = EditBotanicalNameForm(obj=bn)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing botanical name \'{0}\'.'.format(bn.name))
        form.name.data = form.name.data.strip()
        if form.name.data != bn.name:
                edited = True
                bn.name = form.name.data
                messages.append('Name changed to: \'{0}\'.'.format(bn.name))
        for cn in list(bn.common_names):
            if cn.id not in form.common_names.data:
                edited = True
                bn.common_names.remove(cn)
                messages.append('Removed common name \'{0}\'.'.format(cn.name))
        cnids = [cona.id for cona in bn.common_names]
        for cnid in form.common_names.data:
            if cnid not in cnids:
                edited = True
                cn = CommonName.query.get(cnid)
                bn.common_names.append(cn)
                messages.append('Added common name \'{0}\'.'.format(cn.name))
        if form.synonyms_string.data != bn.synonyms_string:
            edited = True
            if form.synonyms_string.data:
                bn.synonyms_string = form.synonyms_string.data
                messages.append('Synonyms changed to: \'{0}\'.'
                                .format(bn.synonyms_string))
            else:
                bn.synonyms_string = None
                messages.append('Synonyms cleared.')
        if edited:
            db.session.commit()
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(bn.name))
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made.'.format(bn.name))
            flash_all(messages)
            return redirect(url_for('seeds.edit_botanical_name', bn_id=bn_id))
    crumbs = cblr.crumble_route_group('edit_botanical_name', EDIT_ROUTES)
    return render_template('/seeds/edit_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_section', methods=['GET', 'POST'])
@seeds.route('/edit_section/<section_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_section(section_id=None):
    """Display page for editing a Section from the database."""
    section = Section.query.get(section_id) if section_id else None
    if section is None:
        return redirect(url_for('seeds.select_section',
                                dest='seeds.edit_section'))
    form = EditSectionForm(obj=section)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing section \'{0}\':'.format(section.name))
        old_cn = section.common_name
        if form.common_name_id.data != section.common_name.id:
            edited = True
            section.common_name = CommonName.query.get(
                form.common_name_id.data
            )
            messages.append('Common name changed to: \'{0}\'.'
                            .format(section.common_name.name))
        old_name = section.name
        if form.name.data != section.name:
            edited = True
            section.name = form.name.data
            messages.append('Name changed to: {0}'.format(section.name))
        if not form.description.data:
            form.description.data = None
        if form.description.data != section.description:
            edited = True
            if form.description.data:
                section.description = form.description.data
                messages.append('Description changed to: <p>{0}</p>'
                                .format(section.description))
            else:
                section.description = None
                messages.append('Description cleared.')
        if old_cn is not section.common_name:
            for cv in section.cultivars:
                if cv.common_name is not section.common_name:
                    old_cvname = cv.fullname
                    cv.common_name = section.common_name
                    messages.append('Common name for the cultivar \'{0}\' has '
                                    'been changed to: \'{1}\'.'
                                    .format(old_cvname, cv.common_name.name))
        if edited:
            db.session.commit()
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(section.name))
            flash_all(messages)

            if old_cn is not section.common_name or old_name != section.name:
                try:
                    warnings = []
                    for cv in section.cultivars:
                        warnings.append(redirect_cultivar_warning(
                            cv,
                            old_cv_slug=cv.slug,
                            old_cn_slug=old_cn.slug,
                            new_cv_slug=cv.generate_slug(),
                            new_cn_slug=section.common_name.slug
                        ))
                    if warnings:
                        flash_all(warnings)
                except NotEnabledError:
                    pass

            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made.'
                            .format(section.name))
            flash_all(messages)
            return redirect(url_for('seeds.edit_section',
                                    section_id=section_id))
    crumbs = cblr.crumble_route_group('edit_section', EDIT_ROUTES)
    return render_template('seeds/edit_section.html',
                           crumbs=crumbs,
                           form=form,
                           section=section)


@seeds.route('/edit_cultivar', methods=['GET', 'POST'])
@seeds.route('/edit_cultivar/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_cultivar(cv_id=None):
    """Edit a cultivar stored in the database."""
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if cv is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.edit_cultivar'))
    form = EditCultivarForm(obj=cv)
    if form.validate_on_submit():
        edited = False
        messages = []
        warnings = []
        messages.append('Editing cultivar \'{0}\':'.format(cv.fullname))
        old_slugs = {'cv': cv.slug,
                     'cn': cv.common_name.slug,
                     'idx': cv.common_name.index.slug}
        if form.common_name_id.data != cv.common_name_id:
            edited = True
            cv.common_name = CommonName.query.get(form.common_name_id.data)
            messages.append('Common name changed to: \'{0}\'.'
                            .format(cv.common_name.name))
        if not form.botanical_name_id.data:
            form.botanical_name_id.data = None
        if form.botanical_name_id.data != cv.botanical_name_id:
            edited = True
            if form.botanical_name_id.data:
                cv.botanical_name = BotanicalName.query.get(
                    form.botanical_name_id.data
                )
                messages.append('Botanical name changed to: \'{0}\'.'
                                .format(cv.botanical_name.name))
            else:
                cv.botanical_name = None
                messages.append('Botanical name cleared.')
        if not form.section_id.data:
            form.section_id.data = None
        if form.section_id.data != cv.section_id:
            edited = True
            if form.section_id.data:
                cv.section = Section.query.get(form.section_id.data)
                messages.append('Section changed to: \'{0}\'.'
                                .format(cv.section.name))
            else:
                cv.section = None
                messages.append('Section cleared.')
        if form.subtitle.data != cv.subtitle:
            if form.subtitle.data:
                edited = True
                cv.subtitle = form.subtitle.data
                messages.append('Subtitle changed to: \'{0}\.'
                                .format(cv.subtitle))
            elif cv.subtitle:
                edited = True
                cv.subtitle = None
                messages.append('Subtitle set to default.')
        if cv.name != form.name.data:
            edited = True
            cv.name = form.name.data
            messages.append('(Short) Name changed to: \'{0}\'.'
                            .format(cv.name))
        if form.thumbnail.data:
            thumb_name = secure_filename(form.thumbnail.data.filename)
            edited = True
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
            img = Image.query.filter_by(filename=thumb_name).one_or_none()
            if img:
                # Rename existing image instead of overwriting it.
                now = datetime.datetime.now().strftime('%m-%d-%Y_%H_%M_%S_%f')
                postfix = '_moved_' + now
                img.add_postfix(postfix)
                warnings.append(
                    'Warning: An image already exists with the filename '
                    '\'{0}\', so it has been renamed to \'{1}\' to prevent '
                    'it from being overwritten by the upload of \'{0}\'.'
                    .format(thumb_name, img.filename)
                )
            cv.thumbnail = Image(filename=thumb_name)
            form.thumbnail.data.save(upload_path)
            messages.append('Thumbnail uploaded as: \'{0}\'.'
                            .format(cv.thumbnail.filename))
        if not form.description.data:
            form.description.data = None
        if form.description.data != cv.description:
            edited = True
            if form.description.data:
                cv.description = form.description.data
                messages.append('Description changed to: <p>{0}</p>'
                                .format(cv.description))
            else:
                cv.description = None
                messages.append('Description cleared.')
        if form.synonyms_string.data != cv.synonyms_string:
            edited = True
            cv.synonyms_string = form.synonyms_string.data
            if form.synonyms_string.data:
                messages.append('Synonyms set to: \'{0}\'.'
                                .format(cv.synonyms_string))
            else:
                messages.append('Synonyms cleared.')
        if (not form.new_until.data or
                form.new_until.data <= datetime.date.today()):
            form.new_until.data = None
        if form.new_until.data != cv.new_until:
            edited = True
            if not form.new_until.data:
                cv.new_until = None
                messages.append('No longer marked as new.')
            else:
                cv.new_until = form.new_until.data
                messages.append('Marked as new until {0}.'
                                .format(cv.new_until.strftime('%m/%d/%Y')))
        if form.featured.data and not cv.featured:
            edited = True
            cv.featured = True
            messages.append('\'{0}\' will now be featured on its common '
                            'name\'s page.'.format(cv.fullname))
        elif not form.featured.data and cv.featured:
            edited = True
            cv.featured = False
            messages.append('\'{0}\' will no longer be featured on its common '
                            'name\'s page.'.format(cv.fullname))

        if form.in_stock.data and not cv.in_stock:
            edited = True
            cv.in_stock = True
            messages.append('\'{0}\' is now in stock.'.format(cv.fullname))
        elif not form.in_stock.data and cv.in_stock:
            edited = True
            cv.in_stock = False
            messages.append('\'{0}\' is now out of stock.'
                            .format(cv.fullname))
        if form.active.data and not cv.active:
            edited = True
            cv.active = True
            messages.append('\'{0}\' is now active.'.format(cv.fullname))
        elif not form.active.data and cv.active:
            edited = True
            cv.active = False
            messages.append('\'{0}\' is no longer active.'
                            .format(cv.fullname))
        if form.visible.data and not cv.visible:
            edited = True
            cv.visible = True
            messages.append('\'{0}\' will now be visible on '
                            'auto-generated pages.'.format(cv.fullname))
        elif not form.visible.data and cv.visible:
            edited = True
            cv.visible = False
            messages.append('\'{0}\' will no longer be visible on '
                            'auto-generated pages.'.format(cv.fullname))
        if edited:
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(cv.fullname))
            db.session.commit()
            flash_all(messages)
            if (old_slugs['cv'] != cv.slug or
                    old_slugs['cn'] != cv.common_name.slug or
                    old_slugs['idx'] != cv.common_name.index.slug):
                try:
                    warnings.append(redirect_cultivar_warning(
                        cv,
                        old_idx_slug=old_slugs['idx'],
                        old_cn_slug=old_slugs['cn'],
                        old_cv_slug=old_slugs['cv'],
                        new_idx_slug=cv.common_name.index.slug,
                        new_cn_slug=cv.common_name.slug,
                        new_cv_slug=cv.slug
                    ))
                except NotEnabledError:
                    pass
            if warnings:
                flash_all(warnings)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made'
                            .format(cv.fullname))
            flash_all(messages)
            return redirect(url_for('seeds.edit_cultivar', cv_id=cv_id))
    crumbs = cblr.crumble_route_group('edit_cultivar', EDIT_ROUTES)
    return render_template('seeds/edit_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/edit_packet', methods=['GET', 'POST'])
@seeds.route('/edit_packet/<pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_packet(pkt_id=None):
    packet = Packet.query.get(pkt_id) if pkt_id else None
    if packet is None:
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.edit_packet'))
    form = EditPacketForm(obj=packet)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing packet \'{0}\'.'.format(packet.info))
        if form.cultivar_id.data != packet.cultivar_id:
            edited = True
            packet.cultivar = Cultivar.query.get(form.cultivar_id.data)
            messages.append('Cultivar changed to: \'{0}\'.'
                            .format(packet.cultivar.fullname))
        form.sku.data = form.sku.data.strip()
        if form.sku.data != packet.sku:
            edited = True
            packet.sku = form.sku.data
            messages.append('SKU changed to: \'{0}\'.'.format(packet.sku))
        dec_p = USDollar.usd_to_decimal(form.price.data)
        if dec_p != packet.price:
            edited = True
            packet.price = dec_p
            messages.append('Price set to: \'${0}\'.'.format(packet.price))
        fq = form.qty_val.data
        fu = form.units.data.strip()
        if (Quantity(value=fq).value != packet.quantity.value or
                fu != packet.quantity.units):
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
                packet.quantity = Quantity(value=fq, units=fu)
            if not oldqty.packets:
                db.session.delete(oldqty)
            messages.append('Quantity set to: \'{0} {1}\'.'
                            .format(packet.quantity.value,
                                    packet.quantity.units))
        if edited:
            db.session.commit()
            messages.append('Changes to \'{0}\' committed to the database.'
                            .format(packet.info))
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to \'{0}\' were made.'
                            .format(packet.info))
            flash_all(messages)
            return redirect(url_for('seeds.edit_packet', pkt_id=pkt_id))
    crumbs = cblr.crumble_route_group('edit_packet', EDIT_ROUTES)
    return render_template('seeds/edit_packet.html',
                           crumbs=crumbs,
                           form=form)


def move_cultivars(cn, other):
    """Move all instances of `Cultivar` from one `CommonName` to another.

    Note:
        This doesn't actually move them, it just adds them to the other side

    Attributes:
        cn: The `CommonName` to move `Cultivar` instances from.
        other: The `CommonName` to move the cultivars to.
    """
    warnings = []
    for cv in list(cn.cultivars):
        if cv.name_with_section not in [c.name_with_section for c in
                                        other.cultivars]:
            other.cultivars.append(cv)
        else:
            warnings.append(
                'Could not move \'{0}\' because a cultivar with the same name '
                'and section already exists! Click <a href="{1}">here</a> if '
                'you want to edit it, or <a href="{2}">here</a> if you want '
                'to remove it.'
                .format(cv.fullname,
                        url_for('seeds.edit_cultivar', cv_id=cv.id),
                        url_for('seeds.remove_cultivar', cv_id=cv.id))
            )
    return warnings


def move_botanical_names(cn, other):
    """Move botanical names from one `CommonName` to another.

    Args:
        cn: The `CommonName` to move `BotanicalName` instances from.
        other: The `CommonName` to move them to.
    """
    for bn in list(cn.botanical_names):
        if bn not in other.botanical_names:
            other.botanical_names.append(bn)


def move_common_names(idx, other):
    """Move all instances of `CommonName` from one `Index` to another.

    Attributes:
        idx: The `Index` to move `CommonName` instances from.
        other: The `Index` to move the common names to.
    """
    warnings = []
    for cn in list(idx.common_names):
        other_cns = [c.name for c in other.common_names]
        if cn.name not in other_cns:
            other.common_names.append(cn)
        else:
            warnings.append(
                'Could not move \'{0}\' because a common name with the same '
                'name already belongs to \'{1}\'. Instead of moving it, its '
                'children (botanical names, section, and cultivars) will be '
                'moved to the one belonging to \'{1}\' if possible.'
                .format(cn.name, other.name)
            )
            other_cn = next((
                c for c in other.common_names if c.name == cn.name), None
            )
            move_botanical_names(cn, other_cn)
            warnings += move_section(cn, other_cn)
            warnings += move_cultivars(cn, other_cn)
    return warnings


def move_section(cn, other):
    """Move all instances of `Section` from one `CommonName` to another.

    Attributes:
        cn: The `CommonName` to move `Section` instances from.
        other: The `CommonName` to move the section to.
    """
    warnings = []
    for sec in cn.sections:
        if sec.name not in [s.name for s in other.section]:
            other.section.append(sec)
        else:
            warnings.append(
                'Could not move \'{0}\' because a section with the same name '
                'already belongs to \'{1}\'. Click <a href="{2}">here</a> if '
                'you would like to edit \'{0}\', or <a href="{3}">here</a> '
                'if you would like to remove it.'
                .format(sec.name,
                        other.name,
                        url_for('seeds.edit_section', section_id=sec.id),
                        url_for('seeds.remove_section', section_id=sec.id))
            )
    return warnings


@seeds.route('/remove_index', methods=['GET', 'POST'])
@seeds.route('/remove_index/<idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_index(idx_id=None):
    """Remove an index from the database."""
    index = Index.query.get(idx_id) if idx_id else None
    if index is None:
        return redirect(url_for('seeds.select_index',
                                dest='seeds.remove_index'))
    if Index.query.count() == 1:
        flash('Error: Cannot remove the index \'{0}\' without another index '
              'existing to move its children to! Please add an index so you '
              'can move {0}\'s children to it.'
              .format(index.name), 'error')
        return redirect(url_for('seeds.add_index'))
    form = RemoveIndexForm(index=index)
    if form.validate_on_submit():
        messages = []
        warnings = []
        if form.verify_removal.data:
            messages.append('Removing index \'{0}\':'.format(index.name))
            new_index = Index.query.get(form.move_to.data)
            warnings += redirect_index_warnings(index,
                                                old_idx_slug=index.slug,
                                                new_idx_slug=new_index.slug)
            # This needs to come after redirect warnings because SQLAlchemy
            # removes `CommonName` instances from the old `Index` when
            # appending them to the new `Index`.
            # TODO: See if there are any bugs in this due to things moving
            # after redirect warnings are given.
            warnings += move_common_names(index, new_index)
            db.session.delete(index)
            db.session.commit()
            messages.append('Index removed.')
            flash_all(messages)
            if warnings:
                flash_all(warnings, 'warning')
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Index was not removed, so no changes were made. '
                            'If you would like to remove it, please check the '
                            'box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_index',
                                    idx_id=idx_id))
    crumbs = cblr.crumble_route_group('remove_index', REMOVE_ROUTES)
    return render_template('seeds/remove_index.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_common_name', methods=['GET', 'POST'])
@seeds.route('/remove_common_name/<cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_common_name(cn_id=None):
    """Remove a common name from the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if cn is None:
        return redirect(url_for('seeds.select_common_name',
                                dest='seeds.remove_common_name'))
    form = RemoveCommonNameForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing common name \'{0}\':'.format(cn.name))
            new_cn = CommonName.query.get(form.move_to.data)
            if cn.synonyms:
                cn.synonyms_string = None
                messages.append('Synonyms cleared.')
            move_botanical_names(cn, new_cn)
            try:
                for cv in cn.cultivars:
                    warnings.append(redirect_cultivar_warning(
                        cv,
                        old_cn_slug=cn.slug,
                        new_cn_slug=new_cn.slug
                    ))
            except NotEnabledError:
                pass
            warnings += move_cultivars(cn, new_cn)
            db.session.delete(cn)
            db.session.commit()
            messages.append('Common name removed.')
            flash_all(messages)
            if warnings:
                flash_all(warnings)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Common name was not removed, so no changes '
                            'were made. If you would like to remove it, '
                            'please check the box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_common_name', cn_id=cn_id))
    crumbs = cblr.crumble_route_group('remove_common_name', REMOVE_ROUTES)
    return render_template('seeds/remove_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_botanical_name', methods=['GET', 'POST'])
@seeds.route('/remove_botanical_name/<bn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_botanical_name(bn_id=None):
    """Remove a botanical name from the database."""
    bn = BotanicalName.query.get(bn_id) if bn_id else None
    if bn is None:
        return redirect(url_for('seeds.select_botanical_name',
                                dest='seeds.remove_botanical_name'))
    form = RemoveBotanicalNameForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            messages.append('Removing botanical name \'{0}\':'.format(bn.name))
            if bn.synonyms:
                bn.synonyms_string = None
                messages.append('Synonyms have been cleared.')
            db.session.delete(bn)
            db.session.commit()
            messages.append('Botanical name removed.')
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Botanical name was not removed, so no changes '
                            'were made. If you would like to remove it, '
                            'please check the box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_botanical_name',
                                    bn_id=bn_id))
    crumbs = cblr.crumble_route_group('remove_botanical_name', REMOVE_ROUTES)
    return render_template('seeds/remove_botanical_name.html',
                           bn=bn,
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_section', methods=['GET', 'POST'])
@seeds.route('/remove_section/<section_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_section(section_id=None):
    """Display page for removing section from database."""
    section = Section.query.get(section_id) if section_id else None
    if section is None:
        return redirect(url_for('seeds.select_section',
                                dest='seeds.remove_section'))
    form = RemoveSectionForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing section \'{0}\':'.format(section.name))
            db.session.delete(section)
            db.session.commit()
            messages.append('Section removed.')
            flash_all(messages)
            if warnings:
                flash_all(warnings, 'warning')
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Section was not removed, so no changes were '
                            'made. If you would like to remove it, please '
                            'check the box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_section',
                                    section_id=section_id))
    crumbs = cblr.crumble_route_group('remove_section', REMOVE_ROUTES)
    return render_template('seeds/remove_section.html',
                           crumbs=crumbs,
                           form=form,
                           section=section)


@seeds.route('/remove_cultivar', methods=['GET', 'POST'])
@seeds.route('/remove_cultivar/<cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_cultivar(cv_id=None):
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if cv is None:
        return redirect(url_for('seeds.select_cultivar',
                                dest='seeds.remove_cultivar'))
    form = RemoveCultivarForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing cultivar \'{0}\':'.format(cv.fullname))
            if cv.synonyms:
                cv.synonyms_string = None
                messages.append('Synonyms cleared.')
            if form.delete_images.data:
                if cv.thumbnail:
                    if (not cv.thumbnail.cultivars or
                            cv.thumbnail.cultivars == [cv]):
                        messages.append('Thumbnail image file \'{0}\' deleted.'
                                        .format(cv.thumbnail.filename))
                        db.session.delete(cv.thumbnail)
                    else:
                        messages.append('Thumbnail image file \'{0}\' was not '
                                        'deleted because it is in use by '
                                        'other cultivars.')
                if cv.images:
                    for img in cv.images:
                        if img.cultivars == [cv] and img.cultivar is None:
                            messages.append('Image file \'{0}\' associated '
                                            'with \'{1}\' has been deleted. '
                                            .format(img.filename, cv.fullname))
                            db.session.delete(img)
            old_path = url_for('seeds.cultivar',
                               idx_slug=cv.common_name.index.slug,
                               cn_slug=cv.common_name.slug,
                               cv_slug=cv.slug)
            warnings.append(
                'Warning: the path \'{0}\' is no longer valid. <a '
                'href="{1}" target="_blank">Click here</a> if you wish to'
                'add a redirect for it.'
                .format(old_path,
                        url_for('seeds.add_redirect',
                                old_path=old_path,
                                status_code=301))
            )
            db.session.delete(cv)
            db.session.commit()
            messages.append('Cultivar removed.')
            flash_all(messages)
            if warnings:
                flash_all(warnings, 'warning')
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Cultivar was not removed, so no changes '
                            'were made. If you would like to remove it, '
                            'please check the box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_cultivar', cv_id=cv.id))
    crumbs = cblr.crumble_route_group('remove_cultivar', REMOVE_ROUTES)
    return render_template('seeds/remove_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/remove_packet', methods=['GET', 'POST'])
@seeds.route('/remove_packet/<pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_packet(pkt_id=None):
    """Remove a packet from the database."""
    packet = Packet.query.get(pkt_id) if pkt_id else None
    if packet is None:
        return redirect(url_for('seeds.select_packet',
                                dest='seeds.remove_packet'))
    form = RemovePacketForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            if len(packet.quantity.packets) == 1:
                db.session.delete(packet.quantity)
            db.session.delete(packet)
            db.session.commit()
            messages.append('Packet removed.')
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Packet was not removed, so no changes '
                            'were made. If you would like to remove it, '
                            'please check the box labeled \'Yes\'.')
            flash_all(messages)
            return redirect(url_for('seeds.remove_packet', pkt_id=pkt_id))
    crumbs = cblr.crumble_route_group('remove_packet', REMOVE_ROUTES)
    return render_template('seeds/remove_packet.html',
                           crumbs=crumbs,
                           form=form,
                           packet=packet)


@seeds.route('/select_index', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_index():
    """Select an index to load on another page.

    Request Args:
        dest: The route to redirect to after `Index` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!', 'error')
        return redirect(url_for('seeds.manage'))
    form = SelectIndexForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, idx_id=form.index.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_index', dest=dest)
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
        dest: The route to redirect to after `Index` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCommonNameForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, cn_id=form.common_name.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_common_name', dest=dest)
    )
    return render_template('seeds/select_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_botanical_name', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_botanical_name():
    """Select a botanical name to load on another page.

    Request Args:
        dest: The route to redirect to after `BotanicalName` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectBotanicalNameForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, bn_id=form.botanical_name.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_botanical_name', dest=dest)
    )
    return render_template('seeds/select_botanical_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_section', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_section():
    """Select a section to load on another page.

    Request Args:
        dest: The route to redirect to after `Section` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectSectionForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, section_id=form.section.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_section', dest=dest)
    )
    return render_template('seeds/select_section.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_cultivar', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_cultivar():
    """Select a cultivar to load on another page.

    Request Args:
        dest: The route to redirect after `Cultivar` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCultivarForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, cv_id=form.cultivar.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_cultivar', dest=dest)
    )
    return render_template('seeds/select_cultivar.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/select_packet', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_packet():
    """Select a packet to load on another page.

    Request Args:
        dest: The route to redirect to after `Packet` is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectPacketForm()
    if form.validate_on_submit():
        return redirect(url_for(dest, pkt_id=form.packet.data))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_packet', dest=dest)
    )
    return render_template('seeds/select_packet.html',
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
def home():
    """Home page for seeds section."""
    indexes = Index.query.all()
    return render_template('seeds/home.html', indexes=indexes)


@seeds.route('/<idx_slug>')
def index(idx_slug=None):
    """Display an `Index`."""
    index = Index.query.filter_by(slug=idx_slug).one_or_none()
    if index is not None:
        crumbs = (
            cblr.crumble('home', 'Home'),
            cblr.crumble('index', index.header, idx_slug=index.slug)
        )
        return render_template('seeds/index.html',
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
        individuals = [cv for cv in cn.cultivars if not cv.section]
        count = len([cv for cv in cn.cultivars if cv.public])
        crumbs = (
            cblr.crumble('home', 'Home'),
            cblr.crumble('index', cn.index.header, idx_slug=idx_slug),
            cn.name
        )
        sections = [s for s in cn.sections if not s.parent]
        featured = [c for c in cn.cultivars if c.featured]
        # TMP
        print(cn.name)
        print('Total cultivars: {0}'.format(len(cn.cultivars)))
        print('Active cultivars: {0}'.format(len([(c for c in cn.cultivars
                                                   if c.active)])))
        print('In stock cultivars: {0}'.format(len([(c for c in cn.cultivars
                                                     if c.in_stock)])))
        return render_template('seeds/common_name.html',
                               featured=featured,
                               sections=sections,
                               individuals=individuals,
                               cn=cn,
                               count=count,
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
            # TODO: Breadcrumbs
            return render_template('seeds/cultivar.html',
                                   idx_slug=idx_slug,
                                   cn_slug=cn_slug,
                                   # crumbs=crumbs,
                                   cultivar=cv)
    abort(404)


@seeds.route('flip_featured/<cv_id>')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_featured(cv_id):
    """Toggle 'featured' status of given `Cultivar`."""
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    if cv.featured:
        cv.featured = False
        flash('\'{0}\' will no longer be featured on its common name\'s page.'
              .format(cv.fullname))
    else:
        cv.featured = True
        flash('\'{0}\' will now be featured on its common name\'s page.'
              .format(cv.fullname))
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))


@seeds.route('/flip_in_stock/<cv_id>')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_in_stock(cv_id):
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


@seeds.route('/flip_active/<cv_id>')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def flip_active(cv_id):
    """Reverse active status of given cultivar."""
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    if cv.active:
        flash('\'{0}\' has been set as inactive.'.
              format(cv.fullname))
        cv.active = False
    else:
        flash('\'{0}\' has been set as active.'.
              format(cv.fullname))
        cv.active = True
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))


@seeds.route('/flip_visible/<cv_id>')
def flip_visible(cv_id):
    """Reverse visible status of given cultivar."""
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    if cv.visible:
        cv.visible = False
        flash('\'{0}\' is no longer visible on auto-generated pages.'
              .format(cv.fullname))
    else:
        cv.visible = True
        flash('\'{0}\' is now visible on auto-generated pages.'
              .format(cv.fullname))
    db.session.commit()
    return redirect(request.args.get('next') or url_for('seeds.manage'))

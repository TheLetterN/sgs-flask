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

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
)
from flask_login import login_required

from app import db, format_ship_date, list_to_english, Permission
from app.breadcrumbs import Crumbler
from app.decorators import permission_required
from app.pending import Pending
from app.redirects import Redirect, RedirectsFile
from . import seeds
from ..lastcommit import LastCommit
from app.db_helpers import dbify
from app.seeds.models import (
    BulkCategory,
    BulkItem,
    BulkSeries,
    CommonName,
    Cultivar,
    Image,
    Index,
    Packet,
    Section,
    USDollar
)
from app.seeds.forms import (
    AddBulkCategoryForm,
    AddBulkItemForm,
    AddBulkSeriesForm,
    AddCommonNameForm,
    AddIndexForm,
    AddPacketForm,
    AddRedirectForm,
    AddCultivarForm,
    AddSectionForm,
    EditBulkCategoryForm,
    EditBulkItemForm,
    EditBulkSeriesForm,
    EditCommonNameForm,
    EditCultivarForm,
    EditIndexForm,
    EditPacketForm,
    EditSectionForm,
    EditShipDateForm,
    RemoveIndexForm,
    RemoveCommonNameForm,
    RemoveObjectForm,
    RemovePacketForm,
    RemoveSectionForm,
    RemoveCultivarForm,
    SelectObjectForm
)


cblr = Crumbler('seeds')


MODELS = {
 'Bulk Category': BulkCategory,
 'Bulk Item': BulkItem,
 'Bulk Series': BulkSeries,
 'Common Name': CommonName,
 'Cultivar': Cultivar,
 'Packet': Packet,
 'Section': Section,
 'Index': Index
}


ADD_ROUTES = (
    ('manage', 'Manage Seeds'),
    'add_index',
    'add_common_name',
    'add_section',
    'add_cultivar',
    'add_packet'
)


EDIT_ROUTES = (
    ('manage', 'Manage Seeds'),
    'edit_index',
    'edit_common_name',
    'edit_section',
    'edit_cultivar',
    'edit_packet'
)


REMOVE_ROUTES = (
    ('manage', 'Manage Seeds'),
    'remove_index',
    'remove_common_name',
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


def request_kwargs():
    """Return a normal `dict` of request.args."""
    return {k: request.args.get(k) for k in request.args}


def origin():
    """Get the 'origin' request arg if present."""
    return request.args.get('origin')


def redirect_after_submit(*urls):
    """Redirect to origin or first passed arg that exists."""
    try:
        return redirect(next(u for u in urls if u))
    except StopIteration:
        if request.referrer:
            return redirect(request.referrer)
        else:
            return redirect(request.full_path)


def flash_all(messages, category='message'):
    if category == 'message':
        if len(messages) > 2:
            start = messages.pop(0)
            end = messages.pop()
            start = '<span>{}</span>'.format(start)
            end = '<span>{}</span>'.format(end)
            msgs = ['  <li>{}</li>'.format(m) for m in messages]
            msgs.insert(0, start)
            msgs.insert(1, '<ul class="flashed_list">')
            msgs.append('</ul>')
            msgs.append(end)
            flash('\n'.join(msgs), category)
        else:
            for message in messages:
                flash(message, category)
    else:
        for message in messages:
            flash(message, category)


def edit_optional_data(field, obj, attr, messages):
    """Edit a column that may contain no data.
    
    Attributes:
        field: The form to get data from.
        obj: The object to edit.
        attr: The attribute of the object to edit as a string.
        messages: A messages list to append message to.
    """
    edited = False
    if field.data:
        if getattr(obj, attr) != field.data:
            edited = True
            setattr(obj, attr, field.data)
            messages.append(
                '{} changed to: {}'.format(field.label.text, field.data)
            )
    elif getattr(obj, attr) is not None:  # Also remove blank strings.
            edited = True
            setattr(obj, attr, None)
            messages.append('{} cleared.'.format(field.label.text))
    return edited


def redirect_warning(old_path, links):
    """Generate a message warning that a redirect should be created.

    Args:
        old_path: The path that has been rendered invalid.
        links: A link or links to forms to add possible redirects.

    Returns:
        Markup: A string containing a warning that a redirect should be added.
    """
    return ('Warning: the path "{0}" is no longer valid. You may wish to '
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


# Image functions
def relative_to_static(filename):
    """Return filename with path to static removed."""
    return filename.replace(
        current_app.config.get('STATIC_FOLDER'), ''
    ).strip('/')


def add_thumbnail(form, obj, messages):
    """Add a thumbnail to the given object.

    Args:
        form: A form with `thumbnail` and `thumbnail_filename` fields.
        obj: The object to add the thumbnail to.
        messages: The list to append messages to.
    """
    if form.thumbnail.data:
        obj.thumbnail = Image.with_upload(
            filename=form.thumbnail_filename.data,
            upload=form.thumbnail.data
        )
        messages.append(
            'Thumbnail uploaded to: app/static/{}'
            .format(obj.thumbnail.filename)
        )


def edit_thumbnail(form, obj, messages):
    """Edit a thumbnail based on a new upload.

    Args:
        field: The FileField the new thumbnail is uploaded with.
        obj: The object with the thumbnail to edit.
        messages: The list to append messages to.

    Returns:
        bool: Whether or not the thumbnail was edited.
    """
    edited =False
    if not form.thumbnail_id.data:
        form.thumbnail_id.data = None
    if form.thumbnail_id.data != obj.thumbnail_id:
        edited = True
        if form.thumbnail_id.data:
            obj.thumbnail = next(
                i for i in obj.images if i.id == form.thumbnail_id.data
            )
            messages.append(
                'Thumbnail changed to: {}'.format(obj.thumbnail.filename)
            )
        else:
            obj.thumbnail = None
            messages.append('Thumbnail unset.')
    elif form.thumbnail.data:
        edited = True
        if (obj.thumbnail and
                obj.thumbnail.filename == form.thumbnail_filename.data):
            form.thumbnail.data.save(str(obj.thumbnail.path))
            messages.append('Thumbnail file replaced.')
        else:
            obj.thumbnail = Image.with_upload(
                filename=form.thumbnail_filename.data,
                upload=form.thumbnail.data
            )
            messages.append(
                'New thumbnail uploaded as "{}".'
                .format(obj.thumbnail.filename)
            )
    elif form.thumbnail_filename.data:
        try:
            if form.thumbnail_filename.data != obj.thumbnail.filename:
                edited = True
                obj.thumbnail.rename(form.thumbnail_filename.data)
                messages.append(
                    'Thumbnail renamed as "{}".'
                    .format(obj.thumbnail.filename)
                )
        except AttributeError:
            pass
    return edited


# Routes
@seeds.route('/_dbify')
def _dbify():
    text = request.args.get('text', '', type=str)
    print(text)
    return jsonify(result=dbify(text))


@seeds.route('/')
def home():
    """Home page."""
    return render_template('seeds/home.html')


@seeds.route('/<page>.html')
def static_html(page):
    """Display a page generated from html files in app/static/html"""
    try:
        return render_template('static/' + page + '.html', page=page)
    except TemplateNotFound:
        abort(404)


@seeds.route('/bulk')
def bulk():
    categories = BulkCategory.query.all()
    crumbs = (
        cblr.crumble('home', 'Home'),
        cblr.crumble('bulk', 'Bulk')
    )
    return render_template(
        'seeds/bulk.html',
        categories=categories,
        crumbs=crumbs
    )


@seeds.route('/bulk/<slug>.html')
def bulk_category(slug):
    category = BulkCategory.query.filter(
        BulkCategory.slug == slug
    ).one_or_none()
    if not category:
        abort(404)
    crumbs = (
        cblr.crumble('home', 'Home'),
        cblr.crumble('bulk', 'Bulk'),
        cblr.crumble('bulk_category', category.title, slug=slug)
    )
    return render_template(
        'seeds/bulk_category.html',
        crumbs=crumbs,
        category=category
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
        messages.append('Creating new index "{0}":'
                        .format(index.name))
        add_thumbnail(form, index, messages)
        index.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(index.slug))
        if form.description.data:
            index.description = form.description.data
            messages.append('Description set to: <p>{0}</p>'
                            .format(index.description))
        if form.pos.data is -1:
            index.set_position(1)
            messages.append('Will be listed before other indexes.')
        else:
            other = Index.query.get(form.pos.data)
            if other.position is None:
                other.auto_position()
            index.set_position(other.position + 1)
            messages.append('Will be listed after "{0}"'.format(other.name))
        db.session.commit()
        messages.append('New index "{0}" added to the database.'
                        .format(index.name))
        flash_all(messages)
        return redirect_after_submit(
            index.url,
            url_for('seeds.add_common_name', idx_id=index.id)
        )
    crumbs = cblr.crumble_route_group('add_index', ADD_ROUTES)
    return render_template('seeds/add_index.html', crumbs=crumbs, form=form)


@seeds.route('/add_common_name', methods=['GET', 'POST'])
@seeds.route('/add_common_name/<int:idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_common_name(idx_id=None):
    """Handle web interface for adding CommonName objects to the database."""
    idx = Index.query.get(idx_id) if idx_id else None
    if not idx:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_common_name',
            id_arg='idx_id',
            model='Index'
        ))

    form = AddCommonNameForm(index=idx)
    if form.validate_on_submit():
        messages = []
        cn = CommonName(name=form.name.data)
        db.session.add(cn)
        messages.append('Creating new common name "{0}" and adding it to '
                        'index "{1}":'.format(cn.name, idx.name))
        cn.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(cn.slug))
        if form.subtitle.data:
            cn.subtitle = form.subtitle.data
            messages.append('Subtitle set to: <p>{}</p>'.format(cn.subtitle))
        if form.list_as.data:
            cn.list_as = form.list_as.data
            messages.append('Will be listed as: <p>{}</p>'.format(cn.list_as))
        add_thumbnail(form, cn, messages)
        if form.botanical_names.data:
            cn.botanical_names = form.botanical_names.data
            messages.append(
                'Botanical names set to: <p>{}</p>'.format(cn.botanical_names)
            )
        if form.sunlight.data:
            cn.sunlight = form.sunlight.data
            messages.append(
                'Sunlight set to: <p>{}</p>'.format(cn.sunlight)
            )
        if form.description.data:
            cn.description = form.description.data
            messages.append('Description set to: <p>{0}</p>'
                            .format(cn.description))
        if form.instructions.data:
            cn.instructions = form.instructions.data
            messages.append('Planting instructions set to: <p>{0}</p>'
                            .format(cn.instructions))
        if form.pos.data == -1:
            idx.common_names.insert(0, cn)
            messages.append('Will be listed before other common names.')
        else:
            after = CommonName.query.get(form.pos.data)
            idx.common_names.insert(idx.common_names.index(after) + 1, cn)
            messages.append('Will be listed after "{0}".'
                            .format(after.name))
        if form.gw_common_names_ids.data:
            cn.gw_common_names = CommonName.from_ids(
                form.gw_common_names_ids.data
            )
            messages.append(
                'Grows with common names: {}.'
                .format(list_to_english(c.name for c in cn.gw_common_names))
            )
        if form.gw_cultivars_ids.data:
            cn.gw_cultivars = Cultivar.from_ids(
                form.gw_cultivars_ids.data
            )
            messages.append(
                'Grows with cultivars: {}.'
                .format(list_to_english(c.fullname for c in cn.gw_cultivars))
            )
        if form.gw_sections_ids.data:
            cn.gw_sections = Section.from_ids(form.gw_sections_ids.data)
            messages.append(
                'Grows with sections: {}.'
                .format(list_to_english(s.fullname for s in cn.gw_sections))
            )
        if form.visible.data:
            cn.visible = True
            messages.append('"{0}" is visible on auto-generated pages.'
                            .format(cn.name))
        else:
            cn.visible = False
            messages.append('"{0}" is not visible on auto-generated pages.'
                            .format(cn.name))
        db.session.commit()
        messages.append('New common name "{0}" added to the database.'
                        .format(cn.name))
        flash_all(messages)
        return redirect_after_submit(
            cn.url,
            url_for('seeds.add_section', cn_id=cn.id)
        )
    crumbs = cblr.crumble_route_group('add_common_name', ADD_ROUTES)
    return render_template('seeds/add_common_name.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_section', methods=['GET', 'POST'])
@seeds.route('/add_section/<int:cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_section(cn_id=None):
    """Add a section to the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_section',
            id_arg='cn_id',
            model='Common Name'
        ))

    form = AddSectionForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        section = Section(name=form.name.data)
        db.session.add(section)
        messages.append('Creating section "{0}" for common name "{1}":'
                        .format(section.name, cn.name))
        section.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(section.slug))
        if form.parent.data:
            parent = next(s for s in cn.sections if s.id == form.parent.data)
            parent.children.insert(len(parent.children), section)
            messages.append('Will be a subsection of: "{0}"'
                            .format(parent.name))
        if form.subtitle.data:
            section.subtitle = form.subtitle.data
            messages.append('Subtitle set to: "{0}"'
                            .format(section.subtitle))
        add_thumbnail(form, section, messages)
        if form.description.data:
            section.description = form.description.data
            messages.append('Description set to: <p>{0}</p>.'
                            .format(section.description))
        if form.pos.data == -1:
            cn.sections.insert(0, section)
            messages.append('Will be listed before other sections in "{0}".'
                            .format(cn.name))
        else:
            after = Section.query.get(form.pos.data)
            cn.sections.insert(cn.sections.index(after) + 1, section)
            messages.append('Will be listed after "{0}" in "{1}".'
                            .format(after.name, cn.name))
        db.session.commit()
        messages.append('New section "{0}" added to the database.'
                        .format(section.fullname))
        flash_all(messages)
        return redirect_after_submit(
            section.url,
            url_for('seeds.add_cultivar', cn_id=cn.id)
        )
    crumbs = cblr.crumble_route_group('add_section', ADD_ROUTES)
    return render_template('seeds/add_section.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_cultivar', methods=['GET', 'POST'])
@seeds.route('/add_cultivar/<int:cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_cultivar(cn_id=None):
    """Add a cultivar to the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_cultivar',
            id_arg='cn_id',
            model='Common Name'
        ))

    form = AddCultivarForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        cv = Cultivar(name=form.name.data, common_name=cn)
        db.session.add(cv)
        messages.append('Creating cultivar with short name "{0}" for common '
                        'name "{1}":'.format(cv.name, cn.name))
        cv.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(cv.slug))
        if form.subtitle.data:
            cv.subtitle = form.subtitle.data
            messages.append('Subtitle set to: "{0}"'.format(cv.subtitle))
        if form.botanical_name.data:
            cv.botanical_name = form.botanical_name.data
            messages.append('Botanical name set to: "{0}".'
                            .format(cv.botanical_name))
        if form.section.data:
            sec = Section.query.get(form.section.data)
            cv.sections = [sec]
            messages.append('Section set to: "{0}".'
                            .format(sec.name))
        if form.organic.data:
            cv.organic = True
            messages.append('Set as organic.')
        else:
            cv.organic = False
        if form.taxable.data:
            cv.taxable = True
            messages.append('Set as taxable in California.')
        else:
            cv.taxable = False
        add_thumbnail(form, cv, messages)
        if form.description.data:
            cv.description = form.description.data
            messages.append('Description set to: <p>{0}</p>'
                            .format(cv.description))
        if not cv.sections:
            try:
                cn.child_cultivars.remove(cv)
            except ValueError:
                pass
            if form.pos.data == -1:
                cn.child_cultivars.insert(0, cv)
                messages.append(
                    'Will be listed before other individual cultivars '
                    'belonging to "{0}".'.format(cn.name)
                )
            else:
                after = Cultivar.query.get(form.pos.data)
                cv.insert_after(after)
                messages.append(
                    'Will be listed after "{0}".'.format(after.fullname)
                )
        if form.gw_common_names_ids.data:
            cv.gw_common_names = CommonName.from_ids(
                form.gw_common_names_ids.data
            )
            messages.append(
                'Grows with common names: {}.'
                .format(list_to_english(c.name for c in cv.gw_common_names))
            )
        if form.gw_cultivars_ids.data:
            cv.gw_cultivars = Cultivar.from_ids(
                form.gw_cultivars_ids.data
            )
            messages.append(
                'Grows with cultivars: {}.'
                .format(list_to_english(c.fullname for c in cv.gw_cultivars))
            )
        if form.gw_sections_ids.data:
            cv.gw_sections = Section.from_ids(form.gw_sections_ids.data)
            messages.append(
                'Grows with sections/series: {}.'
                .format(list_to_english(s.fullname for s in cv.gw_sections))
            )
        if form.new_for.data:
            cv.new_for = form.new_for.data
            messages.append('Marked as new for: {}'.format(cv.new_for))
        if form.featured.data:
            cv.featured = True
            messages.append('"{0}" will be featured on its common '
                            'name\'s page.'.format(cv.fullname))
        if form.in_stock.data:
            cv.in_stock = True
            messages.append('"{0}" is in stock.'.format(cv.fullname))
        else:
            cv.in_stock = False
            messages.append('"{0}" is not in stock.'.format(cv.fullname))
        if form.active.data:
            cv.active = True
            messages.append('"{0}" is currently active.'.format(cv.fullname))
        else:
            cv.active = False
            messages.append('"{0}" is currently inactive.'
                            .format(cv.fullname))
        if form.visible.data:
            cv.visible = True
            messages.append('"{0}" will be visible in auto-generated pages.'
                            .format(cv.fullname))
        else:
            cv.visible = False
            messages.append('"{0}" will not be visible in auto-generated '
                            'pages, but it can still be used in custom pages.'
                            .format(cv.fullname))
        if form.open_pollinated.data:
            cv.open_pollinated = True
            messages.append('{} is open pollinated.'.format(cv.fullname))
        if form.maturation.data:
            cv.maturation = form.maturation.data
            messages.append(
                'Maturation time set to: "{}".'.format(cv.maturation)
            )
        db.session.commit()
        messages.append('New cultivar "{0}" added to the database.'
                        .format(cv.fullname))
        flash_all(messages)
        return redirect_after_submit(
            cv.url,
            url_for('seeds.add_packet', cv_id=cv.id)
        )
    crumbs = cblr.crumble_route_group('add_cultivar', ADD_ROUTES)
    return render_template('seeds/add_cultivar.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/add_packet', methods=['GET', 'POST'])
@seeds.route('/add_packet/<int:cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_packet(cv_id=None):
    """Add a packet to the database."""
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if not cv:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_packet',
            id_arg='cv_id',
            model='Cultivar'
        ))
    form = AddPacketForm(cultivar=cv)
    if form.validate_on_submit():
        messages = []
        packet = Packet(sku=form.sku.data.strip(), cultivar=cv)
        db.session.add(packet)
        messages.append('Creating packet with SKU #{0} for cultivar "{1}":'
                        .format(packet.sku, cv.fullname))
        packet.product_name = form.product_name.data
        messages.append(
            'Product name set to: "{}".'.format(packet.product_name)
        )
        packet.price = form.price.data
        messages.append('Price set to: ${0}.'.format(packet.price))
        packet.amount = form.amount.data
        messages.append('Amount of seeds: {}'.format(packet.amount))
        db.session.commit()
        messages.append('New packet with SKU #{0} added to the database.'
                        .format(packet.sku))
        flash_all(messages)
        return redirect_after_submit(cv.url)
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
        return redirect(origin() or url_for('seeds.manage'))
    crumbs = (cblr.crumble('manage', 'Manage Seeds'),
              cblr.crumble('add_redirect'))
    return render_template('seeds/add_redirect.html', crumbs=crumbs, form=form)


@seeds.route('/add_bulk_category', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def add_bulk_category():
    form = AddBulkCategoryForm()
    if form.validate_on_submit():
        messages = []
        bc = BulkCategory(name=form.name.data)
        db.session.add(bc)
        messages.append('Creating new bulk category "{}":'
                        .format(bc.name))
        bc.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(bc.slug))
        if form.list_as.data:
            bc.list_as = form.list_as.data
            messages.append('Will be listed as "{}".'.format(bc.list_as))
        if form.subtitle.data:
            bc.subtitle = form.subtitle.data
            messages.append('Subtitle set to "{}".'.format(bc.subtitle))
        add_thumbnail(form, bc, messages)
        db.session.commit()
        flash_all(messages)
        return redirect_after_submit(bc.url)
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('add_bulk_category')
    )
    return render_template(
        'seeds/add_bulk_category.html',
        crumbs=crumbs,
        form=form
    )


@seeds.route('/add_bulk_series', methods=['GET', 'POST'])
@seeds.route('/add_bulk_series/<int:cat_id>', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def add_bulk_series(cat_id=None):
    cat = BulkCategory.query.get(cat_id) if cat_id else None
    if not cat:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_bulk_series',
            id_arg='cat_id',
            model='Bulk Category'
        ))
    form = AddBulkSeriesForm(category=cat)
    if form.validate_on_submit():
        messages = []
        bs = BulkSeries(name=form.name.data, category=cat)
        db.session.add(bs)
        messages.append('Creating new bulk series "{}":'.format(bs.name))
        bs.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(bs.slug))
        if form.subtitle.data:
            bs.subtitle = form.subtitle.data
            messages.append('Subtitle set to "{}".'.format(bs.subtitle))
        add_thumbnail(form, bs, messages)
        db.session.commit()
        flash_all(messages)
        return redirect_after_submit(bs.url)
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('add_bulk_series')
    )
    return render_template('seeds/add_bulk_series.html', form=form)


@seeds.route('/add_bulk_item', methods=['GET', 'POST'])
@seeds.route('/add_bulk_item/<int:cat_id>', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def add_bulk_item(cat_id=None):
    cat = BulkCategory.query.get(cat_id) if cat_id else None
    if not cat:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.add_bulk_item',
            id_arg='cat_id',
            model='Bulk Category'
        ))
    form = AddBulkItemForm(category=cat)
    if form.validate_on_submit():
        messages = []
        bi = BulkItem(name=form.name.data, category=cat)
        db.session.add(bi)
        messages.append('Creating new bulk item "{}":'.format(bi.name))
        if form.series_id.data:
            bi.series = BulkSeries.query.get(form.series_id.data)
            messages.append('Series set to "{}".'.format(bi.series.name))
        bi.slug = form.slug.data
        messages.append('Slug set to "{}".'.format(bi.slug))
        bi.product_name = form.product_name.data
        messages.append('Product name set to "{}".'.format(bi.product_name))
        bi.sku = form.sku.data
        messages.append('SKU set to "{}".'.format(bi.sku))
        bi.price = form.price.data
        messages.append('Price set to ${}.'.format(bi.price))
        bi.taxable = True if form.taxable.data else False
        if bi.taxable:
            messages.append('Set as taxable.')
        else:
            messages.append('Set as not taxable.')
        add_thumbnail(form, bi, messages)
        db.session.commit()
        flash_all(messages)
        return redirect_after_submit(bi.url)
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('add_bulk_item')
    )
    return render_template(
        'seeds/add_bulk_item.html',
        crumbs=crumbs,
        form=form
    )


@seeds.route('/edit_index', methods=['GET', 'POST'])
@seeds.route('/edit_index/<int:idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_index(idx_id=None):
    index = Index.query.get(idx_id) if idx_id else None
    if index is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_index',
            id_arg='idx_id',
            model='Index'
        ))

    form = EditIndexForm(obj=index)
    if form.validate_on_submit():
        edited = False
        messages = []
        old_slug = index.slug
        messages.append('Editing index "{0}":'.format(index.name))
        if form.name.data != index.name:
            edited = True
            index.name = form.name.data
            messages.append('Name changed to: "{0}".'.format(index.name))
        if form.slug.data != index.slug:
            edited = True
            index.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(index.slug))
        edited = edit_thumbnail(form, index, messages) or edited
        edited = edit_optional_data(
            form.description,
            index,
            'description',
            messages
        ) or edited
        prev = index.previous
        if prev and form.pos.data == -1:  # Moving to first position.
            edited = True
            index.set_position(1)
            messages.append('Will be listed before all other indexes.')
        elif form.pos.data != -1 and (not prev or form.pos.data != prev.id):
            edited = True
            other = Index.query.get(form.pos.data)
            if not other.position:
                other.auto_position()
            index.set_position(other.position + 1)
            messages.append('Will be listed after "{0}".'.format(other.name))
        if edited:
            db.session.commit()
            messages.append('Changes to "{0}" committed to the database.'
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
            return redirect_after_submit(index.url)
        else:
            messages.append('No changes to "{0}" were made.'
                            .format(index.name))
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = cblr.crumble_route_group('edit_index', EDIT_ROUTES)
    return render_template('seeds/edit_index.html',
                           crumbs=crumbs,
                           form=form,
                           index=index)


@seeds.route('/edit_common_name', methods=['GET', 'POST'])
@seeds.route('/edit_common_name/<int:cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_common_name(cn_id=None):
    """"Edit a common name stored in the database.

    Args:
        cn_id: The id number of the common name to edit.
    """
    cn = CommonName.query.get(cn_id) if cn_id else None
    if not cn:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_common_name',
            id_arg='cn_id',
            model='Common Name'
        ))
    form = EditCommonNameForm(obj=cn)
    dest = None
    if form.validate_on_submit():
        edited = False
        messages = []
        warnings = []
        old_slugs = {'cn': cn.slug, 'idx': cn.index.slug}
        idx = cn.index
        messages.append('Editing common name "{0}":'.format(cn.name))
        if form.index_id.data != cn.index.id:
            edited = True
            new_idx = Index.query.get(form.index_id.data)
            idx.common_names.remove(cn)
            # This will insert cn at the end of new_idx.common_names.
            # This is done instead of appending to ensure cn.idx_pos is set
            # correctly.
            new_idx.common_names.insert(len(new_idx.common_names), cn)
            messages.append('Index changed to: "{0}".'.format(cn.index.name))
        if form.name.data != cn.name:
            edited = True
            cn.name = form.name.data
            messages.append('Name changed to: "{0}".'.format(cn.name))
        if form.slug.data != cn.slug:
            edited = True
            cn.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(cn.slug))
        if form.list_as.data != cn.list_as:
            edited = True
            cn.list_as = form.list_as.data
            messages.append('Will now be listed as: "{}".'.format(cn.list_as))
        edited = edit_optional_data(
            form.subtitle,
            cn,
            'subtitle',
            messages
        ) or edited
        edited = edit_thumbnail(form, cn, messages) or edited
        edited = edit_optional_data(
            form.botanical_names,
            cn,
            'botanical_names',
            messages
        ) or edited
        edited = edit_optional_data(
            form.sunlight,
            cn,
            'sunlight',
            messages
        ) or edited 
        edited = edit_optional_data(
            form.description,
            cn,
            'description',
            messages
        ) or edited
        edited = edit_optional_data(
            form.instructions,
            cn,
            'instructions',
            messages
        ) or edited
        if idx is cn.index:
            cns = idx.common_names
            cn_index = cns.index(cn)
            if form.pos.data == -1 and cn_index != 0:
                edited = True
                cns.insert(0, cns.pop(cn_index))
                messages.append('Will now be listed first.')
            elif (form.pos.data != -1 and
                    (cn_index == 0 or form.pos.data != cns[cn_index - 1].id)):
                edited = True
                prev = next(c for c in cns if c.id == form.pos.data)
                cn.move_after(prev)
                messages.append('Will now be listed after "{0}".'
                                .format(prev.name))
        else:
            dest = url_for('seeds.edit_common_name', cn_id=cn.id)
            warnings.append(
                'Due to changing {0}\'s index to "{1}", it will be listed '
                'last under that index. You will need to edit it again if you '
                'want it in a different position.'
                .format(cn.name, cn.index.name)
            )
        if set(form.gw_common_names_ids.data) != set(cn.gw_common_names_ids):
            edited = True
            cn.gw_common_names = CommonName.from_ids(
                form.gw_common_names_ids.data
            )
            if cn.gw_common_names:
                messages.append(
                    'Grows with common names: {}.'
                    .format(
                        list_to_english(c.name for c in cn.gw_common_names)
                    )
                )
            else:
                messages.append('Grows with common names cleared.')
        if set(form.gw_sections_ids.data) != set(cn.gw_sections_ids):
            edited = True
            cn.gw_sections = Section.from_ids(form.gw_sections_ids.data)
            if cn.gw_sections:
                messages.append(
                    'Grows with sections/series: {}.'
                    .format(
                        list_to_english(s.fullname for s in cn.gw_sections)
                    )
                )
            else:
                messages.append('Grows with sections/series cleared.')
        if set(form.gw_cultivars_ids.data) != set(cn.gw_cultivars_ids):
            edited = True
            cn.gw_cultivars = Cultivar.from_ids(form.gw_cultivars_ids.data)
            if cn.gw_cultivars:
                messages.append(
                    'Grows with cultivars: {}.'
                    .format(
                        list_to_english(c.fullname for c in cn.gw_cultivars)
                    )
                )
            else:
                messages.append('Grows with cultivars cleared.')
        if edited:
            messages.append('Changes to "{0}" committed to the database.'
                            .format(cn.name))
            db.session.commit()
            flash_all(messages)

            if old_slugs['cn'] != cn.slug or old_slugs['idx'] != cn.index.slug:
                warnings += redirect_common_name_warnings(
                    cn,
                    old_idx_slug=old_slugs['idx'],
                    old_cn_slug=old_slugs['cn'],
                    new_idx_slug=cn.index.slug,
                    new_cn_slug=cn.slug
                )
                if warnings:
                    flash_all(warnings, 'warning')

            return redirect_after_submit(cn.url)
        else:
            messages.append('No changes to "{0}" were made.'.format(cn.name))
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = cblr.crumble_route_group('edit_common_name', EDIT_ROUTES)
    return render_template('seeds/edit_common_name.html',
                           crumbs=crumbs,
                           form=form,
                           cn=cn)


@seeds.route('/edit_section', methods=['GET', 'POST'])
@seeds.route('/edit_section/<int:section_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_section(section_id=None):
    """Display page for editing a Section from the database."""
    section = Section.query.get(section_id) if section_id else None
    if section is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_section',
            id_arg='section_id',
            model='Section'
        ))
    form = EditSectionForm(obj=section)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing section "{0}":'.format(section.name))
        old_cn = section.common_name
        if form.common_name_id.data != section.common_name.id:
            edited = True
            section.common_name = CommonName.query.get(
                form.common_name_id.data
            )
            messages.append('Common name changed to: "{0}".'
                            .format(section.common_name.name))
        old_parent = section.parent
        if form.parent_id.data == 0:
            form.parent_id.data = None
        if (old_cn is section.common_name and
                form.parent_id.data != section.parent_id):
            edited = True
            if form.parent_id.data:
                parent = next(
                    s for s in section.common_name.sections if
                    s.id == form.parent_id.data
                )
                parent.children.insert(len(parent.children), section)
                messages.append('Will now be a subcategory of: "{0}"'
                                .format(section.parent.name))
            else:
                section.parent = None
                messages.append('Will no longer be a subcategory.')
        old_name = section.name
        if form.name.data != section.name:
            edited = True
            section.name = form.name.data
            messages.append('Name changed to: "{0}"'.format(section.name))
        if form.slug.data != section.slug:
            edited = True
            section.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(section.slug))
        edited = edit_optional_data(
            form.subtitle,
            section,
            'subtitle',
            messages
        ) or edited
        edited = edit_thumbnail(form, section, messages) or edited
        edited = edit_optional_data(
            form.description,
            section,
            'description',
            messages
        ) or edited
        if section.common_name is old_cn and section.parent is old_parent:
            secs = section.parent_collection
            s_index = secs.index(section)
            if form.pos.data == -1 and s_index != 0:
                edited = True
                secs.insert(0, secs.pop(s_index))
                messages.append(
                    'Will now be listed first in its parent container.'
                )
            elif (form.pos.data != -1 and
                    (s_index == 0 or form.pos.data != secs[s_index - 1].id)):
                edited = True
                prev = next(s for s in secs if s.id == form.pos.data)
                section.move_after(prev)
                messages.append('Will now be listed after "{0}"'
                                .format(prev.name))
        if old_cn is not section.common_name:
            for cv in section.cultivars:
                if cv.common_name is not section.common_name:
                    old_cvname = cv.fullname
                    cv.common_name = section.common_name
                    messages.append('Common name for the cultivar "{0}" has '
                                    'been changed to: "{1}".'
                                    .format(old_cvname, cv.common_name.name))
        if edited:
            db.session.commit()
            messages.append('Changes to "{0}" committed to the database.'
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

            return redirect_after_submit(section.url)
        else:
            messages.append('No changes to "{0}" were made.'
                            .format(section.name))
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = cblr.crumble_route_group('edit_section', EDIT_ROUTES)
    return render_template('seeds/edit_section.html',
                           crumbs=crumbs,
                           form=form,
                           section=section)


@seeds.route('/edit_cultivar', methods=['GET', 'POST'])
@seeds.route('/edit_cultivar/<int:cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_cultivar(cv_id=None):
    """Edit a cultivar stored in the database."""
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if cv is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_cultivar',
            id_arg='cv_id',
            model='Cultivar'
        ))
    form = EditCultivarForm(obj=cv)
    if form.validate_on_submit():
        edited = False
        messages = []
        warnings = []
        messages.append('Editing cultivar "{0}":'.format(cv.fullname))
        old_slugs = {'cv': cv.slug,
                     'cn': cv.common_name.slug,
                     'idx': cv.common_name.index.slug}
        old_cn = cv.common_name
        if form.common_name_id.data != cv.common_name_id:
            edited = True
            cv.common_name = CommonName.query.get(form.common_name_id.data)
            messages.append('Common name changed to: "{0}".'
                            .format(cv.common_name.name))
        if cv.name != form.name.data:
            edited = True
            cv.name = form.name.data
            messages.append('(Short) Name changed to: "{0}".'
                            .format(cv.name))
        if form.slug.data != cv.slug:
            edited = True
            cv.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(cv.slug))
        old_parent_sec = cv.parent_section
        edited = edit_optional_data(
            form.subtitle,
            cv,
            'subtitle',
            messages
        ) or edited
        edited = edit_optional_data(
            form.botanical_name,
            cv,
            'botanical_name',
            messages
        ) or edited
        if not form.section_id.data:
            form.section_id.data = None
        if form.section_id.data != cv.section_id:
            edited = True
            if form.section_id.data:
                sec = Section.query.get(form.section_id.data)
                cv.sections = [sec]
                messages.append('Section changed to: "{0}".'
                                .format(sec.name))
            else:
                cv.sections = []
                messages.append('Section cleared.')
        if form.organic.data != cv.organic:
            edited = True
            if form.organic.data:
                cv.organic = True
                messages.append('Set as organic.')
            else:
                cv.organic = False
                messages.append('No longer set as organic.')
        if form.taxable.data != cv.taxable:
            edited = True
            if form.taxable.data:
                cv.taxable = True
                messages.append('Set as organic.')
            else:
                cv.taxable = False
                messages.append('No longer set as taxable.')
        edited = edit_thumbnail(form, cv, messages) or edited
        edited = edit_optional_data(
            form.description,
            cv,
            'description',
            messages
        ) or edited
        if old_cn is cv.common_name and old_parent_sec is cv.parent_section:
            pc = cv.parent_collection
            cv_index = pc.index(cv)
            if form.pos.data == -1 and cv_index != 0:
                edited = True
                pc.insert(0, pc.pop(cv_index))
                messages.append(
                    'Will now be listed first in its parent container.'
                )
            elif (form.pos.data != -1 and
                    (cv_index == 0 or form.pos.data != pc[cv_index - 1].id)):
                edited = True
                prev = next(cv for cv in pc if cv.id == form.pos.data)
                cv.move_after(prev)
                messages.append('Will now be listed after "{0}".'
                                .format(prev.fullname))
        if set(form.gw_common_names_ids.data) != set(cv.gw_common_names_ids):
            edited = True
            cv.gw_common_names = CommonName.from_ids(
                form.gw_common_names_ids.data
            )
            if cv.gw_common_names:
                messages.append(
                    'Grows with common names: {}.'
                    .format(
                        list_to_english(c.name for c in cv.gw_common_names)
                    )
                )
            else:
                messages.append('Grows with common names cleared.')
        if set(form.gw_sections_ids.data) != set(cv.gw_sections_ids):
            edited = True
            cv.gw_sections = Section.from_ids(
                form.gw_sections_ids.data
            )
            if cv.gw_sections:
                messages.append(
                    'Grows with sections/series: {}.'
                    .format(list_to_english(s.name for s in cv.gw_sections))
                )
            else:
                messages.append('Grows with sections/series cleared.')
        if set(form.gw_cultivars_ids.data) != set(cv.gw_cultivars_ids):
            edited = True
            cv.gw_cultivars = Cultivar.from_ids(form.gw_cultivars_ids.data)
            if cv.gw_cultivars:
                messages.append(
                    'Grows with cultivars: {}.'
                    .format(
                        list_to_english(c.fullname for c in cv.gw_cultivars)
                    )
                )
            else:
                messages.append('Grows with cultivars cleared.')
        edited = edit_optional_data(
            form.new_for,
            cv,
            'new_for',
            messages
        ) or edited
        if form.featured.data and not cv.featured:
            edited = True
            cv.featured = True
            messages.append('"{0}" will now be featured on its common '
                            'name\'s page.'.format(cv.fullname))
        elif not form.featured.data and cv.featured:
            edited = True
            cv.featured = False
            messages.append('"{0}" will no longer be featured on its common '
                            'name\'s page.'.format(cv.fullname))

        if form.in_stock.data and not cv.in_stock:
            edited = True
            cv.in_stock = True
            messages.append('"{0}" is now in stock.'.format(cv.fullname))
        elif not form.in_stock.data and cv.in_stock:
            edited = True
            cv.in_stock = False
            messages.append('"{0}" is now out of stock.'
                            .format(cv.fullname))
        if form.active.data and not cv.active:
            edited = True
            cv.active = True
            messages.append('"{0}" is now active.'.format(cv.fullname))
        elif not form.active.data and cv.active:
            edited = True
            cv.active = False
            messages.append('"{0}" is no longer active.'
                            .format(cv.fullname))
        if form.visible.data and not cv.visible:
            edited = True
            cv.visible = True
            messages.append('"{0}" will now be visible on '
                            'auto-generated pages.'.format(cv.fullname))
        elif not form.visible.data and cv.visible:
            edited = True
            cv.visible = False
            messages.append('"{0}" will no longer be visible on '
                            'auto-generated pages.'.format(cv.fullname))
        if form.open_pollinated.data and not cv.open_pollinated:
            edited = True
            cv.open_pollinated = True
            messages.append('Set as open pollinated.')
        elif not form.open_pollinated.data and cv.open_pollinated:
            edited = True
            cv.open_pollinated = False
            messages.append('No longer set as open pollinated.')
        edited = edit_optional_data(
            form.maturation,
            cv,
            'maturation',
            messages
        ) or edited
        if edited:
            messages.append('Changes to "{0}" committed to the database.'
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
            return redirect_after_submit(cv.url)
        else:
            messages.append('No changes to "{0}" were made'
                            .format(cv.fullname))
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = cblr.crumble_route_group('edit_cultivar', EDIT_ROUTES)
    return render_template('seeds/edit_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/edit_packet', methods=['GET', 'POST'])
@seeds.route('/edit_packet/<int:pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_packet(pkt_id=None):
    packet = Packet.query.get(pkt_id) if pkt_id else None
    if packet is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_packet',
            id_arg='pkt_id',
            model='Packet'
        ))

    form = EditPacketForm(obj=packet)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing packet "{0}".'.format(packet.info))
        if form.cultivar_id.data != packet.cultivar_id:
            edited = True
            packet.cultivar = Cultivar.query.get(form.cultivar_id.data)
            messages.append('Cultivar changed to: "{0}".'
                            .format(packet.cultivar.fullname))
        if form.sku.data != packet.sku:
            edited = True
            packet.sku = form.sku.data
            messages.append('SKU changed to: "{0}".'.format(packet.sku))
        dec_p = USDollar.usd_to_decimal(form.price.data)
        if dec_p != packet.price:
            edited = True
            packet.price = dec_p
            messages.append('Price changed to: "${0}".'.format(packet.price))
        if form.amount.data != packet.amount:
            edited = True
            packet.amount = form.amount.data
            messages.append('Amount changed to: {}'.format(packet.amount))
        if edited:
            db.session.commit()
            messages.append('Changes to "{0}" committed to the database.'
                            .format(packet.info))
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('No changes to "{0}" were made.'
                            .format(packet.info))
            flash_all(messages)
            return redirect(url_for('seeds.edit_packet', pkt_id=pkt_id))
    crumbs = cblr.crumble_route_group('edit_packet', EDIT_ROUTES)
    return render_template('seeds/edit_packet.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/edit_bulk_category', methods=['GET', 'POST'])
@seeds.route('/edit_bulk_category/<int:cat_id>', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def edit_bulk_category(cat_id=None):
    bc = BulkCategory.query.get(cat_id) if cat_id else None
    if not bc:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_bulk_category',
            id_arg='cat_id',
            model='Bulk Category'
        ))

    form = EditBulkCategoryForm(obj=bc)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing bulk category "{}".'.format(bc.name))
        if form.name.data != bc.name:
            edited = True
            bc.name = form.name.data
            messages.append('Name changed to "{}".'.format(bc.name))
        if form.slug.data != bc.slug:
            edited = True
            bc.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(bc.slug))
        edited = edit_optional_data(
            form.list_as,
            bc,
            'list_as',
            messages
        ) or edited
        edited = edit_optional_data(
            form.subtitle,
            bc,
            'subtitle',
            messages
        ) or edited
        edited = edit_thumbnail(form, bc, messages) or edited
        if edited:
            db.session.commit()
            messages.append(
                'Changes to "{}" commited to database.'.format(bc.name)
            )
            return redirect_after_submit(bc.url)
        else:
            messages.append('No changes were made.')
            flash_all(messages)
            return redirect(request.path)

    return render_template(
        'seeds/edit_bulk_category.html',
        category=bc, 
        form=form
    )


@seeds.route('/edit_bulk_series', methods=['GET', 'POST'])
@seeds.route('/edit_bulk_series/<int:ser_id>', methods=['GET', 'POST'])
def edit_bulk_series(ser_id=None):
    """Edit a `BulkSeries`."""
    bs = BulkSeries.query.get(ser_id) if ser_id else None
    if not bs:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_bulk_series',
            id_arg='ser_id',
            model='Bulk Series'
        ))
    form = EditBulkSeriesForm(obj=bs)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing bulk series "{}"...'.format(bs.name))
        if form.category_id.data != bs.category_id:
            edited = True
            bs.category = BulkCategory.query.get(form.category_id.data)
            messages.append(
                'Category changed to "{}".'.format(bs.category.name)
            )
        if form.name.data != bs.name:
            edited = True
            bs.name = form.name.data
            messages.append('Name changed to "{}".'.format(bs.name))
        if form.slug.data != bs.slug:
            edited = True
            bs.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(bs.slug))
        edited = edit_optional_data(
            field=form.subtitle,
            obj=bs,
            attr='subtitle',
            messages=messages
        ) or edited
        edited = edit_thumbnail(form, bs, messages) or edited
        if edited:
            db.session.commit()
            messages.append(
                'Changes to "{}" committed to the database.'.format(bs.name)
            )
            flash_all(messages)
            return redirect_after_submit(bs.url)
        else:
            messages.append('No changes to "{}" were made.'.format(bs.name))
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('edit_bulk_series')
    )
    return render_template(
        'seeds/edit_bulk_series.html',
        crumbs=crumbs,
        form=form
    )


@seeds.route('/edit_bulk_item', methods=['GET', 'POST'])
@seeds.route('/edit_bulk_item/<int:item_id>', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def edit_bulk_item(item_id=None):
    item = BulkItem.query.get(item_id) if item_id else None
    if not item:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.edit_bulk_item',
            id_arg='item_id',
            model='Bulk Item'
        ))
    form = EditBulkItemForm(obj=item)
    if form.validate_on_submit():
        edited = False
        messages = []
        messages.append('Editing bulk item "{}"...'.format(item.name))
        if form.category_id.data != item.category_id:
            edited = True
            item.category = BulkCategory.query.get(form.category_id.data)
            messages.append(
                'Category changed to "{}".'.format(item.category.name)
            )
        if not form.series_id.data:
            form.series_id.data = None
        if form.series_id.data != item.series_id:
            edited = True
            if form.series_id.data:
                item.series = BulkSeries.query.get(form.series_id.data)
                messages.append(
                    'Series changed to "{}".'.format(item.series.name)
                )
            else:
                item.series = None
                messages.append('Series cleared.')
        if form.name.data != item.name:
            edited = True
            item.name = form.name.data
            messages.append('Name changed to "{}".'.format(item.name))
        if form.slug.data != item.slug:
            edited = True
            item.slug = form.slug.data
            messages.append('Slug changed to "{}".'.format(item.slug))
        if form.product_name.data != item.product_name:
            edited = True
            item.product_name = form.product_name.data
            messages.append(
                'Product name changed to "{}".'.format(item.product_name)
            )
        if form.sku.data != item.sku:
            edited = True
            item.sku = form.sku.data
            messages.append('SKU changed to "{}".'.format(item.sku))
        dec_p = USDollar.usd_to_decimal(form.price.data)
        if dec_p != item.price:
            edited = True
            item.price = dec_p
            messages.append('Price changed to ${}.'.format(item.price))
        if form.taxable.data and not item.taxable:
            edited = True
            item.taxable = True
            messages.append('Set as taxable.')
        elif not form.taxable.data and item.taxable:
            edited = True
            item.taxable = False
            messages.append('No longer set as taxable.')
        edited = edit_thumbnail(form, item, messages) or edited
        if edited:
            db.session.commit()
            messages.append(
                'Changes to "{}" committed to database.'.format(item.name)
            )
            flash_all(messages)
            return redirect_after_submit(item.url)
        else:
            messages.append('No changes were made.')
            flash_all(messages)
            return redirect(request.full_path)
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('edit_bulk_item')
    )
    return render_template(
        'seeds/edit_bulk_item.html',
        crumbs=crumbs,
        form=form
    )


def migrate_cultivars(cn, other):
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
                'Could not move "{0}" because a cultivar with the same name '
                'and section already exists! Click <a href="{1}">here</a> if '
                'you want to edit it, or <a href="{2}">here</a> if you want '
                'to remove it.'
                .format(cv.fullname,
                        url_for('seeds.edit_cultivar', cv_id=cv.id),
                        url_for('seeds.remove_cultivar', cv_id=cv.id))
            )
    return warnings


def migrate_common_names(idx, other):
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
                'Could not move "{0}" because a common name with the same '
                'name already belongs to "{1}". Instead of moving it, its '
                'children (section, and cultivars) will be '
                'moved to the one belonging to "{1}" if possible.'
                .format(cn.name, other.name)
            )
            other_cn = next((
                c for c in other.common_names if c.name == cn.name), None
            )
            warnings += migrate_sections(cn, other_cn)
            warnings += migrate_cultivars(cn, other_cn)
    return warnings


def migrate_sections(cn, other):
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
                'Could not move "{0}" because a section with the same name '
                'already belongs to "{1}". Click <a href="{2}">here</a> if '
                'you would like to edit "{0}", or <a href="{3}">here</a> '
                'if you would like to remove it.'
                .format(sec.name,
                        other.name,
                        url_for('seeds.edit_section', section_id=sec.id),
                        url_for('seeds.remove_section', section_id=sec.id))
            )
    return warnings


@seeds.route('/remove_object', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def remove_object():
    model = request.args.get('model')
    if not model:
        flash(
            'Error: No model was specified to remove an item from!',
            category='error'
        )
        return redirect(request.referrer or url_for('seeds.manage'))
    select_url = url_for(
        'seeds.select_object',
        dest='seeds.remove_object',
        id_arg='obj_id',
        model=model
        )
    try:
        obj_id = int(request.args.get('obj_id'))
    except TypeError:
        return redirect(select_url)
    obj = MODELS[model].query.get(obj_id)
    if not obj:
        flash('No {} could be found with the id: {}'.format(model, obj_id))
        return redirect(select_url)
    name = obj.name
    form = RemoveObjectForm()
    if form.validate_on_submit():
        if form.verify_removal:
            db.session.delete(obj)
            db.session.commit()
            flash('{} removed from database.'.format(name))
            return redirect(url_for('seeds.manage'))
    return render_template(
        'seeds/remove_object.html',
        form=form,
        model=model,
        name=name
    )


@seeds.route('/remove_index', methods=['GET', 'POST'])
@seeds.route('/remove_index/<int:idx_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_index(idx_id=None):
    """Remove an index from the database."""
    index = Index.query.get(idx_id) if idx_id else None
    if index is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.remove_index',
            id_arg='idx_id',
            model='Index'
        ))
    form = RemoveIndexForm(index=index)
    if form.validate_on_submit():
        messages = []
        warnings = []
        if form.verify_removal.data:
            messages.append('Removing index "{0}":'.format(index.name))
            if form.move_to.data:
                new_index = Index.query.get(form.move_to.data)
                warnings += redirect_index_warnings(
                    index,
                    old_idx_slug=index.slug,
                    new_idx_slug=new_index.slug
                )
                warnings += migrate_common_names(index, new_index)
            else:
                warnings.append(
                    'Warning: CommonNames belonging to "{}" have been '
                    'orphaned.'.format(index.name)
                )
            index.clean_positions(remove_self=True)
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
                            'box labeled "Yes".')
            flash_all(messages)
            return redirect(url_for('seeds.remove_index',
                                    idx_id=idx_id))
    crumbs = cblr.crumble_route_group('remove_index', REMOVE_ROUTES)
    return render_template('seeds/remove_index.html',
                           crumbs=crumbs,
                           form=form)


@seeds.route('/remove_common_name', methods=['GET', 'POST'])
@seeds.route('/remove_common_name/<int:cn_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_common_name(cn_id=None):
    """Remove a common name from the database."""
    cn = CommonName.query.get(cn_id) if cn_id else None
    if cn is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.remove_common_name',
            id_arg='cn_id',
            model='Common Name'
        ))
    form = RemoveCommonNameForm(cn=cn)
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing common name "{0}":'.format(cn.name))
            new_cn = CommonName.query.get(form.move_to.data)
            if cn.synonyms:
                cn.synonyms_string = None
                messages.append('Synonyms cleared.')
            try:
                for cv in cn.cultivars:
                    warnings.append(redirect_cultivar_warning(
                        cv,
                        old_cn_slug=cn.slug,
                        new_cn_slug=new_cn.slug
                    ))
            except NotEnabledError:
                pass
            warnings += migrate_cultivars(cn, new_cn)
            if cn.thumbnail:
                db.session.delete(cn.thumbnail)
            cn.index.common_names.remove(cn)  # Sets idx_pos for remaining.
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
                            'please check the box labeled "Yes".')
            flash_all(messages)
            return redirect(url_for('seeds.remove_common_name', cn_id=cn_id))
    crumbs = cblr.crumble_route_group('remove_common_name', REMOVE_ROUTES)
    return render_template('seeds/remove_common_name.html',
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
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.remove_section',
            id_arg='section_id',
            model='Section'
        ))
    form = RemoveSectionForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing section "{0}":'.format(section.name))
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
                            'check the box labeled "Yes".')
            flash_all(messages)
            return redirect(url_for('seeds.remove_section',
                                    section_id=section_id))
    crumbs = cblr.crumble_route_group('remove_section', REMOVE_ROUTES)
    return render_template('seeds/remove_section.html',
                           crumbs=crumbs,
                           form=form,
                           section=section)


@seeds.route('/remove_cultivar', methods=['GET', 'POST'])
@seeds.route('/remove_cultivar/<int:cv_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_cultivar(cv_id=None):
    cv = Cultivar.query.get(cv_id) if cv_id else None
    if cv is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.remove_cultivar',
            id_arg='cv_id',
            model='Cultivar'
        ))
    form = RemoveCultivarForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            warnings = []
            messages.append('Removing cultivar "{0}":'.format(cv.fullname))
            if cv.synonyms:
                cv.synonyms_string = None
                messages.append('Synonyms cleared.')
            if form.delete_images.data:
                if cv.thumbnail:
                    if (not cv.thumbnail.cultivars or
                            cv.thumbnail.cultivars == [cv]):
                        messages.append('Thumbnail image file "{0}" deleted.'
                                        .format(cv.thumbnail.filename))
                        db.session.delete(cv.thumbnail)
                    else:
                        messages.append('Thumbnail image file "{0}" was not '
                                        'deleted because it is in use by '
                                        'other cultivars.')
                if cv.images:
                    for img in cv.images:
                        if (img.cultivars == [cv] and
                                cv not in img.cultivars_with_thumb):
                            messages.append('Image file "{0}" associated '
                                            'with "{1}" has been deleted. '
                                            .format(img.filename, cv.fullname))
                            db.session.delete(img)
            old_path = url_for('seeds.cultivar',
                               idx_slug=cv.common_name.index.slug,
                               cn_slug=cv.common_name.slug,
                               cv_slug=cv.slug)
            warnings.append(
                'Warning: the path "{0}" is no longer valid. <a '
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
                            'please check the box labeled "Yes".')
            flash_all(messages)
            return redirect(url_for('seeds.remove_cultivar', cv_id=cv.id))
    crumbs = cblr.crumble_route_group('remove_cultivar', REMOVE_ROUTES)
    return render_template('seeds/remove_cultivar.html',
                           crumbs=crumbs,
                           form=form,
                           cultivar=cv)


@seeds.route('/remove_packet', methods=['GET', 'POST'])
@seeds.route('/remove_packet/<int:pkt_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_packet(pkt_id=None):
    """Remove a packet from the database."""
    packet = Packet.query.get(pkt_id) if pkt_id else None
    if packet is None:
        return redirect(url_for(
            'seeds.select_object',
            dest='seeds.remove_packet',
            id_arg='pkt_id',
            model='Packet'
        ))
    form = RemovePacketForm()
    if form.validate_on_submit():
        messages = []
        if form.verify_removal.data:
            db.session.delete(packet)
            db.session.commit()
            messages.append('Packet removed.')
            flash_all(messages)
            return redirect(url_for('seeds.manage'))
        else:
            messages.append('Packet was not removed, so no changes '
                            'were made. If you would like to remove it, '
                            'please check the box labeled "Yes".')
            flash_all(messages)
            return redirect(url_for('seeds.remove_packet', pkt_id=pkt_id))
    crumbs = cblr.crumble_route_group('remove_packet', REMOVE_ROUTES)
    return render_template('seeds/remove_packet.html',
                           crumbs=crumbs,
                           form=form,
                           packet=packet)


@seeds.route('/kwargs_test')
def kwargs_test():
    def foo(**kwargs):
        print('kwargs:')
        for k in kwargs:
            print('{}: {}'.format(k, kwargs[k]))
    kwargs = {k: request.args.get(k) for k in request.args}
    defined_arg = kwargs.pop('defined')
    print('Defined arg: {}'.format(defined_arg))
    foo(**kwargs)
    return('done')


@seeds.route('/select_object', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def select_object():
    """View for selecting an object to work with.

    Note:
        Any unspecified request args passed will be passed along to the
        destination route as kwargs.

    Request Args:
        dest: The destination route.
        id_arg: The name of the argument the id of the object will be passed
            as.
        model: The name of the model to load instances of, with spaces between
            words so that it can be shown on the page without having to find a
            way to add spaces between camelcase words.
    """
    kwargs = request_kwargs()
    dest = kwargs.pop('dest')
    id_arg = kwargs.pop('id_arg')
    model = kwargs['model']
    if dest != 'seeds.remove_object':
        kwargs.pop('model')
    if not dest:
        flash('Error: No destination specified.', category='error')
        return redirect(url_for('seeds.manage'))
    form = SelectObjectForm(model=MODELS[model])
    if form.validate_on_submit():
        kwargs[id_arg] = form.id.data
        return redirect(url_for(dest, **kwargs))
    crumbs = (
        cblr.crumble('manage', 'Manage Seeds'),
        cblr.crumble('select_object', dest=dest, id_arg=id_arg)
    )
    return render_template('seeds/select_object.html',
                           crumbs=crumbs,
                           form=form,
                           model=model)


@seeds.route('/manage')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def manage():
    pending = Pending(current_app.config.get('PENDING_FILE'))
    lc = LastCommit()
    if pending.exists():
        pending.load()
    return render_template('seeds/manage.html', pending=pending, lc=lc)


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


@seeds.route('/<idx_slug>/<cn_slug>.html')
def common_name(idx_slug=None, cn_slug=None):
    """Display page for a common name."""
    cn = CommonName.query\
        .join(Index, Index.id == CommonName.index_id)\
        .filter(CommonName.slug == cn_slug, Index.slug == idx_slug)\
        .one_or_none()
    if cn is not None:
        individuals = cn.child_cultivars
        count = len([cv for cv in cn.cultivars if cv.public])
        crumbs = (
            cblr.crumble('home', 'Home'),
            cblr.crumble('index', cn.index.header, idx_slug=idx_slug),
            cn.name
        )
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
                               individuals=individuals,
                               cn=cn,
                               count=count,
                               crumbs=crumbs)
    else:
        abort(404)


@seeds.route('/<idx_slug>/<cn_slug>/<cv_slug>.html')
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


@seeds.route('/flip_cultivar_bool/<int:cv_id>/<attr>')
@permission_required(Permission.MANAGE_SEEDS)
def flip_cultivar_bool(cv_id, attr):
    """Toggle a boolean attribute of a `Cultivar`."""
    cv = Cultivar.query.get(cv_id)
    if cv is None:
        abort(404)
    cv[attr] = not cv[attr]
    if cv[attr]:
        flash('"{}" is now set as {}.'.format(cv.fullname, attr))
    else:
        flash('"{}" is no longer set as {}.'.format(cv.fullname, attr))
    db.session.commit()
    return redirect(request.args.get('origin') or url_for('seeds.manage'))


@seeds.route('/edit_ship_date', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_SEEDS)
def edit_ship_date():
    """Edit the expected date of shipment for orders."""
    form = EditShipDateForm()
    if form.validate_on_submit():
        sd = form.ship_date.data
        current_app.jinja_env.globals['ship_date'] = format_ship_date(sd)
        ship_date = sd.strftime('%m/%d/%Y')
        with open('data/ship_date.dat', 'w', encoding='utf-8') as ofile:
            ofile.write(ship_date)
        flash('Ship date set to {}.'.format(ship_date))
        return redirect(request.args.get('origin') or url_for('seeds.manage'))
    return render_template('seeds/edit_ship_date.html', form=form)


# Functions and views for moving objects in ordering_list collections.
def move_object(cls, obj_id, delta):
    """Move a movable object (in an `ordering_list`) <delta> positions.

    Args:
        cls: The class (db model) of the object to move.
        obj_id: The id (primary key) of the object to move.
        delta: The number of positions to move; positive for forward, negative
            for backward.
    """
    delta = int(delta)  # Flask's int converter doesn't handle negatives.
    obj = cls.query.get(obj_id)
    if obj is None:
        abort(404)
    if obj.move(delta):
        db.session.commit()
        flash('"{0}" has been moved {1} {2} position{3}.'
              .format(obj.name,
                      'forward' if delta > 0 else 'backward',
                      abs(delta),
                      's' if abs(delta) > 1 else ''))
    else:
        if delta < 0:
            flash('"{0}" is already first.'.format(obj.name))
        else:
            flash('"{0}" is already last.'.format(obj.name))
    return redirect(request.args.get('origin') or url_for('seeds.manage'))


@seeds.route('/move_common_name/<int:cn_id>/<delta>')
@permission_required(Permission.MANAGE_SEEDS)
def move_common_name(cn_id, delta):
    """Move a common name <delta> positions in its index."""
    return move_object(CommonName, cn_id, delta)


@seeds.route('/move_section/<int:section_id>/<delta>')
@permission_required(Permission.MANAGE_SEEDS)
def move_section(section_id, delta):
    """Move a section <delta> positions in its parent container."""
    return move_object(Section, section_id, delta)


@seeds.route('/move_cultivar/<int:cv_id>/<delta>')
@permission_required(Permission.MANAGE_SEEDS)
def move_cultivar(cv_id, delta):
    """Move a cultivar <delta> positions in its parent container."""
    return move_object(Cultivar, cv_id, delta)

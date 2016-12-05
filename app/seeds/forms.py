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
from pathlib import Path

from flask import current_app, Markup, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from werkzeug import secure_filename
from wtforms import (
    BooleanField,
    HiddenField,
    RadioField,
    SelectField,
    SelectMultipleField,
    SubmitField,
    ValidationError
)
from wtforms.fields.html5 import DateField
from wtforms.validators import InputRequired, Length, Optional
from app.form_helpers import (
    BeginsWith,
    ListItemLength,
    ReplaceMe,
    SecureFileField,
    SecureFilenameField,
    SlugifiedStringField,
    StrippedStringField,
    StrippedTextAreaField
)
from app import estimate_ship_date
from app.redirects import RedirectsFile
from .models import (
    BulkCategory,
    CommonName,
    Cultivar,
    Image,
    Index,
    Packet,
    Section
)
from app.seeds.models import USDollar as USDollar_


THIS_YEAR = datetime.date.today().year


IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']


SUNLIGHT_CHOICES = [
    ('', 'N/A'),
    ('sun-or-part-shade-before',
     '\U0001F315 \U0001F313  full sun to part shade'),
    ('sun-before', '\U0001F315  full sun'),
    ('sun-or-part-shade-or-light-shade-before',
     ('\U0001F315 \U0001F313 \U0001F311  full sun in mild climates, part '
      'shade to light shade elsewhere')),
    ('part-shade-before', '\U0001F313  part shade'),
    ('part-shade-or-shade-before',
     '\U0001F313 \U0001F311  part shade to light shade'),
    ('part-shade-or-full-shade-before',
     '\U0001F313 \U0001F311  part shade to full shade'),
    ('sun-part-shade-where-hot-before',
     '\U0001F315 \U0001F313  full sun, part shade in hot climates'),
    ('sun-part-shade-before',
     '\U0001F315 \U0001F313 \U0001F311  full sun, part shade, or light shade')
]


# Module functions
def select_field_choices(model=None,
                         items=None,
                         title_attribute='name',
                         order_by=None):
    """Create a list of select field choices from a model or list of items.

    Note:
        If both `model` and `items` are passed, `model` will be ignored, as the
        only use it could have if `items` are passed would be to check against
        the type of `items`, which would likely create more overhead than it's
        worth. This approach also allows mixing of item types if the need
        arises.

    Args:
        model: An optional database model (such as `app.seeds.models.Index`) to
            query from if no `items` are given.
        items: An optional list of database model instances to generate the
            select list from.
        title_attribute: The item attribute to use as a title for the select
            choice.
        order_by: Attribute to order results by.

    Returns:
        list: A list of tuples formatted (item.id, <title>), with title coming
            from the attribute specified by `title_attribute`. If model is not
            set and items is falsey, return an empty list.
    """
    if not items:
        if not order_by:
            order_by = 'position' if hasattr(model, 'position') else 'id'
        if model:
            items = model.query.order_by(order_by).all()
        else:
            return []
    elif order_by:  # Use default order of items if order_by not specified.
        items = sorted(items, key=lambda x: getattr(x, order_by))
    return [(item.id, getattr(item, title_attribute)) for item in items]


def position_choices(**kwargs):
    """Return a list of choices for selecting where to position an instance."""
    choices = select_field_choices(**kwargs)
    choices = [(c[0], 'After: ' + c[1]) for c in choices]
    choices.insert(0, (-1, 'First'))
    return choices


def image_choices(images):
    """Return a list of choices for images in a collection."""
    choices = [(i.id, i.filename) for i in images]
    choices.insert(0, (0, 'None'))
    return choices


def remove_from_choices(choices, obj):
    """Remove the choice pointing to `obj` from a list of select choices.

    Args:

    choices: The select field choices to remove `obj` from.
    obj: The database model instance to be removed from choices; typically this
        is the object a form is editing.
    """
    obj_choice = next(
        (c for c in choices if c[0] == obj.id),
        None
    )
    try:
        choices.remove(obj_choice)
    except ValueError:
        # No need to remove it if it's not there.
        pass


def image_path(filename):
    """Return the path to an image with given filename."""
    try:
        return Path(current_app.config.get('STATIC_FOLDER'), filename)
    except TypeError:
        return None


class USDollar(object):
    """Validator to ensure data in fields for USD amounts is parseable."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid US Dollar value.'
        self.message = message

    def __call__(self, form, field):
        if field:
            try:
                USDollar_.usd_to_decimal(field.data)
            except:
                raise ValidationError(self.message)


# Add Forms
class AddWithThumbnailForm(FlaskForm):
    """A base for forms for adding data which may include a thumbnail.
    
    Attributes:
        thumbnail: File field for thumbnail image.
        thumbnail_filename: String field for thumbnail filename.
    """
    thumbnail = SecureFileField(
        'Thumbnail Image',
        validators=[FileAllowed(IMAGE_EXTENSIONS, 'Images only!')]
    )
    thumbnail_filename = SecureFilenameField(
        'Thumbnail Filename',
        validators=[Length(max=254)]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.thumbnail_filename.tooltip=(
            'Files will be saved in app/static, and filenames may include '
            'subdirectories (e.g. images/flowers/hibiscus.jpg) which will be '
            'created as needed.'
        )

    def validate_thumbnail_filename(self, field):
        """Raise error if a file with the same (full) name already exists."""
        if self.thumbnail.data:
            if not field.data:
                raise ValidationError('Thumbnail must have a filename!')
            else:
                try:
                    if image_path(field.data).exists():
                        raise ValidationError(
                            'A file named "{}" already exists!'
                            .format(field.data)
                        )
                except AttributeError:
                    pass


class AddIndexForm(AddWithThumbnailForm):
    """Form for adding a new `Index` to the database.

    Attributes:
        name: String field for the name of an `Index`.
        description: Text field for the description of an`Index`.
        pos: Select field for where this `Index` belongs in relation to others.
    """
    name = StrippedStringField(
        'Index Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    submit = SubmitField('Save Index')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos.choices = position_choices(model=Index, order_by='position')
        if not self.pos.data:
            self.pos.data = self.pos.choices[-1][0]

    def validate_slug(self, field):
        idx = Index.query.filter(Index.slug == field.data).one_or_none()
        if idx:
            raise ValidationError(Markup(
                'An index with the slug "{}" already exists! <a href="{}">'
                'Click here</a> if you wish to edit it.'
                .format(field.data, url_for('seeds.edit_index', idx_id=idx.id))
            ))



class AddCommonNameForm(AddWithThumbnailForm):
    """Form for adding a new `CommonName` to the database.

    Attributes:
        name: DBified string field for the name of a `CommonName`.
        description: Text field for the optional description of a `CommonName`.
        instructions: Text field for optional planting instructions.
        next_page: Radio field to select page to redirect to after submitting
            a `CommonName`.

        index: The `Index` added `CommonName` will be under.
    """
    name = StrippedStringField(
        'Common Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    list_as = StrippedStringField(
        'List As',
        validators=[Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle/Synonyms',
        validators=[Length(max=254)]
    )
    botanical_names = StrippedStringField(
        'Botanical Name(s)',
        validators=[Length(max=508)]
    )
    sunlight = SelectField('Sunlight', choices=SUNLIGHT_CHOICES) 
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    instructions = StrippedTextAreaField(
        'Planting Instructions',
        validators=[Length(max=5120)])
    pos = SelectField('Position', coerce=int)
    visible = BooleanField('Show on auto-generated pages', default='checked')
    gw_common_names_ids = SelectMultipleField(
        'Other Common Names',
        render_kw={'size': 10},
        coerce=int
    )
    gw_sections_ids = SelectMultipleField(
        'Sections/Series',
        render_kw={'size': 10},
        coerce=int
    )
    gw_cultivars_ids = SelectMultipleField(
        'Cultivars',
        render_kw={'size': 10},
        coerce=int
    )
    submit = SubmitField('Save Common Name')

    def __init__(self, index, *args, **kwargs):
        """Initialize `AddCommonNameForm`.

        Args:
            index: The `Index` added `CommonName` belongs to.
        """
        super().__init__(*args, **kwargs)
        self.index = index
        self.set_selects()

    def set_selects(self):
        self.pos.choices = position_choices(items=self.index.common_names,
                                            order_by='idx_pos')
        if not self.pos.data:
            self.pos.data = self.pos.choices[-1][0]
        self.gw_common_names_ids.choices = select_field_choices(
            model=CommonName,
            order_by='name'
        )
        self.gw_sections_ids.choices = select_field_choices(
            model=Section,
            order_by='name',
            title_attribute='fullname'
        )
        self.gw_cultivars_ids.choices = select_field_choices(
            model=Cultivar,
            order_by='name',
            title_attribute='fullname'
        )

    def validate_slug(self, field):
        """Raise `ValidationError` if `CommonName` instance already exists.

        A new `CommonName` must be a unique combination of `CommonName.name`
        and `CommonName.index_id`.

        Raises:
            ValidationError: If a `CommonName` with the same name and `Index`
                already exists.
        """
        cn = CommonName.query.filter(
            CommonName.slug == field.data,
            CommonName.index_id == self.index.id
        ).one_or_none()
        if cn:
            raise ValidationError(Markup(
                'A common name with the slug "{0}" and index "{1}". already '
                'exists. <a href="{2}">Click here</a> if you wish to edit it.'
                .format(cn.slug,
                        cn.index.name,
                        url_for('seeds.edit_common_name', cn_id=cn.id))
                ))


class AddSectionForm(AddWithThumbnailForm):
    """Form for adding a `Section` to the database.

    Attributes:
        name: DBified string field for `Section` name.
        description: Text field for optional section description.
        pos: Position within parent `CommonName.sections`.

        cn: The `CommonName` this `Section` will belong to.
    """
    parent = SelectField('Subcategory Of (Optional)', coerce=int)
    name = StrippedStringField(
        'Section Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle',
        validators=[Length(max=254)]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    submit = SubmitField('Save Section')

    def __init__(self, cn, *args, **kwargs):
        """Initialize `AddSectionForm`.

        Args:
            cn: The `CommonName` added `Section` belongs to.
        """
        super().__init__(*args, **kwargs)
        self.cn = cn
        self.pos.choices = position_choices(
            items=self.cn.child_sections
        )
        if not self.pos.data:
            self.pos.data = self.pos.choices[-1][0]
        self.parent.choices = select_field_choices(items=self.cn.sections,
                                                   order_by='id')
        self.parent.choices.insert(0, (0, 'None'))

    def validate_name(self, field):
        """Raise `ValidationError` if name  + common name already exists in db.

        Raises:
            ValidationError: If the section already exists in the database.
        """
        for section in self.cn.sections:
            if section.name == field.data:
                raise ValidationError(Markup(
                    'The common name \'{0}\' already has a section named '
                    '\'{1}\'! Click <a href="{2}">here</a> if you wish to '
                    'edit that section.'
                    .format(self.cn.name,
                            section.name,
                            url_for('seeds.edit_section',
                                    section_id=section.id))
                ))


class AddCultivarForm(AddWithThumbnailForm):
    """Form for adding a new `Cultivar` to the database.

    Attributes:
        name: String field for the name of added `Cultivar`.
        subtitle: An optional subtitle to use if the subtitle is something
            other than '<common name> Seeds'.
        botanical_name: String field for botanical name for cultivar.
        section: Select field for optional `Section` for added `Cultivar`.
        description: Text field for optional `Cultivar` HTML description.
        synonyms: String field for optional synonyms of this cultivar.
        new_until: Date field for optional date to mark added `Cultivar` as new
            until.
        featured: Checkbox for whether or not to feature the `Cultivar` on the
            page for its `CommonName`.
        in_stock: Checkbox for whether or not added `Cultivar` is in stock.
        active: Checkbox for whether or not added `Cultivar` is to be actively
            replenished when stock gets low.
        visible: Checkbox for whether or not added `Cultivar` should be visible
            on auto-generated pages.
        taxable: Checkbox for whether or not added `Cultivar` is taxable
            in the state of California.

        cn: The `CommonName` added `Cultivar` belongs to.
    """
    name = StrippedStringField(
        'Cultivar Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle',
        validators=[Length(max=254)]
    )
    botanical_name = StrippedStringField(
        'Botanical Name(s)',
        validators=[Length(max=254)]
    )
    section = SelectField('Section', coerce=int)
    organic = BooleanField('Organic')
    thumbnail = SecureFileField(
        'Thumbnail Image',
        validators=[FileAllowed(IMAGE_EXTENSIONS, 'Images only!')]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    gw_common_names_ids = SelectMultipleField(
        'Common Names',
        render_kw={'size': 10},
        coerce=int
    )
    gw_sections_ids = SelectMultipleField(
        'Sections/Series',
        render_kw={'size': 10},
        coerce=int
    )
    gw_cultivars_ids = SelectMultipleField(
        'Other Cultivars',
        render_kw={'size': 10},
        coerce=int
    )
    new_for = SelectField(
        'New For',
        choices=[
            (0, 'N/A'),
            (THIS_YEAR, str(THIS_YEAR)),
            (THIS_YEAR + 1, str(THIS_YEAR + 1))
        ],
        default=0,
        coerce=int
    )
    new_until = DateField('New until (leave as-is if not new)',
                          format='%m/%d/%Y',
                          default=datetime.date.today())
    featured = BooleanField('Featured')
    in_stock = BooleanField('In Stock', default='checked')
    active = BooleanField('Actively replenished', default='checked')
    visible = BooleanField('Visible on auto-generated pages',
                           default='checked')
    taxable = BooleanField('Taxable in California', default='checked')
    open_pollinated = BooleanField('Open Pollinated')
    maturation = StrippedStringField(
        'Maturation Time',
        validators=[Length(max=254)]
    )
    submit = SubmitField('Save Cultivar')

    def __init__(self, cn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cn = cn
        self.set_selects()
        if not self.submit.data:
            self.subtitle.data = self.cn.name

    def set_selects(self):
        """Sets indexes, and common_names from db."""
        self.section.choices = select_field_choices(items=self.cn.sections,
                                                    order_by='name')
        self.section.choices.insert(0, (0, 'None'))
        self.gw_common_names_ids.choices = select_field_choices(
            model=CommonName,
            order_by='name'
        )
        self.gw_sections_ids.choices = select_field_choices(
            model=Section,
            order_by='name',
            title_attribute='fullname'
        )
        self.gw_cultivars_ids.choices = select_field_choices(
            model=Cultivar,
            order_by='name',
            title_attribute='fullname'
        )
        self.pos.choices = position_choices(items=self.cn.child_cultivars)
        if not self.pos.data:
            self.pos.data = self.pos.choices[-1][0]

    def validate_name(self, field):
        """Raise `ValidationError` if `Cultivar` already exists.

        Raises:
            ValidationError: If a `Cultivar` with the same name, `CommonName`,
            and (optional) `Section` already exists.
        """
        sec_id = self.section.data if self.section.data else None
        cv = Cultivar.query.filter(
            Cultivar.name == field.data,
            Cultivar.common_name_id == self.cn.id,
            Cultivar.section_id == sec_id
        ).one_or_none()
        if cv:
            raise ValidationError(Markup(
                'The cultivar \'{0}\' already exists! <a href="{1}" '
                'target="_blank">Click here</a> if you wish to edit it.'
                .format(cv.fullname,
                        url_for('seeds.edit_cultivar', cv_id=cv.id))
            ))


class AddPacketForm(FlaskForm):
    """Form for adding a packet to a cultivar.

    Attributes:
        sku: String field for product SKU of added packet.
        price: String field for price in US Dollars.
        amount: String field for amount of seed in added packet.
        again: Checkbox for whether or not to keep adding
            packets on submit.

        cultivar: The `Cultivar` added `Packet` belongs to.
    """
    sku = StrippedStringField(
        'SKU',
        validators=[InputRequired(), Length(max=32)]
    )
    product_name = StrippedStringField(
        'Product Name',
        validators=[InputRequired(), Length(max=254)]
    )
    price = StrippedStringField(
        'Price in US dollars',
        validators=[InputRequired(), Length(max=16), USDollar()]
    )
    amount = StrippedStringField(
        'Amount of Seeds',
        validators=[InputRequired(), Length(max=16)]
    )
    submit = SubmitField('Save Packet')

    def __init__(self, cultivar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cultivar = cultivar
        if not self.submit.data:
            self.product_name.data = self.cultivar.product_name

    def validate_sku(self, field):
        """Raise ValidationError if sku already exists in database.

        Raises:
            ValidationError: If value of sku is already used by another packet.
        """
        packet = Packet.query\
            .filter(Packet.sku == field.data.strip())\
            .one_or_none()
        if packet:
            pkt_url = url_for('seeds.edit_packet', pkt_id=packet.id)
            raise ValidationError(
                Markup('The SKU \'{0}\' is already in use by \'{1}\'. <a '
                       'href="{2}">Click here</a> if you wish to edit it.'
                       .format(packet.sku, packet.cultivar.fullname, pkt_url))
            )


class AddBulkCategoryForm(AddWithThumbnailForm):
    """Form for adding a `BulkCategory` to db.

    Attributes:
        name: Name of the bulk category.
        slug: URL slug for bulk category.
        list_as: What to list the bulk category as in links.
    """
    name = StrippedStringField(
        'Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = StrippedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    list_as = StrippedStringField('List As', validators=[Length(max=254)])
    subtitle = StrippedStringField('Subtitle', validators=[Length(max=254)])
    submit = SubmitField('submit')

    def validate_slug(self, field):
        """Raise an error if a `BulkCategory` with the same slug exists."""
        bc = BulkCategory.query.filter(
            BulkCategory.slug == field.data
        ).one_or_none()
        if bc:
            raise ValidationError(Markup(
                'A bulk category with the slug "{}" already exists. <a href='
                '"{}">Click here</a> if you wish to edit it.'
                .format(field.data,
                        url_for('seeds.edit_bulk_category', cat_id=bc.id))
            ))


class AddRedirectForm(FlaskForm):
    """Form for adding a redirect to the application.

    Attributes:
        old_path: String field for path to redirect from.
        new_path: String field for path to redirect to.
        status_code: Select field for HTTP redirect status code to use.
    """
    old_path = StrippedStringField(
        'Old Path',
        validators=[BeginsWith('/'),
                    InputRequired(),
                    Length(max=4096),
                    ReplaceMe()]
    )
    new_path = StrippedStringField(
        'New Path',
        validators=[BeginsWith('/'),
                    InputRequired(),
                    Length(max=4096),
                    ReplaceMe()]
    )
    status_code = SelectField('Status Code',
                              coerce=int,
                              choices=[(300, '300 Multiple Choices'),
                                       (301, '301 Moved Permanently'),
                                       (302, '302 Found'),
                                       (303, '303 See Other'),
                                       (304, '304 Not Modified'),
                                       (305, '305 Use Proxy'),
                                       (306, '306 Switch Proxy'),
                                       (307, '307 Temporary Redirect'),
                                       (308, '308 Permanent Redirect')],
                              default=302)
    submit = SubmitField('Save Redirect')

    def __init__(self,
                 old_path=None,
                 new_path=None,
                 status_code=None,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        if old_path:
            self.old_path.data = old_path
        if new_path:
            self.new_path.data = new_path
        if status_code:
            self.status_code.data = int(status_code)

    def validate_old_path(self, field):
        """Raise a ValidationError if a redirect from old_path exists."""
        rdf = RedirectsFile(current_app.config.get('REDIRECTS_FILE'))
        if rdf.exists():
            rdf.load()
            old_paths = [rd.old_path for rd in rdf.redirects]
            if field.data in old_paths:
                old_rd = rdf.get_redirect_with_old_path(field.data)
                raise ValidationError('\'{0}\' is already being redirected to '
                                      '\'{1}\'!'.format(old_rd.old_path,
                                                        old_rd.new_path))

    def validate_new_path(self, field):
        """Raise a ValidationError if new path points to another redirect."""
        rdf = RedirectsFile(current_app.config.get('REDIRECTS_FILE'))
        if rdf.exists():
            rdf.load()
            old_paths = [rd.old_path for rd in rdf.redirects]
            if field.data in old_paths:
                old_rd = rdf.get_redirect_with_old_path(field.data)
                rd_url = url_for('seeds.add_redirect',
                                 old_path=self.old_path.data,
                                 new_path=old_rd.new_path,
                                 status_code=self.status_code.data)
                raise ValidationError(Markup(
                    'The path \'{0}\' is being redirected to \'{1}\'. You '
                    'may wish to <a href="{2}" target="_blank">add a redirect '
                    'from \'{3}\' to \'{1}\'</a> instead.'
                    .format(field.data,
                            old_rd.new_path,
                            rd_url,
                            self.old_path.data)))


# Edit Forms
class EditWithThumbnailForm(FlaskForm):
    """Base form for editing objects that have thumbnails."""
    thumbnail_id = SelectField('Choose a Thumbnail', coerce=int)
    thumbnail = SecureFileField(
        'New Thumbnail',
        validators=[FileAllowed(IMAGE_EXTENSIONS, 'Images only!')]
    )
    thumbnail_filename = SecureFilenameField(
        'Thumbnail Filename',
        validators=[Length(max=254)]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        obj = kwargs['obj']
        self.thumbnail_id.choices = [
            (
                i.id, 
                '{}{}'.format(
                    ('Current: ' if obj.thumbnail and
                     i.id == obj.thumbnail.id else ''),
                    i.filename
                )
            ) for i in obj.images
        ]
        self.thumbnail_id.choices.insert(0, (0, 'None'))
        self.image_urls = {i.id: i.url for i in obj.images}
        self.image_urls[0] = ''
        if not self.submit.data:
            try:
                self.thumbnail_filename.data = obj.thumbnail.filename
            except AttributeError:
                pass
        self.thumbnail_id.tooltip = (
            'Warning: Selecting anything other than the current '
            'thumbnail will cause any other changes to thumbnail (such '
            'as uploading a new file or changing Thumbnail Filename) to '
            'be ignored.'
        )
        self.thumbnail.tooltip = (
            'Warning: Uploading a new image without editing Thumbnail '
            'Filename will replace the existing image file with the uploaded '
            'image.'
        )
        self.thumbnail_filename.tooltip = (
            'Editing this without uploading a new image file will rename/move '
            'the existing thumbnail file.'
        )

    def validate_thumbnail_filename(self, field):
        """Raise error if new thumbnail is uploaded w/o a filename."""
        if self.thumbnail.data and not field.data:
            raise ValidationError(
                'Cannot upload new thumbnail without a filename.'
            )


class EditIndexForm(EditWithThumbnailForm):
    """Form for editing an existing `Index` from the database.

    Attributes:
        index: The `Index` to edit.
        name: DBified string field for `Index` name.
        description: String field for description.
    """
    id = HiddenField()
    name = StrippedStringField(
        'Index',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    submit = SubmitField('Save Index')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos.choices = position_choices(model=Index, order_by='position')
        obj = kwargs['obj']
        choice = next(c for c in self.pos.choices if c[0] == obj.id)
        choice_index = self.pos.choices.index(choice)
        if not self.pos.data:
            if choice_index == 0:
                self.pos.data = -1
            else:
                self.pos.data = self.pos.choices[choice_index - 1][0]
        self.pos.choices.pop(choice_index)

    def validate_name(self, field):
        """Raise ValidationError if changing name would result in clash."""
        idx = Index.query.filter(Index.name == field.data,
                                 Index.id != self.id.data).one_or_none()
        if idx:
            raise ValidationError(Markup(
                'A different index is already named \'{0}\'. <a href="{1}" '
                'target="_blank">Click here</a> if you would like to edit it.'
                .format(idx.name,
                        url_for('seeds.edit_index', idx_id=self.id))
            ))


class EditCommonNameForm(EditWithThumbnailForm):
    """Form for editing an existing common name in the database.

    Attributes:
        index_id: Select field for `Index` edited `CommonName` belongs to.
        name: DBified string field for name of `CommonName`.
        description: Text field for `CommonName` description.
        instructions Text field for planting instructions.
        synonyms_string: String field for synonyms of edited `CommonName`.
    """
    id = HiddenField()
    index_id = SelectField('Index',
                           coerce=int,
                           validators=[InputRequired()])
    name = StrippedStringField(
        'Common Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    list_as = StrippedStringField(
        'List As',
        validators=[InputRequired(), Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle/Synonyms',
        validators=[Length(max=254)]
    )
    botanical_names = StrippedStringField(
        'Botanical Name(s)',
        validators=[Length(max=254)]
    )
    sunlight = SelectField('Sunlight', choices=SUNLIGHT_CHOICES)
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    instructions = StrippedTextAreaField(
        'Planting Instructions',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    gw_common_names_ids = SelectMultipleField(
        'Other Common Names',
        render_kw={'size': 10},
        coerce=int
    )
    gw_sections_ids = SelectMultipleField(
        'Sections/Series',
        render_kw={'size': 10},
        coerce=int
    )
    gw_cultivars_ids = SelectMultipleField(
        'Cultivars',
        render_kw={'size': 10},
        coerce=int
    )
    submit = SubmitField('Save Common Name')

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        self.obj = kwargs['obj']
        self.set_selects()

    def set_selects(self):
        """Populate indexes with Indexes from the database."""
        cn = self.obj
        self.index_id.choices = select_field_choices(model=Index)
        self.gw_common_names_ids.choices = select_field_choices(
            model=CommonName,
            order_by='name'
        )
        remove_from_choices(self.gw_common_names_ids.choices, cn)
        self.gw_sections_ids.choices = select_field_choices(
            model=Section,
            order_by='name',
            title_attribute='fullname'
        )
        self.gw_cultivars_ids.choices = select_field_choices(
            model=Cultivar,
            order_by='name',
            title_attribute='fullname'
        )
        self.pos.choices = position_choices(items=cn.index.common_names,
                                            order_by='idx_pos')
        remove_from_choices(self.pos.choices, cn)
        if not self.pos.data:
            collection = cn.index.common_names
            cn_index = collection.index(cn)
            if cn_index == 0:
                self.pos.data = -1
            else:
                self.pos.data = collection[cn_index - 1].id

    def validate_name(self, field):
        """Raise ValidationError if conflict would be created."""
        cn = CommonName.query.filter(
            CommonName.name == field.data,
            CommonName.index_id == self.index_id.data,
            CommonName.id != int(self.id.data)
        ).one_or_none()
        if cn:
            raise ValidationError(Markup(
                'A common name \'{0}\' already exists with the index '
                '\'{1}\'. <a href="{2}" target="_blank">Click here</a> if you '
                'wish to edit it.'
                .format(cn.name,
                        cn.index.name,
                        url_for('seeds.edit_common_name', cn_id=cn.id))
            ))

    def validate_synonyms_string(self, field):
        """Raise a ValidationError if any synonyms are too long.

        Raises:
            ValidationError: If any synonym is too long.
        """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')


class EditSectionForm(EditWithThumbnailForm):
    """Form for editing a Section to the database.

    Attributes:
        id: The unique id of edited `Section`.
        name: DBified string field for `Section` name.
        common_name_id: Select field for `CommonName` section belongs to.
        description: Text field for `Section` description.
    """
    id = HiddenField()
    parent_id = SelectField('Subsection Of (Optional)', coerce=int)
    common_name_id = SelectField('Select Common Name', coerce=int)
    name = StrippedStringField(
        'Section Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle',
        validators=[Length(max=254)]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    submit = SubmitField('Save Section')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = kwargs['obj']
        self.set_selects()

    def set_selects(self):
        """Set select choices."""
        self.common_name_id.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )
        self.parent_id.choices = select_field_choices(
            items=self.obj.common_name.sections,
            order_by='cn_pos'
        )
        self.parent_id.choices.insert(0, (0, 'None'))
        self.pos.choices = position_choices(items=self.obj.parent_collection)
        remove_from_choices(self.pos.choices, self.obj)
        if not self.pos.data:
            secs = self.obj.parent_collection
            s_index = secs.index(self.obj)
            if s_index == 0:
                self.pos.data = -1
            else:
                self.pos.data = secs[s_index - 1].id

    def validate_name(self, field):
        """Raise if another `Section` exists with same name and CN."""
        sec = Section.query.filter(
            Section.name == field.data,
            Section.common_name_id == int(self.common_name_id.data),
            Section.id != self.id.data
        ).one_or_none()
        if sec:
            raise ValidationError(Markup(
                'A section named \'{0}\' already belongs to the common name '
                '\{1}\'. <a href="{2}" target="_blank">Click here</a> if you '
                'wish to edit it.'
                .format(sec.name,
                        sec.common_name.name,
                        url_for('seeds.edit_section', section_id=sec.id))
            ))


class EditCultivarForm(EditWithThumbnailForm):
    """Form for editing an existing cultivar in the database.

    Attributes:
        id: Unique ID for `Cultivar` to be edited.
        common_name_id: Select field for `CommonName` of edited `Cultivar`.
        botanical_name: String field for botanical name of `Cultivar`.
        section_id: Select field for `Section` `Cultivar` is in, if any.
        name: DBified string field for `Cultivar` name, excluding section and
            common name.
        subtitle: DBified string field for optional subtitle.
        description: Text field for HTML description of `Cultivar`.
        synonyms_string: String field for synonyms of `Cultivar`.
        new_until: Date field for when `Cultivar` will no longer be marked as
            new, if applicable.
        featured: Checkbox for whether or not to feature the `Cultivar` on the
            page for its `CommonName`.
        active: Checkbox for whether or not `Cultivar` is to be restocked when
            low/out of stock.
        in_stock: Checkbox for whether or not `Cultivar` is in stock.
    """
    id = HiddenField()
    common_name_id = SelectField('Common Name',
                                 coerce=int,
                                 validators=[InputRequired()])
    botanical_name = StrippedStringField(
        'Botanical Name',
        validators=[Length(max=254)]
    )
    section_id = SelectField('Section', coerce=int)
    organic = BooleanField('Organic')
    taxable = BooleanField('Taxable in California')
    name = StrippedStringField(
        'Cultivar Name',
        validators=[InputRequired(), Length(max=254)]
    )
    slug = SlugifiedStringField(
        'URL Slug',
        validators=[InputRequired(), Length(max=254)]
    )
    subtitle = StrippedStringField(
        'Subtitle',
        validators=[Length(max=254)]
    )
    description = StrippedTextAreaField(
        'Description',
        validators=[Length(max=5120)]
    )
    pos = SelectField('Position', coerce=int)
    gw_common_names_ids = SelectMultipleField(
        'Common Names',
        render_kw={'size': 10},
        coerce=int
    )
    gw_sections_ids = SelectMultipleField(
        'Sections/Series',
        render_kw={'size': 10},
        coerce=int
    )
    gw_cultivars_ids = SelectMultipleField(
        'Other Cultivars',
        render_kw={'size': 10},
        coerce=int
    )
    new_for = SelectField(
        'New For',
        choices=[
            (0, 'N/A'),
            (THIS_YEAR, str(THIS_YEAR)),
            (THIS_YEAR + 1, str(THIS_YEAR + 1))
        ],
        default=0,
        coerce=int
    )
    featured = BooleanField('Featured')
    active = BooleanField('Actively replenished')
    visible = BooleanField('Visible on auto-generated pages')
    in_stock = BooleanField('In Stock')
    open_pollinated = BooleanField('Open Pollinated')
    maturation = StrippedStringField(
        'Maturation Time',
        validators=[Length(max=254)]
    )
    submit = SubmitField('Save Cultivar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj = kwargs['obj']
        self.set_selects()

    def set_selects(self):
        """Set choices for all select fields with values from database."""
        self.common_name_id.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )
        self.section_id.choices = select_field_choices(model=Section,
                                                       order_by='name')
        self.section_id.choices.insert(0, (0, 'N/A'))
        self.gw_common_names_ids.choices = select_field_choices(
            model=CommonName,
            order_by='name'
        )
        self.gw_sections_ids.choices = select_field_choices(
            model=Section,
            order_by='name',
            title_attribute='fullname'
        )
        self.gw_cultivars_ids.choices = select_field_choices(
            model=Cultivar,
            order_by='name',
            title_attribute='fullname'
        )
        remove_from_choices(self.gw_cultivars_ids.choices, self.obj)
        self.pos.choices = position_choices(items=self.obj.parent_collection)
        remove_from_choices(self.pos.choices, self.obj)
        if not self.pos.data:
            cvs = self.obj.parent_collection
            cv_index = cvs.index(self.obj)
            if cv_index == 0:
                self.pos.data = -1
            else:
                self.pos.data = cvs[cv_index - 1].id

    def validate_name(self, field):
        """Raise ValidationError if changes would create duplicate cultivar."""
        cn_id = self.common_name_id.data
        sec_id = self.section_id.data if self.section_id.data else None
        cv = Cultivar.query.filter(
            Cultivar.name == field.data,
            Cultivar.common_name_id == cn_id,
            Cultivar.section_id == sec_id,
            Cultivar.id != self.id.data
        ).one_or_none()
        if cv:
            raise ValidationError('The cultivar \'{0}\' already exists!'
                                  .format(cv.fullname))

    def validate_section_id(self, field):
        """Raise ValidationError if `Section` does not belong to `CommonName`.

        Raises:
            ValidationError: If selected section does not belong to selected
                common name.
        """
        if field.data:
            sec = Section.query.get(field.data)
            if self.common_name_id.data != sec.common_name_id:
                sec_url = url_for('seeds.edit_section', section_id=sec.id)
                raise ValidationError(Markup(
                    'The selected section does not belong to the selected '
                    'common name. <a href="{0}">Click here</a> if you would '
                    'like to edit the section \'{1}\'.'
                    .format(sec_url, sec.name)
                ))

    def validate_synonyms_string(self, field):
        """Raise a ValidationError if any synonyms are too long.

        Raises:
            ValidationError: If any synonym is too long.
        """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')


class EditPacketForm(FlaskForm):
    """Form for adding a packet to a cultivar.

    Attributes:
        id: Unique ID of `Packet`.
        sku: String field for `Packet` product SKU.
        price: String field for price in US dollars.
        amount: Amount of seeds in packet.
    """
    id = HiddenField()
    cultivar_id = SelectField('Cultivar', coerce=int)
    sku = StrippedStringField(
        'SKU',
        validators=[InputRequired(), Length(max=32)]
    )
    product_name = StrippedStringField(
        'Product Name',
        validators=[InputRequired(), Length(max=254)]
    )
    price = StrippedStringField(
        'Price in US dollars',
        validators=[InputRequired(), Length(max=16), USDollar()]
    )
    amount = StrippedStringField(
        'Amount of Seeds',
        validators=[InputRequired(), Length(max=16)]
    )
    submit = SubmitField('Save Packet')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()

    def set_selects(self):
        """Set select fields."""
        self.cultivar_id.choices = select_field_choices(
            model=Cultivar,
            title_attribute='fullname',
            order_by='slug'
        )
        print(self.cultivar_id.data)

    def validate_sku(self, field):
        """Raise ValidationError if SKU belongs to another packet."""
        pkt = Packet.query.filter(Packet.sku == field.data.strip(),
                                  Packet.id != self.id.data).one_or_none()
        if pkt:
            raise ValidationError(Markup(
                'The SKU \'{0}\' is already in use by the packet \'{1}\' '
                'belonging to {2}. <a href="{3}" target="_blank">Click here'
                '</a> if you would like to edit it.'
                .format(pkt.sku,
                        pkt.info,
                        pkt.cultivar.name,
                        url_for('seeds.edit_packet', pkt_id=pkt.id))
            ))


class RemoveIndexForm(FlaskForm):
    """Form for removing an `Index` from the database.

    Attributes:
        move_to: Select field for selecting Index to move children of
            this index to when deleting it.
        verify_removal: Checkbox to confirm deletion should happen.

        index: The `Index` to remove.
    """
    move_to = SelectField('Move common names and cultivars in this index '
                          'to', coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Index')

    def __init__(self, index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.index = index
        self.set_selects()

    def set_selects(self):
        """Set move_to SelectField with other Indexes."""
        idxs = Index.query.filter(Index.id != self.index.id).all()
        self.move_to.choices = select_field_choices(items=idxs)


class RemoveCommonNameForm(FlaskForm):
    """Form for removing a `CommonName` from the database.

    Attributes:
        move_to: Select field for `CommonName` to move children to.
        verify_removal: Checkbox for whether or not to remove `CommonName`.

        cn: The `CommonName` to remove.
    """
    move_to = SelectField('Move cultivars associated with '
                          'this common name to', coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Common Name')

    def __init__(self, cn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cn = cn
        self.set_selects()

    def set_selects(self):
        """Set select fields.

        Args:
            cn_id: The id of the CommonName to be removed.
        """
        cns = CommonName.query.filter(CommonName.id != self.cn.id).all()
        self.move_to.choices = select_field_choices(
            items=cns,
            title_attribute='select_field_title',
            order_by='name'
        )


class RemoveSectionForm(FlaskForm):
    """Form for removing a `Section` from the database.

    Attributes:
        verify_removal: Checkbox for whether or not to remove `Section`.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Section')


class RemoveCultivarForm(FlaskForm):
    """Form for removing a `Cultivar` from the database.

    Attributes:
        delete_images: Checkbox for whether or not to delete images associated
            with `Cultivar` being removed.
        verify_removal: Checkbox for whether or not to remove `Cultivar`.
    """
    delete_images = BooleanField('Also delete all images for this cultivar',
                                 default=True)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Cultivar')


class RemovePacketForm(FlaskForm):
    """Form for removing a `Packet` from the database.

    Attributes:
        verify_removal: Checkbox for whether or not to remove `Packet`.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Packet')


class SelectIndexForm(FlaskForm):
    """Form for selecting an index.

    Attributes:
        index: Select field for `Index`.
    """
    index = SelectField('Select Index', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate index with Indexes from the database."""
        self.index.choices = select_field_choices(model=Index)


class SelectCommonNameForm(FlaskForm):
    """Form for selecting a common name.

    Attributes:
        common_name: Select field for `CommonName`.
    """
    common_name = SelectField('Select Common Name', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate `common_name`."""
        self.common_name.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )


class SelectSectionForm(FlaskForm):
    """Form for selecting a section.

    Attributes:
        section: Select field for `Section`.
    """
    section = SelectField('Select Section', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate `section`."""
        self.section.choices = select_field_choices(model=Section,
                                                    order_by='name')


class SelectCultivarForm(FlaskForm):
    """Form for selecting a cultivar.

    Attributes:
        cultivar: Select field for `Cultivar`.
    """
    cultivar = SelectField('Select Cultivar', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate `cultivar`."""
        self.cultivar.choices = select_field_choices(
            model=Cultivar,
            order_by='slug',
            title_attribute='fullname'
        )


class SelectPacketForm(FlaskForm):
    """Form for selecting a packet.

    Attributes:
        packet: Select field for `Packet`.
    """
    packet = SelectField('Select Packet', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate packet with Packets from database."""
        self.packet.choices = select_field_choices(model=Packet,
                                                   order_by='sku',
                                                   title_attribute='info')


class EditShipDateForm(FlaskForm):
    """Form for editing the expected ship date for domestic orders."""
    ship_date = DateField(
        'Orders from today ship on',
        format='%m/%d/%Y', validators=[InputRequired()]
    )
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.ship_date.data:
            self.ship_date.data = estimate_ship_date()

    def validate_ship_date(self, field):
        """Make sure ship_date is later than today."""
        if field.data < datetime.date.today():
            raise ValidationError(
                'While shipping orders before they\'re made would be pretty '
                'neat, it is unfortunately a physical impossibility.'
            )


class EditRatesForm(FlaskForm):
    """Form for editing rates and dates."""
    free_shipping_threshold = StrippedStringField(
        'Free shipping for orders over'
    )
    usps_first_class = StrippedStringField('USPS First-Class (Domestic)')
    usps_priority = StrippedStringField('USPS Priority (Domestic)')
    itl_first_class = StrippedStringField(
            'USPS First-Class (International)'
    )
    itl_priority = StrippedStringField('USPS Priority (International)')
    submit = SubmitField('Submit')


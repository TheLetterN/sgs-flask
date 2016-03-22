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

from flask import current_app, Markup, url_for
from werkzeug import secure_filename
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    HiddenField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError
)
from wtforms.validators import DataRequired, Length
from app.redirects import RedirectsFile
from .models import (
    BotanicalName,
    dbify,
    Index,
    CommonName,
    Image,
    Packet,
    Quantity,
    Cultivar,
    Series,
)
from .models import USDollar as USDollar_


IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']


# Module functions
def select_field_choices(model=None,
                         items=None,
                         title_attribute='name',
                         order_by='id'):
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
        if model:
            items = model.query.order_by(order_by).all()
        else:
            return []
    else:
        items = sorted(items, key=lambda x: getattr(x, order_by))
    return [(item.id, getattr(item, title_attribute)) for item in items]


# Custom validators
#
# Note: Each validator has a `messages` attribute, which is just the error
# message to display when triggered.
class IsBotanicalName(object):
    """Validator to ensure data looks like a valid botanical name."""
    def __init__(self, message=None):
        if not message:
            self.message = (
                'Field does not appear to contain a valid botanical name. A '
                'valid botanical name must begin with a genus, which should '
                'have its first (and only first) letter capitalized.'
            )

    def __call__(self, form, field):
        if not BotanicalName.validate(field.data):
            raise ValidationError(self.message)


class NotSpace(object):
    """Validator to ensure a field is not purely whitespace."""
    def __init__(self, message=None):
        if not message:
            message = 'Field cannot consist entirely of whitespace.'
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.isspace():
            raise ValidationError(self.message)


class ReplaceMe(object):
    """Validator for fields populated with data that needs to be edited.

    These fields can be populated with strings that need to be edited by the
    user to be valid. The parts that need to be edited are enclosed in <>.
    """
    def __init__(self, message=None):
        if not message:
            self.message = 'Field contains data that needs to be replaced. '\
                           'Please replace any sections surrounded by < and '\
                           '> with requested data.'

    def __call__(self, form, field):
        if '<' in field.data and '>' in field.data:
            raise ValidationError(self.message)


class RRPath(object):
    """Validatator for fields requiring a root-relative path."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must contain a root-relative path beginning with'\
                      'a forward slash. (/)'
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data[0] != '/':
            raise ValidationError(self.message)


class SynonymLength(object):
    """Validator for length of each synonym in a comma-separated list.

    Note:
        This validator only concerns itself with the length of each synonym,
        so if no synonyms are present it will not raise an error.
    """
    def __init__(self, min_length, max_length, message=None):
        if min_length < max_length:
            self.min_length = min_length
            self.max_length = max_length
        else:
            raise ValueError('min_length must be less than max_length!')
        if not message:
            self.message = ('Each synonym must be between {0} and {1} '
                            'characters in length!'.format(self.min_length,
                                                           self.max_length))

    def __call__(self, form, field):
        if field.data:
            syns = field.data.split(', ')
            bad_syns = [s for s in syns if len(s) < self.min_length
                                        or len(s) > self.max_length]  # noqa
            if bad_syns:
                raise ValidationError(self.message.format(', '.join(bad_syns)))


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


# Custom fields
class DBifiedStringField(StringField):
    """A StringField that has its data run through dbify().

    Note:
        This is the only place in this module `dbify` needs to be run, as
        `process_formdata` runs before validation, so <field>.data will always
        be dbified before it is actually used.
    """
    def process_formdata(self, value):
        super().process_formdata(value)
        self.data = dbify(self.data)


# Forms
#
# Note: `submit` in forms is always the button for form submission, and `field`
# in validators is always the field being validated.
class AddIndexForm(Form):
    """Form for adding a new `Index` to the database.

    Attributes:
        name: DBified string field for the name of an `Index`.
        description: Text field for the description of an`Index`.
    """
    name = DBifiedStringField('Index Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Add Index')

    def validate_name(self, field):
        """Raise a ValidationError if an `Index` exists with given name.

        Raises:
            ValidationError: If submitted `Index` already exists in the
                database.
        """
        idx = Index.query.filter(Index.name == field.data).one_or_none()
        if idx:
            idx_url = url_for('seeds.edit_index', idx_id=idx.id)
            raise ValidationError(
                Markup('\'{0}\' already exists in the database. <a '
                       'href="{1}">Click here</a> to edit it.'
                       .format(idx.name, idx_url))
            )


class AddCommonNameForm(Form):
    """Form for adding a new `CommonName` to the database.

    Attributes:
        name: DBified string field for the name of a `CommonName`.
        parent_cn: Select field for an optional `CommonName` that the added
            `CommonName` is a subcategory of.
        description: Text field for the optional description of a `CommonName`.
        instructions: Text field for optional planting instructions.
        synonyms: Text field for optional synonyms of added `CommonName`.
        next_page: Radio field to select page to redirect to after submitting
            a `CommonName`.

        index: The `Index` added `CommonName` will be under.
    """
    name = DBifiedStringField('Common Name',
                              validators=[Length(1, 64), NotSpace()])
    parent_cn = SelectField('Subcategory of', coerce=int)
    description = TextAreaField('Description', validators=[NotSpace()])
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    synonyms = StringField('Synonyms',
                           validators=[NotSpace(), SynonymLength(0, 64)])
    next_page = RadioField(
        'After submission, go to',
        choices=[('add_botanical_name', 'Add Botanical Name (optional)'),
                 ('add_series', 'Add Series (optional)'),
                 ('add_cultivar', 'Add Cultivar')],
        default='add_cultivar'
    )
    submit = SubmitField('Add Common Name')

    def __init__(self, index, *args, **kwargs):
        """Initialize `AddCommonNameForm`.

        Args:
            index: The `Index` added `CommonName` belongs to.
        """
        super().__init__(*args, **kwargs)
        self.index = index
        self.set_selects()

    def validate_name(self, field):
        """Raise `ValidationError` if `CommonName` instance already exists.

        A new `CommonName` must be a unique combination of `CommonName.name`
        and `CommonName.index_id`.

        Raises:
            ValidationError: If a `CommonName` with the same name and `Index`
                already exists.
        """
        cn = CommonName.query.filter(
            CommonName.name == field.data,
            CommonName.index_id == self.index.id
        ).one_or_none()
        if cn:
            raise ValidationError(Markup(
                'The common name \'{0}\' already exists under the index '
                '\'{1}\'. <a href="{2}">Click here</a> if you wish to edit it.'
                .format(cn.name,
                        cn.index.name,
                        url_for('seeds.edit_common_name', cn_id=cn.id))
                ))

    def set_selects(self):
        """Populate choices for select (and select multiple) fields."""
        self.parent_cn.choices = select_field_choices(
            items=self.index.common_names,
            title_attribute='name',
            order_by='name'
        )
        self.parent_cn.choices.insert(0, (0, 'N/A'))


class AddBotanicalNameForm(Form):
    """Form for adding a new `BotanicalName` to the database.

    Attributes:
        name: String field for the botanical name itself.
        synonyms: String field for synonyms of the botanical name.
        next_page: Radio field for the next page to move on to after submit.

        cn: The `CommonName` to add `BotanicalName` to.
    """
    name = StringField('Botanical Name',
                       validators=[IsBotanicalName(),
                                   Length(1, 64),
                                   NotSpace()])
    synonyms = StringField('Synonyms', validators=[SynonymLength(1, 64),
                                                   NotSpace()])
    next_page = RadioField('After submission, go to',
                           choices=[('add_series', 'Add Series (optional)'),
                                    ('add_cultivar', 'Add Cultivar')],
                           default='add_cultivar')
    submit = SubmitField('Add Botanical Name')

    def __init__(self, cn, *args, **kwargs):
        """Initialize `AddBotanicalNameForm`.

        Args:
            cn: The `CommonName` to add the new `BotanicalName` to.
        """
        super().__init__(*args, **kwargs)
        self.cn = cn

    def validate_name(self, field):
        """Raise a ValidationError if botanical name already exists.

        Note:
            Even though a `BotanicalName` can have multiple `CommonName`
            instances attached to it, adding `CommonName` instances to an
            existing `BotanicalName` should be handled by
            `app.seeds.views.edit_botanical_name`.

        Raises:
            ValidationError: If the desired `BotanicalName` already exists.
        """
        bn = BotanicalName.query\
            .filter(BotanicalName.name == field.data)\
            .one_or_none()
        if bn:
            raise ValidationError(Markup(
                'The botanical name \'{0}\' already exists! Click '
                '<a href="{1}">here</a> if you wish to edit it.'
                .format(bn.name,
                        url_for('seeds.edit_botanical_name', bn_id=bn.id))
            ))


class AddSeriesForm(Form):
    """Form for adding a `Series` to the database.

    Attributes:
        name: DBified string field for `Series` name.
        description: Text field for optional series description.
        position: Select field for where to put series name in relation
            to cultivar name.

        cn: The `CommonName` this `Series` will belong to.
    """
    name = DBifiedStringField('Series Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    position = SelectField('Position',
                           coerce=int,
                           choices=[(Series.BEFORE_CULTIVAR,
                                     'before'),
                                    (Series.AFTER_CULTIVAR,
                                     'after')])
    submit = SubmitField('Add Series')

    def __init__(self, cn, *args, **kwargs):
        """Initialize `AddSeriesForm`.

        Args:
            cn: The `CommonName` added `Series` belongs to.
        """
        super().__init__(*args, **kwargs)
        self.cn = cn

    def validate_name(self, field):
        """Raise `ValidationError` if name  + common name already exists in db.

        Raises:
            ValidationError: If the same series already exists in the database.
        """
        for series in self.cn.series:
            if series.name == dbify(field.data):
                raise ValidationError(Markup(
                    'The common name \'{0}\' already has a series named '
                    '\'{1}\'! Click <a href="{2}">here</a> if you wish to '
                    'edit that series.'
                    .format(self.cn.name,
                            series.name,
                            url_for('seeds.edit_series', series_id=series.id))
                ))


class AddCultivarForm(Form):
    """Form for adding a new `Cultivar` to the database.

    Attributes:
        name: DBified string field for the name of added `Cultivar`.
        botanical_name: Select field for the optional `BotanicalName` for the
            added `Cultivar`.
        series: Select field for optional `Series` added `Cultivar` belongs to.
        thumbnail: File field for uploading thumbnail image.
        description: Text field for optional `Cultivar` HTML description.
        synonyms: String field for optional synonyms of this cultivar.
        new_until: Date field for optional date to mark added `Cultivar` as new
            until.
        in_stock: Checkbox for whether or not added `Cultivar` is in stock.
        active: Checkbox for whether or not added `Cultivar` is to be actively
            replenished when stock gets low.
        visible: Checkbox for whether or not added `Cultivar` should be visible
            on auto-generated pages.

        cn: The `CommonName` added `Cultivar` belongs to.
    """
    name = DBifiedStringField('Cultivar Name',
                              validators=[Length(1, 64), NotSpace()])
    botanical_name = SelectField('Botanical Name', coerce=int)
    series = SelectField('Series', coerce=int)
    thumbnail = FileField('Thumbnail Image',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])
    description = TextAreaField('Description', validators=[NotSpace()])
    synonyms = StringField('Synonyms', validators=[SynonymLength(1, 64),
                                                   NotSpace()])
    new_until = DateField('New until (leave as-is if not new)',
                          format='%m/%d/%Y',
                          default=datetime.date.today())
    in_stock = BooleanField('In Stock', default='checked')
    active = BooleanField('Actively replenished', default='checked')
    visible = BooleanField('Visible on auto-generated pages',
                           default='checked')
    submit = SubmitField('Add Cultivar')

    def __init__(self, cn, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cn = cn
        self.set_selects()

    def validate_name(self, field):
        """Raise `ValidationError` if `Cultivar` already exists.

        Raises:
            ValidationError: If a `Cultivar` with the same name, `CommonName`,
            and (optional) `Series` already exists.
        """
        sr_id = self.series.data if self.series.data else None
        cv = Cultivar.query.filter(
            Cultivar.name == field.data,
            Cultivar.common_name_id == self.cn.id,
            Cultivar.series_id == sr_id
        ).one_or_none()
        if cv:
            raise ValidationError(Markup(
                'The cultivar \'{0}\' already exists! <a href="{1}" '
                'target="_blank">Click here</a> if you wish to edit it.'
                .format(cv.fullname,
                        url_for('seeds.edit_cultivar', cv_id=cv.id))
            ))

    def validate_thumbnail(self, field):
        """Raise a ValidationError if file exists with thumbnail's name.

        Raises:
            ValidationError: If an `Image` with  already exists in database.
        """
        if field.data:
            filename = secure_filename(field.data.filename)
            image = Image.query\
                .filter(Image.filename == filename)\
                .one_or_none()
            if image is not None:
                raise ValidationError('An image named \'{0}\' already exists! '
                                      'Please choose a different name.'
                                      .format(image.filename))

    def set_selects(self):
        """Sets botanical_names, indexes, and common_names from db."""
        self.botanical_name.choices = select_field_choices(
            items=self.cn.botanical_names,
            order_by='name'
        )
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.series.choices = select_field_choices(items=self.cn.series,
                                                   order_by='name')
        self.series.choices.insert(0, (0, 'None'))


class AddPacketForm(Form):
    """Form for adding a packet to a cultivar.

    Attributes:
        sku: String field for product SKU of added packet.
        price: String field for price in US Dollars.
        quantity: String field for amount of seed in added packet.
        units: String fiield for unit of measure for added packet.
        again: Checkbox for whether or not to keep adding
            packets on submit.

        cultivar: The `Cultivar` added `Packet` belongs to.
    """
    sku = StringField('SKU', validators=[Length(1, 32), NotSpace()])
    price = StringField('Price in US dollars',
                        validators=[DataRequired(), NotSpace(), USDollar()])
    quantity = StringField('Quantity', validators=[DataRequired(), NotSpace()])
    units = StringField('Unit of measurement',
                        validators=[Length(1, 32), NotSpace()])
    again = BooleanField('Add another packet after this.')
    submit = SubmitField('Add Packet')

    def __init__(self, cultivar, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cultivar = cultivar

    def validate_quantity(self, field):
        """Raise ValidationError if quantity cannot be parsed as valid.

        Raises:
            ValidationError: If value of quantity cannot be determined to be a
                valid decimal, fraction, or integer.
        """
        if field.data:
            try:
                Quantity(value=field.data.strip())
            except ValueError:
                raise ValidationError('Field must be a valid numerical value. '
                                      '(integer, decimal, fraction, or mixed '
                                      'number)')

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


class AddRedirectForm(Form):
    """Form for adding a redirect to the application.

    Attributes:
        old_path: String field for path to redirect from.
        new_path: String field for path to redirect to.
        status_code: Select field for HTTP redirect status code to use.
    """
    old_path = StringField('Old Path', validators=[DataRequired(),
                                                   NotSpace(),
                                                   ReplaceMe(),
                                                   RRPath()])
    new_path = StringField('New Path', validators=[DataRequired(),
                                                   NotSpace(),
                                                   ReplaceMe(),
                                                   RRPath()])
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
    submit = SubmitField('Add Redirect')

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


class EditIndexForm(Form):
    """Form for editing an existing `Index` from the database.

    Attributes:
        index: The `Index` to edit.
        name: DBified string field for `Index` name.
        description: String field for description.
    """
    id = HiddenField()
    name = DBifiedStringField('Index', validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Edit Index')

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


class EditCommonNameForm(Form):
    """Form for editing an existing common name in the database.

    Attributes:
        cn_id (int): ID of common name to edit.
        index (SelectField): Select for indexes.
        description (TextAreaField): Field for description of common name.
        instructions (TextAreaField): Field for planting instructions.
        name (StringField): CommonName name to edit.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this common name.
    """
    cn_id = None
    index = SelectField('Index',
                        coerce=int,
                        validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    name = StringField('Common Name', validators=[Length(1, 64), NotSpace()])
    parent_cn = SelectField('Subcategory of', coerce=int)
    submit = SubmitField('Edit Common Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def populate(self, cn):
        """Load a common name from the database and populate form with it.

        Args:
            cn (CommonName): A CommonName object to populate the form from.
        """
        self.name.data = cn.name
        self.description.data = cn.description
        self.instructions.data = cn.instructions
        if cn.parent:
            self.parent_cn.data = cn.parent.id
        if cn.synonyms:
            self.synonyms.data = cn.synonyms_string
        self.index.data = cn.index.id

    def set_selects(self):
        """Populate indexes with Indexes from the database."""
        self.index.choices = select_field_choices(model=Index)
        self.parent_cn.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )
        self.parent_cn.choices.insert(0, (0, 'N/A'))

    def validate_name(self, field):
        """Raise ValidationError if conflict would be created."""
        cn = CommonName.query.filter(
            CommonName.name == dbify(field.data),
            CommonName.index_id == self.index.data,
            CommonName.id != int(self.cn_id)
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

    def validate_synonyms(self, field):
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


class EditBotanicalNameForm(Form):
    """Form for editing an existing botanical name in the database.

    Attributes:
        bn (BotanicalName): BotanicalName to edit.
        common_names (SelectMultipleField): Select field for common names this
            botanical name belongs to.
        name (StringField): Field for name of botanical name.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this botanical name.
    """
    bn = None
    common_names = SelectMultipleField('Select Common Names', coerce=int)
    name = StringField('Botanical Name',
                       validators=[Length(1, 64), NotSpace()])
    submit = SubmitField('Edit Botanical Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def populate(self, bn):
        """Load a BotanicalName from the db and populate form with it.

        Args:
            bn (BotanicalName): The botanical name used to populate the form.
        """
        self.name.data = bn.name
        if bn.common_names:
            self.common_names.data = [cn.id for cn in bn.common_names]
        if bn.synonyms:
            self.synonyms.data = bn.synonyms_string

    def set_common_names(self):
        """Set common_name with common names from the database."""
        self.common_names.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )

    def validate_name(self, field):
        """Raise a ValidationError if name is not valid.

        Raises:
            ValidationError: If name is not a valid binomen.
        """
        if not BotanicalName.validate(field.data):
            raise ValidationError('\'{0}\' does not appear to be a valid '
                                  'botanical name. The first word should '
                                  'begin with a capital letter, and the '
                                  'second word should be all lowercase.'.
                                  format(field.data))
        bn = BotanicalName.query.filter(
            BotanicalName.name == field.data.strip(),
            BotanicalName.id != self.bn.id
        ).one_or_none()
        if bn:
            raise ValidationError(Markup(
                'The botanical name \'{0}\' already exists under the common '
                'name(s) {1}. <a href="{2}" target="_blank">Click here</a> if '
                'you wish to edit it.'
                .format(bn.name,
                        ', '.join([cn.name for cn in bn.common_names]),
                        url_for('seeds.edit_botanical_name', bn_id=bn.id))
            ))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are invalid.

        Raises:
            ValidationError: If any synonym is the same as name, or if any
                synonym is too long.
            """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                synonym = synonym.strip()
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')
                if not BotanicalName.validate(synonym):
                    raise ValidationError('The synonym \'{0}\' does not '
                                          'appear to be a valid botanical '
                                          'name.'.format(synonym))


class EditSeriesForm(Form):
    """Form for editing a Series to the database.

    Attributes:
        sr_id (int): ID of Series to edit.
        common_name (SelectField): Field for selecting a common name.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
        position (SelectField): Field for selecting where series name goes in
            relation to cultivar name.
        submit (SubmitField): Submit button.
    """
    sr_id = None
    common_name = SelectField('Select Common Name', coerce=int)
    description = TextAreaField('Description', validators=[NotSpace()])
    name = StringField('Series Name', validators=[Length(1, 64), NotSpace()])
    position = SelectField('Position',
                           coerce=int,
                           choices=[(Series.BEFORE_CULTIVAR,
                                     'before'),
                                    (Series.AFTER_CULTIVAR,
                                     'after')])
    submit = SubmitField('Edit Series')

    def set_common_name(self):
        """Set common name choices with common names from db."""
        self.common_name.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )

    def populate(self, series):
        """Populate fields with information from a db entry."""
        self.name.data = series.name
        self.common_name.data = series.common_name.id
        self.description.data = series.description
        self.position.data = series.position if series.position else 0

    def validate_name(self, field):
        """Raise ValidationError if other Series exists with same name + CN."""
        sr = Series.query.filter(
            Series.name == dbify(field.data),
            Series.common_name_id == int(self.common_name.data),
            Series.id != self.sr_id
        ).one_or_none()
        if sr:
            raise ValidationError(Markup(
                'A series named \'{0}\' already belongs to the common name '
                '\{1}\'. <a href="{2}" target="_blank">Click here</a> if you '
                'wish to edit it.'
                .format(sr.name,
                        sr.common_name.name,
                        url_for('seeds.edit_series', series_id=sr.id))
            ))


class EditCultivarForm(Form):
    """Form for editing an existing cultivar in the database.

    Attributes:
        cv_id (int): Hidden field containing id of cultivar.
        botanical_name (SelectField): Field for selecting botanical name for
            this cultivar.
        common_name (SelectField): Field for selecting common name for this
            cultivar.
        description (TextAreaField): Field for description of cultivar.
        active (BooleanField): Field for whether this cultivar is dropped or
            active.
        visible (BooleanField): Field for whether or not this cultivar is
            shown on auto-generated pages.
        in_stock (Boolean): Field for whether or not cultivar is in stock.
        name (StringField): Field for name of cultivar.
        series (SelectField): Field for selecting a series this cultivar
            belongs to, if applicable.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this cultivar.
        thumbnail (FileField): Field for uploading a thumbnail for this
            cultivar.
    """
    cv_id = None
    botanical_name = SelectField('Botanical Name', coerce=int)
    common_name = SelectField('Common Name',
                              coerce=int,
                              validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    new_until = DateField('New until (leave as-is if not new)',
                          format='%m/%d/%Y',
                          default=datetime.date.today())
    active = BooleanField('Actively replenished')
    visible = BooleanField('Visible on auto-generated pages')
    in_stock = BooleanField('In Stock')
    name = StringField('Cultivar Name', validators=[Length(1, 64), NotSpace()])
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Edit Cultivar')
    synonyms = StringField('Synonyms', validators=[NotSpace()])
    thumbnail = FileField('New Thumbnail',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Set choices for all select fields with values from database."""
        self.botanical_name.choices = select_field_choices(model=BotanicalName,
                                                           order_by='name')
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.common_name.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )
        self.series.choices = select_field_choices(model=Series,
                                                   order_by='name')
        self.series.choices.insert(0, (0, 'N/A'))

    def populate(self, cultivar):
        """Populate form with data from a Cultivar object.

        Args:
            cultivar (Cultivar): The cultivar to populate this form with.
        """
        if cultivar.botanical_name:
            self.botanical_name.data = cultivar.botanical_name.id
        if cultivar.common_name:
            self.common_name.data = cultivar.common_name.id
        self.description.data = cultivar.description
        if cultivar.in_stock:
            self.in_stock.data = True
        if cultivar.active:
            self.active.data = True
        if not cultivar.invisible:
            self.visible.data = True
        self.name.data = cultivar.name
        if cultivar.series:
            self.series.data = cultivar.series.id
        if cultivar.synonyms:
            self.synonyms.data = cultivar.synonyms_string

    def validate_name(self, field):
        """Raise ValidationError if changes would create duplicate cultivar."""
        cv = Cultivar.query.filter(
            Cultivar.name == dbify(field.data),
            Cultivar.common_name_id == self.common_name.data,
            Cultivar.series_id == self.series.data if self.series.data else
            Cultivar.series_id == None,  # noqa
            Cultivar.id != self.cv_id
        ).one_or_none()
        if cv:
            raise ValidationError('The cultivar \'{0}\' already exists!'
                                  .format(cv.fullname))

    def validate_botanical_name(self, field):
        """Raise ValidationError if bot. name not in selected CommonName.

        Raises:
            ValidationError: If selected botanical name does not belong to
                selected common name.
        """
        if field.data:
            bn = BotanicalName.query.get(field.data)
            if int(self.common_name.data) not in\
                    [cn.id for cn in bn.common_names]:
                bn_url = url_for('seeds.edit_botanical_name', bn_id=bn.id)
                raise ValidationError(
                    Markup('The selected botanical name does not belong to '
                           'the selected common name. <a href="{0}">Click '
                           'here</a> if you would like to edit the botanical '
                           'name \'{1}\''.format(bn_url, bn.name))
                )

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are too long.

        Raises:
            ValidationError: If any synonym is same as name, or any synonym is
                too long.
        """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if synonym == self.name.data:
                    raise ValidationError('\'{0}\' can\'t have itself as a '
                                          'synonym!'.format(self.name.data))
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')


class EditPacketForm(Form):
    """Form for adding a packet to a cultivar.

    Attributes:
        pkt (Packet): The packet to edit.
        price (StringField): Field for price in US Dollars.
        quantity (StringField): Field for amount of seed in a packet.
        units (StringField): Field for unit of measurement.
        sku (StringField): Field for product SKU.
        submit (SubmitField): Submit button.
    """
    pkt = None
    price = StringField('Price in US dollars',
                        validators=[DataRequired(), NotSpace(), USDollar()])
    quantity = StringField('Quantity', validators=[DataRequired(), NotSpace()])
    units = StringField('Unit of measurement',
                        validators=[Length(1, 32), NotSpace()])
    sku = StringField('SKU', validators=[Length(1, 32), NotSpace()])
    submit = SubmitField('Edit Packet')

    def populate(self, packet):
        """Populate form elements with data from database.

        Args:
            packet (Packet): The packet to populate this form with.
        """
        self.price.data = packet.price
        self.units.data = packet.quantity.units
        self.quantity.data = packet.quantity.value
        self.sku.data = packet.sku

    def validate_quantity(self, field):
        """Raise ValidationError if quantity cannot be parsed as valid.

        Raises:
            ValidationError: If value of quantity cannot be determined to be a
                valid decimal, fraction, or integer.
        """
        if field.data:
            try:
                Quantity(value=field.data.strip())
            except ValueError:
                raise ValidationError('Field must be a valid numerical value. '
                                      '(integer, decimal, fraction, or mixed '
                                      'number)')

    def validate_sku(self, field):
        """Raise ValidationError if SKU belongs to another packet."""
        pkt = Packet.query.filter(Packet.sku == field.data.strip(),
                                  Packet.id != self.pkt.id).one_or_none()
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


class RemoveBotanicalNameForm(Form):
    """Form for removing a botanical name."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Botanical Name')


class RemoveIndexForm(Form):
    """Form for removing an index.

    Attributes:
        idx (Index): The Index to remove.
        move_to (SelectField): Field for selecting Index to move children of
            this index to when deleting it.
        verify_removal (BooleanField): Field to confirm deletion should happen.
        submit (SubmitField): Submit button.
    """
    idx = None
    move_to = SelectField('Move common names and cultivars in this index '
                          'to', coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Index')

    def set_move_to(self):
        """Set move_to SelectField with other Indexes.

        Raises: ValueError if no other indexes exist.
        """
        idxs = Index.query.filter(Index.id != self.idx.id).all()
        if idxs:
            self.move_to.choices = [(idx.id, idx.name) for idx in idxs]
        else:
            raise ValueError('Cannot delete index with no other index to move '
                             'its common names to!')


class RemoveCommonNameForm(Form):
    """Form for removing a common name.

    Attributes:
        move_to (SelectField): Field for selecting CommonName to move orphans
            to.
        verify_removal (BooleanField): Field that must be checked for removal
            of CommonName.
        submit (SubmitField): Submit button.
    """
    move_to = SelectField('Move botanical names and cultivars associated with '
                          'this common name to', coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Common Name')

    def set_move_to(self, cn_id):
        """Set move_to SelectField with other CommonNames.

        Args:
            cn_id: The id of the CommonName to be removed.
        """
        cns = CommonName.query.filter(CommonName.id != cn_id,
                                      ~CommonName.invisible).all()
        self.move_to.choices = [(cn.id, cn.name) for cn in cns]


class RemovePacketForm(Form):
    """Form for removing a packet.

    Attributes:
        verify_removal (BooleanField): Field that must be checked for removal
            of packet.
        submit (SubmitField): Submit button.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Packet')


class RemoveCultivarForm(Form):
    """Form for removing a cultivar.

    Attributes:
        delete_images (BooleanField): Field for whether or not to delete images
            associated with cultivar being removed.
        verify_removal (BooleanField): Field that must be checked for removal
            of cultivar.
        submit (SubmitField): Submit button.
    """
    delete_images = BooleanField('Also delete all images for this cultivar')
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Cultivar')


class RemoveSeriesForm(Form):
    """Form for removing a series.

    Attributes:
        verify_removal (BooleanField): Field that must be checked for removal
            of series.
        submit (SubmitField): Submit button.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Series')


class SelectBotanicalNameForm(Form):
    """Form for selecting a botanical name.

    Attributes:
        name (SelectField): Field for selecting a botanical name.
        submit (SubmitField): Submit button.
    """
    botanical_name = SelectField('Select Botanical Name', coerce=int)
    submit = SubmitField('Submit')

    def set_botanical_name(self):
        """Populate names with BotanicalNames from the database."""
        self.botanical_name.choices = select_field_choices(model=BotanicalName,
                                                           order_by='name')


class SelectIndexForm(Form):
    """Form for selecting an index.

    Attributes:
        index (SelectField): Field for selecting an index.
        submit (SubmitField): Submit button.
    """
    index = SelectField('Select Index', coerce=int)
    submit = SubmitField('Submit')

    def set_index(self):
        """Populate index with Indexes from the database."""
        self.index.choices = select_field_choices(model=Index)


class SelectCommonNameForm(Form):
    """Form for selecting a common name.

    Attributes:
        common_name (SelectField): Field for selecting a common name.
        submit (SubmitField): Submit button.
    """
    common_name = SelectField('Select Common Name', coerce=int)
    submit = SubmitField('Submit')

    def set_common_name(self):
        """Populate common_name with CommonNames from the database."""
        self.common_name.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )


class SelectPacketForm(Form):
    """Form for selecting a packet.

    Attributes:
        packet (SelectField): Field for selecting a packet.
        submit (SubmitField): Submit button.
    """
    packet = SelectField('Select Packet', coerce=int)
    submit = SubmitField('Submit')

    def set_packet(self):
        """Populate packet with Packets from database."""
        self.packet.choices = select_field_choices(model=Packet,
                                                   order_by='sku',
                                                   title_attribute='info')


class SelectCultivarForm(Form):
    """Form for selecting a cultivar.

    Attributes:
        cultivar (SelectField): Field for selecting a cultivar.
        submit (SubmitField): Submit button
    """
    cultivar = SelectField('Select Cultivar', coerce=int)
    submit = SubmitField('Submit')

    def set_cultivar(self):
        """Populate cultivar with Cultivars from the database."""
        self.cultivar.choices = select_field_choices(model=Cultivar,
                                                     order_by='name')


class SelectSeriesForm(Form):
    """Form for selecting a series.

    Attributes:
        series (SelectField): Field for selecting a series.
        submit (SubmitField): Submit button.
    """
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Submit')

    def set_series(self):
        """Populate series with Series from the database."""
        self.series.choices = select_field_choices(model=Series,
                                                   order_by='name')

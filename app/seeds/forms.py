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
from wtforms.validators import DataRequired, Length, Optional
from app.redirects import RedirectsFile
from .models import (
    BotanicalName,
    dbify,
    Section,
    CommonName,
    Image,
    Index,
    Packet,
    Quantity,
    Cultivar
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
        if min_length <= max_length:
            self.min_length = min_length
            self.max_length = max_length
        else:
            raise ValueError('min_length can\'t be larger than max_length!')
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
        description: Text field for the optional description of a `CommonName`.
        instructions: Text field for optional planting instructions.
        synonyms: Text field for optional synonyms of added `CommonName`.
        next_page: Radio field to select page to redirect to after submitting
            a `CommonName`.

        index: The `Index` added `CommonName` will be under.
    """
    name = DBifiedStringField('Common Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    synonyms = StringField('Synonyms',
                           validators=[NotSpace(), SynonymLength(0, 64)])
    visible = BooleanField('Show on auto-generated pages', default='checked')
    next_page = RadioField(
        'After submission, go to',
        choices=[('add_botanical_name', 'Add Botanical Name (optional)'),
                 ('add_section', 'Add Section (optional)'),
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
    next_page = RadioField(
        'After submission, go to',
        choices=[('add_section', 'Add Section (optional)'),
                 ('add_cultivar', 'Add Cultivar')],
        default='add_cultivar'
    )
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


class AddSectionForm(Form):
    """Form for adding a `Section` to the database.

    Attributes:
        name: DBified string field for `Section` name.
        description: Text field for optional section description.

        cn: The `CommonName` this `Section` will belong to.
    """
    name = DBifiedStringField('Section Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Add Section')

    def __init__(self, cn, *args, **kwargs):
        """Initialize `AddSectionForm`.

        Args:
            cn: The `CommonName` added `Section` belongs to.
        """
        super().__init__(*args, **kwargs)
        self.cn = cn

    def validate_name(self, field):
        """Raise `ValidationError` if name  + common name already exists in db.

        Raises:
            ValidationError: If the section already exists in the database.
        """
        for section in self.cn.sections:
            if section.name == dbify(field.data):
                raise ValidationError(Markup(
                    'The common name \'{0}\' already has a section named '
                    '\'{1}\'! Click <a href="{2}">here</a> if you wish to '
                    'edit that section.'
                    .format(self.cn.name,
                            section.name,
                            url_for('seeds.edit_section',
                                    section_id=section.id))
                ))


class AddCultivarForm(Form):
    """Form for adding a new `Cultivar` to the database.

    Attributes:
        name: DBified string field for the name of added `Cultivar`.
        botanical_name: Select field for the optional `BotanicalName` for the
            added `Cultivar`.
        section: Select field for optional `Section` for added `Cultivar`.
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
    section = SelectField('Section', coerce=int)
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
        self.section.choices = select_field_choices(items=self.cn.sections,
                                                    order_by='name')
        self.section.choices.insert(0, (0, 'None'))


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
        index_id: Select field for `Index` edited `CommonName` belongs to.
        name: DBified string field for name of `CommonName`.
        description: Text field for `CommonName` description.
        instructions Text field for planting instructions.
        synonyms_string: String field for synonyms of edited `CommonName`.
    """
    id = HiddenField()
    index_id = SelectField('Index',
                           coerce=int,
                           validators=[DataRequired()])
    name = DBifiedStringField('Common Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    synonyms_string = StringField('Synonyms', validators=[NotSpace()])
    submit = SubmitField('Edit Common Name')

    def __init__(self, *args, **kwargs):  # pragma: no cover
        super().__init__(*args, **kwargs)
        self.set_selects()

    def set_selects(self):
        """Populate indexes with Indexes from the database."""
        self.index_id.choices = select_field_choices(model=Index)

    def validate_name(self, field):
        """Raise ValidationError if conflict would be created."""
        cn = CommonName.query.filter(
            CommonName.name == dbify(field.data),
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


class EditBotanicalNameForm(Form):
    """Form for editing an existing botanical name in the database.

    Attributes:
        id: The unique id of edited `BotanicalName`.
        name: String field for name of botanical name.
        common_names: Select multiple field for common names edited botanical
            name belongs to.
        synonyms_string: String field for synonyms of this botanical name.
    """
    id = HiddenField()
    name = StringField('Botanical Name',
                       validators=[Length(1, 64),
                                   IsBotanicalName(),
                                   NotSpace()])
    common_names = SelectMultipleField('Select Common Names', coerce=int)
    synonyms_string = StringField('Synonyms', validators=[NotSpace()])
    submit = SubmitField('Edit Botanical Name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()
        if not self.common_names.data:  # Don't overwrite values from formdata!
            cns = kwargs['obj'].common_names
            self.common_names.data = [cn.id for cn in cns]

    def set_selects(self):
        """Set select fields."""
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

    def validate_synonyms_string(self, field):
        """Raise a ValidationError if any synonyms are invalid.

        Raises:
            ValidationError: If any synonym is not a valid `BotanicalName`,  or
                if any synonym is too long.
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


class EditSectionForm(Form):
    """Form for editing a Section to the database.

    Attributes:
        id: The unique id of edited `Section`.
        name: DBified string field for `Section` name.
        common_name_id: Select field for `CommonName` section belongs to.
        description: Text field for `Section` description.
    """
    id = HiddenField()
    common_name_id = SelectField('Select Common Name', coerce=int)
    name = DBifiedStringField('Section Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Edit Section')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()

    def set_selects(self):
        """Set select choices."""
        self.common_name_id.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )

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


class EditCultivarForm(Form):
    """Form for editing an existing cultivar in the database.

    Attributes:
        id: Unique ID for `Cultivar` to be edited.
        common_name_id: Select field for `CommonName` of edited `Cultivar`.
        botanical_name_id: Select field for `BotanicalName` of `Cultivar`.
        section_id: Select field for `Section` `Cultivar` is in, if any.
        name: DBified string field for `Cultivar` name, excluding section and
            common name.
        description: Text field for HTML description of `Cultivar`.
        thumbnail: File field for thumbnail upload.
        synonyms_string: String field for synonyms of `Cultivar`.
        new_until: Date field for when `Cultivar` will no longer be marked as
            new, if applicable.


    """
    id = HiddenField()
    common_name_id = SelectField('Common Name',
                                 coerce=int,
                                 validators=[DataRequired()])
    botanical_name_id = SelectField('Botanical Name', coerce=int)
    section_id = SelectField('Select Section', coerce=int)
    name = DBifiedStringField('Cultivar Name',
                              validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    thumbnail = FileField('New Thumbnail',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])
    synonyms_string = StringField('Synonyms', validators=[NotSpace()])
    new_until = DateField('New until (leave as-is if not new)',
                          format='%m/%d/%Y',
                          default=datetime.date.today(),
                          validators=[Optional()])
    active = BooleanField('Actively replenished')
    visible = BooleanField('Visible on auto-generated pages')
    in_stock = BooleanField('In Stock')
    submit = SubmitField('Edit Cultivar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()

    def set_selects(self):
        """Set choices for all select fields with values from database."""
        self.botanical_name_id.choices = select_field_choices(
            model=BotanicalName,
            order_by='name'
        )
        self.botanical_name_id.choices.insert(0, (0, 'None'))
        self.common_name_id.choices = select_field_choices(
            model=CommonName,
            title_attribute='select_field_title',
            order_by='name'
        )
        self.section_id.choices = select_field_choices(model=Section,
                                                       order_by='name')
        self.section_id.choices.insert(0, (0, 'N/A'))

    def validate_name(self, field):
        """Raise ValidationError if changes would create duplicate cultivar."""
        cn_id = self.common_name_id.data
        sec_id = self.section_id.data if self.section_id.data else None
        cv = Cultivar.query.filter(
            Cultivar.name == dbify(field.data),
            Cultivar.common_name_id == cn_id,
            Cultivar.section_id == sec_id,
            Cultivar.id != self.id.data
        ).one_or_none()
        if cv:
            raise ValidationError('The cultivar \'{0}\' already exists!'
                                  .format(cv.fullname))

    def validate_botanical_name_id(self, field):
        """Raise ValidationError if bot. name not in selected CommonName.

        Raises:
            ValidationError: If selected botanical name does not belong to
                selected common name.
        """
        if field.data:
            bn = BotanicalName.query.get(field.data)
            cnids = [cn.id for cn in bn.common_names]
            if self.common_name_id.data not in cnids:
                bn_url = url_for('seeds.edit_botanical_name', bn_id=bn.id)
                raise ValidationError(Markup(
                    'The selected botanical name does not belong to the '
                    'selected common name. <a href="{0}">Click here</a> if '
                    'you would like to edit the botanical name \'{1}\''
                    .format(bn_url, bn.name)
                ))

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


class EditPacketForm(Form):
    """Form for adding a packet to a cultivar.

    Attributes:
        id: Unique ID of `Packet`.
        sku: String field for `Packet` product SKU.
        price: String field for price in US dollars.
        qty_val: String field for quantity of seeds in packet.
        units: String field for unit of measure for quantity of seeds.
    """
    id = HiddenField()
    cultivar_id = SelectField('Cultivar', coerce=int)
    sku = StringField('SKU', validators=[Length(1, 32), NotSpace()])
    price = StringField('Price in US dollars',
                        validators=[DataRequired(), NotSpace(), USDollar()])
    qty_val = StringField('Quantity', validators=[DataRequired(), NotSpace()])
    units = StringField('Unit of measurement',
                        validators=[Length(1, 32), NotSpace()])
    submit = SubmitField('Edit Packet')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()
        if not self.qty_val.data:
            self.qty_val.data = str(kwargs['obj'].quantity.value)
        if not self.units.data:
            self.units.data = kwargs['obj'].quantity.units

    def set_selects(self):
        """Set select fields."""
        self.cultivar_id.choices = select_field_choices(
            model=Cultivar,
            title_attribute='fullname',
            order_by='slug'
        )
        print(self.cultivar_id.data)

    def validate_qty_val(self, field):
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


class RemoveIndexForm(Form):
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


class RemoveCommonNameForm(Form):
    """Form for removing a `CommonName` from the database.

    Attributes:
        move_to: Select field for `CommonName` to move children to.
        verify_removal: Checkbox for whether or not to remove `CommonName`.

        cn: The `CommonName` to remove.
    """
    move_to = SelectField('Move botanical names and cultivars associated with '
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


class RemoveBotanicalNameForm(Form):
    """Form for removing a `BotanicalName` from the database.

    Attributes:
        verify_removal: Checkbox for whether or not to remove `BotanicalName`.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Botanical Name')


class RemoveSectionForm(Form):
    """Form for removing a `Section` from the database.

    Attributes:
        verify_removal: Checkbox for whether or not to remove `Section`.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Section')


class RemoveCultivarForm(Form):
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


class RemovePacketForm(Form):
    """Form for removing a `Packet` from the database.

    Attributes:
        verify_removal: Checkbox for whether or not to remove `Packet`.
    """
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Packet')


class SelectIndexForm(Form):
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


class SelectCommonNameForm(Form):
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


class SelectBotanicalNameForm(Form):
    """Form for selecting a botanical name.

    Attributes:
        botanical_name: Select field for `BotanicalName`.
    """
    botanical_name = SelectField('Select Botanical Name', coerce=int)
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_select()

    def set_select(self):
        """Populate `botanical_name`."""
        self.botanical_name.choices = select_field_choices(model=BotanicalName,
                                                           order_by='name')


class SelectSectionForm(Form):
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


class SelectCultivarForm(Form):
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


class SelectPacketForm(Form):
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

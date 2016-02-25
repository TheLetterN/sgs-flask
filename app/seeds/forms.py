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

from decimal import Decimal
from titlecase import titlecase
from flask import current_app, Markup, url_for
from werkzeug import secure_filename
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError
)
from wtforms.validators import DataRequired, Length
from app import dbify
from app.redirects import RedirectsFile
from .models import (
    BotanicalName,
    Index,
    CommonName,
    Image,
    Packet,
    Quantity,
    Cultivar,
    Series
)


IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']


class NotSpace(object):
    """Validator raises a ValidationError if a field is just whitespace."""
    def __init__(self, message=None):
        if not message:
            message = 'Field cannot consist entirely of whitespace.'
        self.message = message

    def __call__(self, form, field):
        if field.data and field.data.isspace():
            raise ValidationError(self.message)


class ReplaceMe(object):
    """Validator for if a field still contains <replace me> data."""
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


class USDollar(object):
    """Validator raises ValidationError if can't be parsed as a USD value."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid US Dollar value.'
        self.message = message

    def __call__(self, form, field):
        if field:
            try:
                Decimal(field.data.replace('$', '').strip())
                if '.' in field.data and len(field.data.split('.')[-1]) > 2:
                    raise ValidationError(self.message)
            except:
                raise ValidationError(self.message)


def botanical_name_select_list(obj=None):
    """Generate a list of BotanicalNames for populating Select fields.
    Either load the botanical names belonging to passed object, or all if no
    object is passed.

    Attributes:
        obj (object): A database object with a botanical_names relationship
            to gather botanical names from.

    Returns:
        list: A list of tuples containing the id and name of each botanical
            name in the database.
    """
    bn_list = []
    if obj and obj.botanical_names:
        items = obj.botanical_names
    else:
        items = BotanicalName.query.order_by('_name')
    for bn in items:
        if not bn.invisible:
            bn_list.append((bn.id, bn.name))
    return bn_list


def index_select_list(obj=None):
    """Generate a list of Indexes for populating Select fields.

    Attributes:
        obj (object): A database object with an indexes relationship to gather
            indexes from.

    Returns:
        list: A list of tuples containing the id and name of each index
            in the database.

    Raises:
        ValueError: If passed object has no indexes.
    """
    if obj and obj.indexes:
        items = obj.indexes
    else:
        items = Index.query.order_by('id')
    return [(index.id, index.name) for index in items]


def common_name_select_list():
    """Generate a list of all CommonNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each common name
            in the database.
    """
    cn_list = []
    for cn in CommonName.query.order_by('_name'):
        if not cn.invisible:
            val = cn.name + ' (' + cn.index.name + ')' if cn.index else cn.name
            cn_list.append((cn.id, val))
    return cn_list


def packet_select_list():
    """Generate a list of all Packets for populating Select fields.

    Returns:
        list: A list of tuples containing the id and info of each packet in
            the database.
    """
    packets = Packet.query.all()
    packets.sort(key=lambda x: x.cultivar.common_name.name)
    return [(pkt.id, '{0}, {1}: {2}'.
                     format(pkt.cultivar.common_name.name,
                            pkt.cultivar.name_with_series,
                            pkt.info)) for pkt in packets]


def series_select_list(obj=None):
    """Generate a list of all Series for populating Select fields.

    Attributes:
        obj (object): Optional object with a relationship with series to draw
            series objects from.

    Returns:
        list: A list of tuples with id and name of each series.
    """
    if obj:
        sl = [(series.id, series.name) for series in obj.series]\
            if obj.series else []
    else:
        sl = [(series.id,  series.common_name.name + ', ' + series.name) for
              series in Series.query.all()]
    return sl


def cultivar_select_list(obj=None):
    """"Generate a list of all Seeds for populating select fields.

    Attributes:
        obj (object): Optional object with a cultivars relationship to draw
            cultivars from.

    Returns:
        list: A list of tuples containing the ids and full names of each
            cultivar in the database.
    """
    if obj and obj.cultivars:
        items = obj.cultivars
    else:
        items = Cultivar.query.order_by('_name')
    return [(cv.id, cv.fullname) for cv in items]


class AddIndexForm(Form):
    """Form for adding a new index to the database.

    Attributes:
        index (StringField): Field for the index name.
        description (TextAreaField): Field for the index's description.
        submit (SubmitField): Submit button.
    """
    index = StringField('Index', validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Add Index')

    def validate_index(self, field):
        """Raise a ValidationError if submitted index already exists.

        Raises:
            ValidationError: If submitted index already exists in the
                database.
        """
        idx = Index.query.filter(Index.name == dbify(field.data)).one_or_none()
        if idx:
            idx_url = url_for('seeds.edit_index', idx_id=idx.id)
            raise ValidationError(
                Markup('\'{0}\' already exists in the database. <a '
                       'href="{1}">Click here</a> to edit it.'
                       .format(idx.name, idx_url))
            )


class AddCommonNameForm(Form):
    """Form for adding a new common name to the database.

    Attributes:
        idx_id (int): ID for Index to use in validation.
        description (TextAreaField): Field for description of common name.
        gw_common_names (SelectMultipleField): Select field for common names
            that grow well with this common name.
        gw_cultivars (SelectMultipleField): Select field for cultivars that
            grow well with this common name.
        instructions (TextAreaField): Field for planting instructions.
        name (StringField): Field for the common name itself.
        next_page (RadioField): Page to move on to after form submission.
        parent_cn (SelectField)" Field to optionally make this common name a
            subcategory of another.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this common name.
    """
    idx_id = None
    description = TextAreaField('Description', validators=[NotSpace()])
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_cultivars = SelectMultipleField('Cultivars', coerce=int)
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    name = StringField('Common Name', validators=[Length(1, 64), NotSpace()])
    next_page = RadioField(
        'After submission, go to',
        choices=[('add_botanical_name', 'Add Botanical Name (optional)'),
                 ('add_series', 'Add Series (optional)'),
                 ('add_cultivar', 'Add Cultivar')],
        default='add_cultivar'
    )
    parent_cn = SelectField('Subcategory of', coerce=int)
    submit = SubmitField('Add Common Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def set_selects(self):
        """Populate indexes with Indexes from the database."""
        self.gw_common_names.choices = common_name_select_list()
        self.gw_cultivars.choices = cultivar_select_list()
        self.parent_cn.choices = common_name_select_list()
        self.parent_cn.choices.insert(0, (0, 'N/A'))

    def validate_name(self, field):
        """Raise ValidationError if Index + CommonName combo already exists.

        Args:
            field: The field to validate: .name.

        Raises:
            ValidationError: If a CommonName with the same name and Index
                already exists.
        """
        cn = CommonName.query.filter(
            CommonName.name == titlecase(field.data),
            CommonName.index_id == self.idx_id
        ).one_or_none()
        if cn:
            raise ValidationError(Markup(
                'The common name \'{0}\' already exists under the index '
                '\'{1}\'. <a href="{2}">Click here</a> if you wish to edit it.'
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


class AddBotanicalNameForm(Form):
    """Form for adding a new botanical name to the database.

    Attributes:
        cn (CommonName): The CommonName this BotanicalName will belong to.
        name (StringField): Field for botanical name.
        next_page (RadioField): The next page to move on to after submit.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms.
    """
    cn = None
    name = StringField('Botanical Name',
                       validators=[Length(1, 64), NotSpace()])
    next_page = RadioField('After submission, go to',
                           choices=[('add_series', 'Add Series (optional)'),
                                    ('add_cultivar', 'Add Cultivar')],
                           default='add_cultivar')
    submit = SubmitField('Add Botanical Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def validate_name(self, field):
        """Raise a ValidationError if name is invalid, or already exists for
        given common name.

        Raises:
            ValidationError: If name is not in valid binomial format, or if
                BotanicalName already exists belonging to common name.
        """
        if not BotanicalName.validate(field.data):
            raise ValidationError('\'{0}\' does not appear to be a valid '
                                  'botanical name. The first word should '
                                  'begin with a capital letter, and the '
                                  'second word should be all lowercase.'.
                                  format(field.data))
        for bn in self.cn.botanical_names:
            if bn._name == field.data:
                raise ValidationError(Markup(
                    'The botanical name \'{0}\' already belongs to the common '
                    'name \'{1}\'. <a href="{2}" target="_blank">Click here'
                    '</a> if you wish to edit it.'
                    .format(bn._name,
                            self.cn.name,
                            url_for('seeds.edit_botanical_name', bn_id=bn.id))
                ))

    def validate_synonyms(self, field):
        """Raise a ValidationError if synonyms or a synonym are invalid.

        Raises:
            ValidationError: if any synonym is too long, or if any synonym is
            not in valid binomial format.
        """
        if field.data:
            synonyms = field.data.split(', ')
            bad_syns = []
            for synonym in synonyms:
                synonym = synonym.strip()
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')
                if not BotanicalName.validate(synonym):
                    bad_syns.append(synonym)
            if bad_syns:
                raise ValidationError('One or more synonyms do not appear to '
                                      'be valid botanical names: {0}'
                                      .format(', '.join(bad_syns)))


class AddSeriesForm(Form):
    """Form for adding a Series to the database.

    Attributes:
        cn (CommonName): The CommonName this Series will belong to.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
        position (SelectField): Field for where to put series name in relation
            to cultivar name.
        submit (SubmitField): Submit button.
    """
    cn = None
    description = TextAreaField('Description', validators=[NotSpace()])
    name = StringField('Series Name', validators=[Length(1, 64), NotSpace()])
    position = SelectField('Position',
                           coerce=int,
                           choices=[(Series.BEFORE_CULTIVAR,
                                     'before'),
                                    (Series.AFTER_CULTIVAR,
                                     'after')])
    submit = SubmitField('Add Series')

    def validate_name(self, field):
        """Raise ValidationError if name  + common name already exists in db.

        Raises:
            ValidationError: If series already exists in database.
        """
        for series in self.cn.series:
            if series.name == dbify(field.data):
                raise ValidationError('The series \'{0}\' already exists '
                                      'belonging to the common name \'{1}\'!'.
                                      format(series.name,
                                             self.cn.name))


class AddCultivarForm(Form):
    """Form for adding a new cultivar to the database.

    Attributes:
        cn_id (int): Common name id used for this cultivar.
        botanical_name (SelectField): Select field for the botanical name
            associated with this cultivar.
        description (TextAreaField): Field for cultivar product description.
        active (BooleanField): Checkbox for whether or not a cultivar is
            active.
        gw_common_names (SelectMultipleField): Select field for common names
            that grow well with this cultivar.
        gw_cultivars (SelectMultipleField): Select field for cultivars that
            grow well with this cultivar.
        in_stock (BooleanField): Checkbox for whether or not this cultivar is
            in stock.
        name (StringField): The cultivar name of the cultivar.
        series (SelectField): Select field for selecting a series this cultivar
            is part of.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this cultivar.
        thumbnail (FileField): Field for uploading thumbnail image.
    """
    cn_id = None
    botanical_name = SelectField('Botanical Name', coerce=int)
    description = TextAreaField('Description', validators=[NotSpace()])
    active = BooleanField('Actively replenished', default='checked')
    visible = BooleanField('Visible in auto-generated pages',
                           default='checked')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_cultivars = SelectMultipleField('Cultivars', coerce=int)
    in_stock = BooleanField('In Stock', default='checked')
    name = StringField('Cultivar Name',
                       validators=[Length(1, 64), NotSpace()])
    series = SelectField('Series', coerce=int)
    submit = SubmitField('Add Cultivar')
    synonyms = StringField('Synonyms', validators=[NotSpace()])
    thumbnail = FileField('Thumbnail Image',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self, cn=None):
        """Sets botanical_names, indexes, and common_names from db.

        Attributes:
            cn (CommonName): Optional common name to refine lists from.
        """
        self.botanical_name.choices = botanical_name_select_list(cn)
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.gw_common_names.choices = common_name_select_list()
        self.gw_cultivars.choices = cultivar_select_list()
        self.series.choices = series_select_list(cn)
        self.series.choices.insert(0, (0, 'None'))

    def validate_name(self, field):
        """Raise ValidationError if cultivar already exists.

        Raises:
            ValidationError: If a cultivar with the same name, common name,
            and (optional)already exists.
        """
        cv = Cultivar.query.filter(
            Cultivar.name == field.data,
            Cultivar.common_name_id == self.cn_id,
            Cultivar.series_id == self.series.data if self.series.data else
            Cultivar.series_id == None  # noqa
        ).one_or_none()
        if cv:
            raise ValidationError(Markup(
                'The cultivar \'{0}\' already exists! <a href="{1}" '
                'target="_blank">Click here</a> if you wish to edit it.'
                .format(cv.fullname,
                        url_for('seeds.edit_cultivar', cv_id=cv.id))
            ))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are invalid.

        Raises:
            ValidationError: If any synonym is too long.
        """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')

    def validate_thumbnail(self, field):
        """Raise a ValidationError if file exists with thumbnail's name.

        Raises:
            ValidationError: If image name already exists in database.
        """
        if field.data:
            image = Image.query.\
                filter_by(filename=secure_filename(field.data.filename)).\
                first()
            if image is not None:
                raise ValidationError('An image named \'{0}\' already exists! '
                                      'Please choose a different name.'
                                      .format(image.filename))


class AddPacketForm(Form):
    """Form for adding a packet to a cultivar.

    Attributes:
        again (BooleanField): Checkbox for whether or not to keep adding
            packets on submit.
        price (StringField): Field for price in US Dollars.
        quantity (StringField): Field for amount of seed in a packet.
        units (StringField): Field for nit of measure for this packet.
        sku (StringField): Field for product SKU of packet.
        submit (SubmitField): Submit button.
    """
    again = BooleanField('Add another packet after this.')
    price = StringField('Price in US dollars',
                        validators=[DataRequired(), NotSpace(), USDollar()])
    quantity = StringField('Quantity', validators=[DataRequired(), NotSpace()])
    units = StringField('Unit of measurement',
                        validators=[Length(1, 32), NotSpace()])
    sku = StringField('SKU', validators=[Length(1, 32), NotSpace()])
    submit = SubmitField('Add Packet')

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
        packet = Packet.query.filter_by(sku=field.data.strip()).one_or_none()
        if packet:
            pkt_url = url_for('seeds.edit_packet', pkt_id=packet.id)
            raise ValidationError(
                Markup('The SKU \'{0}\' is already in use by \'{1}\'. <a '
                       'href="{2}">Click here</a> if you wish to edit it.'
                       .format(packet.sku, packet.cultivar.fullname, pkt_url))
            )


class AddRedirectForm(Form):
    """Form for adding a redirect to the application."""
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
    """Form for editing an existing index in the database.

    Attributes:
        idx_id (int): ID of index to edit.
        name (StringField): Field for index name.
        description (TextAreaField): Field for description.
        submit (SubmitField): Submit button.
    """
    idx_id = None
    name = StringField('Index', validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Edit Index')

    def validate_name(self, field):
        """Raise ValidationError if changing name would result in clash."""
        idx = Index.query.filter(Index.name == dbify(field.data),
                                 Index.id != self.idx_id).one_or_none()
        if idx:
            raise ValidationError(Markup(
                'A different index is already named \'{0}\'. <a href="{1}" '
                'target="_blank">Click here</a> if you would like to edit it.'
                .format(idx.name,
                        url_for('seeds.edit_index', idx_id=idx.id))
            ))

    def populate(self, index):
        """Load index from database and populate form with it.

        Args:
            index (Index): A index object to populate the form from.
        """
        self.name.data = index.name
        self.description.data = index.description


class EditCommonNameForm(Form):
    """Form for editing an existing common name in the database.

    Attributes:
        cn_id (int): ID of common name to edit.
        index (SelectField): Select for indexes.
        description (TextAreaField): Field for description of common name.
        gw_common_names (SelectMultipleField): Field for common names that
            grow well with this one.
        gw_cultivars (SelectMultipleField): Field for cultivars that grow well
            with this common name.
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
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_cultivars = SelectMultipleField('Cultivars', coerce=int)
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
        if cn.gw_common_names:
            self.gw_common_names.data = [gw_cn.id for gw_cn in
                                         cn.gw_common_names]
        if cn.gw_cultivars:
            self.gw_cultivars.data = [gw_cultivar.id for
                                      gw_cultivar in
                                      cn.gw_cultivars]

    def set_selects(self):
        """Populate indexes with Indexes from the database."""
        self.index.choices = index_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_common_names.choices.insert(0, (0, 'None'))
        self.gw_cultivars.choices = cultivar_select_list()
        self.gw_cultivars.choices.insert(0, (0, 'None'))
        self.parent_cn.choices = common_name_select_list()
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
        self.common_names.choices = common_name_select_list()

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
            BotanicalName._name == field.data.strip(),
            BotanicalName.id != self.bn.id
        ).one_or_none()
        if bn:
            raise ValidationError(Markup(
                'The botanical name \'{0}\' already exists under the common '
                'name(s) {1}. <a href="{2}" target="_blank">Click here</a> if '
                'you wish to edit it.'
                .format(bn._name,
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
        self.common_name.choices = common_name_select_list()

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
        gw_common_names (SelectMultipleField): Field for selecting common names
            that grow well with this cultivar.
        gw_cultivars (SelectMultipleField): Field for selecting cultivars that
            grow well with this cultivar.
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
    active = BooleanField('Actively replenished')
    visible = BooleanField('Visible on auto-generated pages')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_cultivars = SelectMultipleField('Cultivars', coerce=int)
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
        self.botanical_name.choices = botanical_name_select_list()
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.common_name.choices = common_name_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_common_names.choices.insert(0, (0, 'None'))
        self.gw_cultivars.choices = cultivar_select_list()
        self.gw_cultivars.choices.insert(0, (0, 'None'))
        self.series.choices = series_select_list()
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
        if cultivar.gw_common_names:
            self.gw_common_names.data = [gw_cn.id for gw_cn in
                                         cultivar.gw_common_names]
        if cultivar.gw_cultivars:
            self.gw_cultivars.data = [gw_cv.id for
                                      gw_cv in
                                      cultivar.gw_cultivars]
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
        self.botanical_name.choices = botanical_name_select_list()


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
        self.index.choices = index_select_list()


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
        self.common_name.choices = common_name_select_list()


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
        self.packet.choices = packet_select_list()


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
        self.cultivar.choices = cultivar_select_list()


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
        self.series.choices = series_select_list()

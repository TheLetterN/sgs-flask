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
from flask import Markup, url_for
from werkzeug import secure_filename
from flask.ext.wtf import Form
from flask.ext.wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DecimalField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    ValidationError
)
from wtforms.validators import DataRequired, Length, Optional
from app import dbify
from .models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Packet,
    Quantity,
    Seed,
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
                    raise ValueError
            except:
                raise ValidationError(self.message)


def botanical_name_select_list():
    """Generate a list of all BotanicalNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each botanical
            name in the database.
    """
    bn_list = []
    for bn in BotanicalName.query.order_by('_name'):
        if not bn.syn_only:
            bn_list.append((bn.id, bn.name))
    return bn_list


def category_select_list():
    """Generate a list of all Categories for populating Select fields.

    Returns:
        list: A list of tuples containing the id and category of each category
            in the database.
    """
    return [(category.id, category.name) for category in
            Category.query.order_by('_name')]


def common_name_select_list():
    """Generate a list of all CommonNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each common name
            in the database.
    """
    cn_list = []
    for cn in CommonName.query.order_by('_name'):
        if not cn.syn_only:
            cn_list.append((cn.id, cn.name))
    return cn_list


def packet_select_list():
    """Generate a list of all Packets for populating Select fields.

    Returns:
        list: A list of tuples containing the id and info of each packet in
            the database.
    """
    packets = Packet.query.all()
    packets.sort(key=lambda x: x.seed.common_name.name)
    return [(pkt.id, '{0}, {1}: {2}'.
                     format(pkt.seed.common_name.name,
                            pkt.seed.name,
                            pkt.info)) for pkt in packets]


def series_select_list():
    """Generate a list of all Series for populating Select fields.

    Returns:
        list: A list of tuples with id and name of each series.
    """
    sl = [(series.id, series.name) for series in Series.query.all()]
    return sl


def seed_select_list():
    """"Generate a list of all Seeds for populating select fields.

    Returns:
        list: A list of tuples containing the ids and strings containing name
            and SKU of each seed in the database.
    """
    seeds = []
    for seed in Seed.query.order_by('_name'):
        if not seed.syn_only:
            seeds.append((seed.id, seed.fullname))
    return seeds


def syn_parents_links(obj):
    """Generate a string containing links to an object's syn_parents.

    Args:
        obj: An object with the syn_parents attribute.

    Returns:
        str: A string listing links to syn_parents of given object.
    """
    if isinstance(obj, BotanicalName):
        return ', '.join(['<a href="{0}">{1}</a>'
                          .format(url_for('seeds.edit_botanical_name',
                                          bn_id=syn_p.id), syn_p.name)
                          for syn_p in obj.syn_parents])
    elif isinstance(obj, CommonName):
        return ', '.join(['<a href="{0}">{1}</a>'
                          .format(url_for('seeds.edit_common_name',
                                          cn_id=syn_p.id), syn_p.name)
                          for syn_p in obj.syn_parents])
    elif isinstance(obj, Seed):
        return ', '.join(['<a href="{0}">{1}</a>'
                          .format(url_for('seeds.edit_seed', seed_id=syn_p.id),
                                  syn_p.fullname)
                          for syn_p in obj.syn_parents])
    else:
        return ''


class AddBotanicalNameForm(Form):
    """Form for adding a new botanical name to the database.

    Attributes:
        common_name (SelectField): Field to select a common name to associate
            with this botanical name.
        name (StringField): Field for botanical name.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms.
    """
    common_name = SelectField('Select Common Name', coerce=int)
    name = StringField('Botanical Name',
                       validators=[Length(1, 64), NotSpace()])
    submit = SubmitField('Add Botanical Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def set_common_names(self):
        """Set common_names with CommonName objects loaded from db."""
        self.common_name.choices = common_name_select_list()

    def validate_name(self, field):
        """Raise a ValidationError if name exists or is invalid.

        Raises:
            ValidationError: If name is not in valid binomial format.
            ValidationError: If a botanical name with the same name already
                exists in the database.
            ValidationError: If a synonym with the same name already exists.
        """
        if not BotanicalName.validate(field.data):
            raise ValidationError('\'{0}\' does not appear to be a valid '
                                  'botanical name. The first word should '
                                  'begin with a capital letter, and the '
                                  'second word should be all lowercase.'.
                                  format(field.data))
        bn = BotanicalName.query.filter_by(name=field.data).first()
        if bn is not None:
            if not bn.syn_only:
                bn_url = url_for('seeds.edit_botanical_name', bn_id=bn.id)
                raise ValidationError(
                    Markup('\'{0}\' already exists as a botanical name for '
                           '\'{1}\'. <a href="{2}">Click here</a> if you '
                           'would like to edit it.'
                           .format(bn.name, bn.common_name.name, bn_url))
                )
            else:
                raise ValidationError(
                    Markup('The botanical name \'{0}\' already exists as a '
                           'synonym of \'{1}\'. You will need to remove it as '
                           'a synonym before adding it here.'
                           .format(bn.name, syn_parents_links(bn)))
                )

    def validate_synonyms(self, field):
        """Raise a ValidationError if synonyms or a synonym are invalid.

        Raises:
            ValidationError: If botanical name itself is present in synonyms.
            ValidationError: If any synonym is too long.
            ValidationError: If any synonym is not in valid binomial format.
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
                if not BotanicalName.validate(synonym):
                    raise ValidationError('The synonym \'{0}\' does not '
                                          'appear to be a valid botanical '
                                          'name!'.format(synonym))


class AddCategoryForm(Form):
    """Form for adding a new category to the database.

    Attributes:
        category (StringField): Field for the category name.
        description (TextAreaField): Field for the category's description.
        submit (SubmitField): Submit button.
    """
    category = StringField('Category', validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Add Category')

    def validate_category(self, field):
        """Raise a ValidationError if submitted category already exists.

        Raises:
            ValidationError: If submitted category already exists in the
                database.
        """
        cat = Category.query.filter_by(name=dbify(field.data)).first()
        if cat is not None:
            cat_url = url_for('seeds.edit_category', cat_id = cat.id)
            raise ValidationError(
                Markup('\'{0}\' already exists in the database. <a '
                       'href="{1}">Click here</a> to edit it.'
                       .format(cat.name, cat_url))
            )


class AddCommonNameForm(Form):
    """Form for adding a new common name to the database.

    Attributes:
        categories (SelectMultipleField): Select field with categories from
            the database to associate with this CommonName.
        description (TextAreaField): Field for description of common name.
        gw_common_names (SelectMultipleField): Select field for common names
            that grow well with this common name.
        gw_seeds (SelectMultipleField): Select field for seeds that grow well
            with this common name.
        instructions (TextAreaField): Field for planting instructions.
        name (StringField): Field for the common name itself.
        parent_cn (selectField)" Field to optionally make this common name a
            subcategory of another.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this common name.
    """
    categories = SelectMultipleField('Select Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
    instructions = TextAreaField('Planting Instructions',
                                 validators=[NotSpace()])
    name = StringField('Common Name', validators=[Length(1, 64), NotSpace()])
    parent_cn = SelectField('Subcategory of', coerce=int)
    submit = SubmitField('Add Common Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def set_selects(self):
        """Populate categories with Categories from the database."""
        self.categories.choices = category_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_seeds.choices = seed_select_list()
        self.parent_cn.choices = common_name_select_list()
        self.parent_cn.choices.insert(0, (0, 'N/A'))

    def validate_name(self, field):
        """Raise a ValidationError if submitted common name already exists.

        Args:
            field: The field to validate: .name.

        Raises:
            ValidationError: If name already in use by another common name.
            ValidationError: If name already in use by a synonym.
        """
        cn = CommonName.query.filter_by(name=titlecase(field.data)).first()
        if cn is not None:
            if not cn.syn_only:
                cn_url = url_for('seeds.edit_common_name', cn_id=cn.id)
                raise ValidationError(
                    Markup('\'{0}\' already exists in the database. <a '
                           'href="{1}">Click here</a> to edit it.'
                           .format(cn.name, cn_url))
                )
            else:
                raise ValidationError(
                    Markup('The common name \'{0}\' already exists as a '
                           'synonym of: \'{1}\'. You will need to remove it '
                           'as a synonym if you wish to add it here.'
                           .format(cn.name, syn_parents_links(cn)))
                )

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are invalid.
        
        Raises:
            ValidationError: If any synonym is the same as common name itself.
            ValidationError: If any synonym too long.
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


class AddPacketForm(Form):
    """Form for adding a packet to a seed.

    Attributes:
        again (BooleanField): Checkbox for whether or not to keep adding
            packets on submit.
        price (StringField): Field for price in US Dollars.
        quantity (StringField): Field for amount of seed in a packet.
        units (StringField): Field for nit of measure for this packet.
        sku (StringField): Field for product SKU of packet.
        submit (SubmitField): Submit button.
    """
    again = BooleanField('Add another packet after this.', default='checked')
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
        packet = Packet.query.filter_by(sku=field.data.strip()).first()
        if packet is not None:
            pkt_url = url_for('seeds.edit_packet', pkt_id = packet.id)
            raise ValidationError(
                Markup('The SKU \'{0}\' is already in use by \'{1}\'. <a '
                       'href="{2}">Click here</a> if you wish to edit it.'
                       .format(packet.sku, packet.seed.fullname, pkt_url))
            )


class AddSeedForm(Form):
    """Form for adding a new seed to the database.

    Attributes:
        botanical_name (SelectField): Select field for selecting the botanical
            name associated with this seed.
        categories (SelectMultipleField): Select field for selecting categories
            associated with seed.
        common_name (SelectMultipleField): Select ield for selecting the common
            name associated with this seed.
        description (TextAreaField): Field for seed product description.
        dropped (BooleanField): Checkbox for whether or not a seed is active.
        gw_common_names (SelectMultipleField): Select field for common names
            that grow well with this seed.
        gw_seeds (SelectMultipleField): Select field for seeds that grow well
            with this seed.
        in_stock (BooleanField): Checkbox for whether or not this seed is in
            stock.
        name (StringField): The cultivar name of the seed.
        series (SelectField): Select field for selecting a series this seed is
            part of.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this seed.
        thumbnail (FileField): Field for uploading thumbnail image.
    """
    botanical_name = SelectField('Select Botanical Name', coerce=int)
    categories = SelectMultipleField('Select Categories', coerce=int)
    common_name = SelectField('Select Common Name',
                              coerce=int,
                              validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    dropped = BooleanField('Dropped/Inactive')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
    in_stock = BooleanField('In Stock', default='checked')
    name = StringField('Seed Name (Cultivar)',
                       validators=[Length(1, 64), NotSpace()])
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Add Seed')
    synonyms = StringField('Synonyms', validators=[NotSpace()])
    thumbnail = FileField('Thumbnail Image',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Sets botanical_names, categories, and common_names from db."""
        self.botanical_name.choices = botanical_name_select_list()
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.categories.choices = category_select_list()
        self.common_name.choices = common_name_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_seeds.choices = seed_select_list()
        self.series.choices = series_select_list()
        self.series.choices.insert(0, (0, 'None'))

    def validate_categories(self, field):
        """Raise ValidationError if any categories not in selected CommonName.

        Raises:
            ValidationError: If any selected categories are not present within
                the selected CommonName.
        """
        cn = CommonName.query.get(self.common_name.data)
        cat_ids = [cat.id for cat in cn.categories]
        for cat_id in field.data:
            if cat_id not in cat_ids:
                cn_url = url_for('seeds.edit_common_name', cn_id=cn.id)
                raise ValidationError(
                    Markup('One or more of selected categories are not '
                           'associated with selected common name \'{0}\'. <a '
                           'href="{1}">Click here</a> if you would like to '
                           'edit \'{0}\'.'.format(cn.name, cn_url)))

    def validate_name(self, field):
        """Raise ValidationError if seed already exists.
        
        Raises:
            ValidationError: If a seed with the same name and common name 
                already exists in the database.
            ValidationError: If the seed name already exists as a synonym."""
        seeds = Seed.query.filter_by(_name=titlecase(field.data)).all()
        for seed in seeds:
            if not seed.syn_only:
                if seed and seed.common_name.id == self.common_name.data:
                    sd_url=url_for('seeds.edit_seed', seed_id=seed.id)
                    raise ValidationError(
                        Markup('A seed named \'{0}\' already exists in the '
                               'database. <a href="{1}">Click here</a> if you '
                               'wish to edit it.'
                               .format(seed.fullname, sd_url))
                    )
            else:
                raise ValidationError(
                    Markup('The seed name \'{0}\' already exists as a synonym '
                           'of: \'{1}\'. You will need to remove it as a '
                           'synonym if you wish to add it here.'
                           .format(seed.name, syn_parents_links(seed)))
                )

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are invalid.
        
        Raises:
            ValidationError: If synonym is the same as this seed's name.
            ValidationError: If synonym is too long.
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


class AddSeriesForm(Form):
    """Form for adding a Series to the database.

    Attributes:
        common_name (SelectField): Field for selecting a common name.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
        submit (SubmitField): Submit button.
    """
    common_name = SelectField('Select Common Name', coerce=int)
    description = TextAreaField('Description', validators=[NotSpace()])
    name = StringField('Series Name', validators=[Length(1, 64), NotSpace()])
    submit = SubmitField('Add Series')

    def set_common_names(self):
        """Set common names choices with common names from db."""
        self.common_name.choices = common_name_select_list()

    def validate_name(self, field):
        """Raise ValidationError if name already exists in db.
        
        Raises:
            ValidationError: If series already exists in database.
        """
        if field.data:
            series = Series.query.filter_by(name=titlecase(field.data)).first()
            if series is not None:
                raise ValidationError('The series \'{0}\' already exists!'.
                                      format(series.name))


class EditBotanicalNameForm(Form):
    """Form for editing an existing botanical name in the database.

    Attributes:
        common_name (SelectField): Select field for common name this botanical
            name belongs to.
        name (StringField): Field for name of botanical name.
        submit (SubmitField): Submit button.
        synonyms (StringField): Field for synonyms of this botanical name.
    """
    common_name = SelectField('Select Common Name',
                                       coerce=int)
    name = StringField('Botanical Name',
                       validators=[Length(1, 64), NotSpace()])
    submit = SubmitField('Edit Botanical Name')
    synonyms = StringField('Synonyms', validators=[NotSpace()])

    def populate(self, bn):
        """Load a BotanicalName from the db and populate form with it."""
        self.name.data = bn.name
        if bn.common_name:
            self.common_name.data = bn.common_name.id
        if bn.synonyms:
            self.synonyms.data = bn.list_synonyms_as_string()

    def set_common_names(self):
        """Set add/remove_common_names with common names from the database."""
        self.common_name.choices = common_name_select_list()

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

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are invalid.
        
        Raises:
            ValidationError: If a synonym is the same as name.
            ValidationError: If a synonym is too long.
            """
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if synonym == self.name.data:
                    raise ValidationError('\'{0}\' can\'t have itself as a '
                                          'synonym.'.format(self.name.data))
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')
                if not BotanicalName.validate(synonym):
                    raise ValidationError('The synonym \'{0}\' does not '
                                          'appear to be a valid botanical '
                                          'name.'.format(synonym))


class EditCategoryForm(Form):
    """Form for editing an existing category in the database.

    Attributes:
        category (StringField): Field for category name.
        description (TextAreaField): Field for description.
        submit (SubmitField): Submit button.
    """
    category = StringField('Category', validators=[Length(1, 64), NotSpace()])
    description = TextAreaField('Description', validators=[NotSpace()])
    submit = SubmitField('Edit Category')

    def populate(self, category):
        """Load category from database and populate form with it.

        Args:
            category (Category): A category object to populate the form from.
        """
        self.category.data = category.name
        self.description.data = category.description


class EditCommonNameForm(Form):
    """Form for editing an existing common name in the database.

    Attributes:
        categories (SelectMultipleField): Select for categories.
        description (StringField): Field for description of common name.
        name (StringField): CommonName name to edit.
        submit (SubmitField): Submit button.
    """
    categories = SelectMultipleField('Select/Deselect Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
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
            self.synonyms.data = cn.list_synonyms_as_string()
        self.categories.data = [cat.id for cat in cn.categories]
        if cn.gw_common_names:
            self.gw_common_names.data = [gw_cn.id for gw_cn in
                                         cn.gw_common_names]
        if cn.gw_seeds:
            self.gw_seeds.data = [gw_seed.id for gw_seed in cn.gw_seeds]

    def set_selects(self):
        """Populate categories with Categories from the database."""
        self.categories.choices = category_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_common_names.choices.insert(0, (0, 'None'))
        self.gw_seeds.choices = seed_select_list()
        self.gw_seeds.choices.insert(0, (0, 'None'))
        self.parent_cn.choices = common_name_select_list()
        self.parent_cn.choices.insert(0, (0, 'N/A'))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are too long."""
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
    """Form for adding a packet to a seed.

    Attributes:
        price (StringField): Field for price in US Dollars.
        quantity (StringField): Field for amount of seed in a packet.
        units (StringField): Field for unit of measurement.
        sku (StringField): Field for product SKU.
        submit (SubmitField): Submit button.
    """
    price = StringField('Price in US dollars',
                        validators=[DataRequired(), NotSpace(), USDollar()])
    quantity = StringField('Quantity', validators=[DataRequired(), NotSpace()])
    units = StringField('Unit of measurement',
                       validators=[Length(1, 32), NotSpace()])
    sku = StringField('SKU', validators=[Length(1, 32), NotSpace()])
    submit = SubmitField('Edit Packet')

    def populate(self, packet):
        """Populate form elements with data from database."""
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


class EditSeedForm(Form):
    """Form for editing an existing seed in the database.
    """
    botanical_name = SelectField('Botanical Names', coerce=int)
    categories = SelectMultipleField('Select/Deselect Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    common_name = SelectField('Common Name',
                              coerce=int,
                              validators=[DataRequired()])
    description = TextAreaField('Description', validators=[NotSpace()])
    dropped = BooleanField('Dropped/Inactive')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
    in_stock = BooleanField('In Stock')
    name = StringField('Seed Name', validators=[Length(1, 64), NotSpace()])
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Edit Seed')
    synonyms = StringField('Synonyms', validators=[NotSpace()])
    thumbnail = FileField('New Thumbnail',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Set choices for all select fields with values from database."""
        self.botanical_name.choices = botanical_name_select_list()
        self.botanical_name.choices.insert(0, (0, 'None'))
        self.categories.choices = category_select_list()
        self.common_name.choices = common_name_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_common_names.choices.insert(0, (0, 'None'))
        self.gw_seeds.choices = seed_select_list()
        self.gw_seeds.choices.insert(0, (0, 'None'))
        self.series.choices = series_select_list()
        self.series.choices.insert(0, (0, 'N/A'))

    def populate(self, seed):
        """Populate form with data from a Seed object."""
        if seed.botanical_name:
            self.botanical_name.data = seed.botanical_name.id
        self.categories.data = [cat.id for cat in seed.categories]
        if seed.common_name:
            self.common_name.data = seed.common_name.id
        self.description.data = seed.description
        if seed.in_stock:
            self.in_stock.data = True
        if seed.dropped:
            self.dropped.data = True
        if seed.gw_common_names:
            self.gw_common_names.data = [gw_cn.id for gw_cn in
                                         seed.gw_common_names]
        if seed.gw_seeds:
            self.gw_seeds.data = [gw_sd.id for gw_sd in seed.gw_seeds]
        self.name.data = seed.name
        if seed.series:
            self.series.data = seed.series.id
        if seed.synonyms:
            self.synonyms.data = seed.list_synonyms_as_string()

    def validate_categories(self, field):
        """Raise ValidationError if any categories not in selected CommonName.

        Raises:
            ValidationError: If any selected categories are not present within
                the selected CommonName.
        """
        cn = CommonName.query.get(self.common_name.data)
        cat_ids = [cat.id for cat in cn.categories]
        for cat_id in field.data:
            if cat_id not in cat_ids:
                cn_url = url_for('seeds.edit_common_name', cn_id=cn.id)
                raise ValidationError(
                    Markup('One or more of selected categories are not '
                           'associated with selected common name \'{0}\'. <a '
                           'href="{1}">Click here</a> if you would like to '
                           'edit \'{0}\'.'.format(cn.name, cn_url)))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are too long."""
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if synonym == self.name.data:
                    raise ValidationError('\'{0}\' can\'t have itself as a '
                                          'synonym!'.format(self.name.data))
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')


class EditSeriesForm(Form):
    """Form for editing a Series to the database.

    Attributes:
        common_name (SelectField): Field for selecting a common name.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
    """
    common_name = SelectField('Select Common Name', coerce=int)
    description = TextAreaField('Description', validators=[NotSpace()])
    name = StringField('Series Name', validators=[Length(1, 64), NotSpace()])
    submit = SubmitField('Edit Series')

    def set_common_names(self):
        """Set common name choices with common names from db."""
        self.common_name.choices = common_name_select_list()

    def populate(self, series):
        """Populate fields with information from a db entry."""
        self.name.data = series.name
        self.common_name.data = series.common_name.id
        self.description.data = series.description


class RemoveBotanicalNameForm(Form):
    """Form for removing a botanical name."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Botanical Name')


class RemoveCategoryForm(Form):
    """Form for removing a category."""
    move_to = SelectField('Move common names and seeds in this category to', 
                          coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Category')

    def set_move_to(self, cat_id):
        """Set move_to SelectField with other Categories.

        Args:
            cat_id: The id of the Category to be removed.
        """
        cats = Category.query.filter(Category.id != cat_id).all()
        self.move_to.choices = [(cat.id, cat.name) for cat in cats]


class RemoveCommonNameForm(Form):
    """Form for removing a common name."""
    move_to = SelectField('Move botanical names and seeds associated with '
                          'this common name to', coerce=int)
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Common Name')

    def set_move_to(self, cn_id):
        """Set move_to SelectField with other CommonNames.

        Args:
            cn_id: The id of the CommonName to be removed.
        """
        cns = CommonName.query.filter(CommonName.id != cn_id).all()
        self.move_to.choices = [(cn.id, cn.name) for cn in cns]


class RemovePacketForm(Form):
    """Form for removing a packet."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Packet')


class RemoveSeedForm(Form):
    """Form for removing a seed."""
    delete_images = BooleanField('Also delete all images for this seed')
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Seed')


class RemoveSeriesForm(Form):
    """Form for removing a series."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Series')

                
class SelectBotanicalNameForm(Form):
    """Form for selecting a botanical name."""
    names = SelectField('Select Botanical Name', coerce=int)
    submit = SubmitField('Submit')

    def set_names(self):
        """Populate names with BotanicalNames from the database."""
        self.names.choices = botanical_name_select_list()


class SelectCategoryForm(Form):
    """Form for selecting a category."""
    categories = SelectField('Select Category', coerce=int)
    submit = SubmitField('Submit')

    def set_categories(self):
        """Populate categories with Categories from the database."""
        self.categories.choices = category_select_list()


class SelectCommonNameForm(Form):
    """Form for selecting a common name."""
    names = SelectField('Select Common Name', coerce=int)
    submit = SubmitField('Submit')

    def set_names(self):
        """Populate names with CommonNames from the database."""
        self.names.choices = common_name_select_list()


class SelectPacketForm(Form):
    """Form for selecting a packet."""
    packets = SelectField('Select Packet', coerce=int)
    submit = SubmitField('Submit')

    def set_packets(self):
        """Populate packets with Packets from database."""
        self.packets.choices = packet_select_list()


class SelectSeedForm(Form):
    """Form for selecting a seed."""
    seeds = SelectField('Select Seed', coerce=int)
    submit = SubmitField('Submit')

    def set_seeds(self):
        """Populate seeds with Seeds from the database."""
        self.seeds.choices = seed_select_list()

class SelectSeriesForm(Form):
    """Form for selecting a series."""
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Submit')

    def set_series(self):
        """Populate series with Series from the database."""
        self.series.choices = series_select_list()

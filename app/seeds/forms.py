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
from .models import (
    BotanicalName,
    Category,
    CommonName,
    Image,
    Packet,
    Price,
    QtyDecimal,
    QtyFraction,
    QtyInteger,
    Seed,
    Series,
    Unit
)


IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']


def botanical_name_select_list():
    """Generate a list of all BotanicalNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each botanical
            name in the database.
    """
    bn_list = []
    for bn in BotanicalName.query.order_by('_name'):
        if not bn.syn_parents:
            bn_list.append((bn.id, bn.name))
    return bn_list


def category_select_list():
    """Generate a list of all Categories for populating Select fields.

    Returns:
        list: A list of tuples containing the id and category of each category
            in the database.
    """
    return [(category.id, category.category) for category in
            Category.query.order_by('_category')]


def common_name_select_list():
    """Generate a list of all CommonNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each common name
            in the database.
    """
    cn_list = []
    for cn in CommonName.query.order_by('_name'):
        if not cn.syn_parents:
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
    return [(pkt.id, '{0}, {1} - SKU {2}: ${3} for {4} {5}'.
                     format(pkt.seed.common_name.name,
                            pkt.seed.name,
                            pkt.sku,
                            pkt.price,
                            pkt.quantity,
                            pkt.unit)) for pkt in packets]


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
        if not seed.syn_parents:
            seeds.append((seed.id, seed.fullname))
    return seeds


class AddBotanicalNameForm(Form):
    """Form for adding a new botanical name to the database.

    Attributes:
        name (StringField): Field for botanical name.
        common_names (SelectMultipleField): Field for selecting common names
            to associate with a botanical name.
        submit (SubmitField): Submit button.
    """
    name = StringField('Botanical Name', validators=[Length(1, 64)])
    common_names = SelectField('Select Common Name', coerce=int)
    submit = SubmitField('Add Botanical Name')
    synonyms = StringField('Synonyms')

    def set_common_names(self):
        """Set common_names with CommonName objects loaded from db."""
        self.common_names.choices = common_name_select_list()

    def validate_name(self, field):
        """Raise a ValidationError if name exists or is invalid.

        Args:
            field: The field to validate: .name.

        Raises:
            ValidationError: If the name does not appear to be a valid
                botanical name.
            ValidationError: If a botanical name with the same name already
                exists in the database.
        """
        if not BotanicalName.validate(field.data):
            raise ValidationError('\'{0}\' does not appear to be a valid '
                                  'botanical name. The first word should '
                                  'begin with a capital letter, and the '
                                  'second word should be all lowercase.'.
                                  format(field.data))
        bn = BotanicalName.query.filter_by(name=field.data).first()
        if bn is not None:
            raise ValidationError('The botanical name \'{0}\' already exists '
                                  'in the database!'.format(bn.name))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are too long.
        
        Also raise an error if any synonym is not a valid botanical name."""
        if field.data:
            synonyms = field.data.split(', ')
            for synonym in synonyms:
                if len(synonym) > 64:
                    raise ValidationError('Each synonym can only be a maximum '
                                          'of 64 characters long!')
                if not BotanicalName.validate(synonym):
                    raise ValidationError('The synonym \'{0}\' does not '
                                          'appear to be a valid botanical '
                                          'name!')


class AddCategoryForm(Form):
    """Form for adding a new category to the database.

    Attributes:
        category (StringField): Field for the category name.
        description (TextAreaField): Field for the category's description.
        submit (SubmitField): Submit button.
    """
    category = StringField('Category', validators=[Length(1, 64)])
    description = TextAreaField('Description')
    submit = SubmitField('Add Category')

    def validate_category(self, field):
        """Raise a ValidationError if submitted category already exists.

        Raises:
            ValidationError: If submitted category already exists in the
                database.
        """
        if Category.query.filter_by(category=field.data.title()).first() is \
                not None:
            raise ValidationError('\'{0}\' already exists in the database!'.
                                  format(field.data))


class AddCommonNameForm(Form):
    """Form for adding a new common name to the database.

    Attributes:
        categories (SelectMultipleField): Select field with categories from
            the database to associate with this CommonName.
        name (StringField): Field for the common name itself.
        description (TextAreaField): Field for description of common name.
        submit (SubmitField): Submit button.
    """
    categories = SelectMultipleField('Select Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    description = TextAreaField('Description')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
    instructions = TextAreaField('Planting Instructions')
    name = StringField('Common Name', validators=[Length(1, 64)])
    parent_cn = SelectField('Subcategory of', coerce=int)
    submit = SubmitField('Add Common Name')
    synonyms = StringField('Synonyms')

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
            ValidationError: If submitted common name is in the database.
        """
        if CommonName.query.filter_by(name=field.data.title()).first() is \
                not None:
            raise ValidationError('\'{0}\' already exists in the database!'.
                                  format(field.data))

    def validate_synonyms(self, field):
        """Raise a ValidationError if any synonyms are too long."""
        synonyms = field.data.split(', ')
        for synonym in synonyms:
            if len(synonym) > 64:
                raise ValidationError('Each synonym can only be a maximum of '
                                      '64 characters long!')


class AddPacketForm(Form):
    """Form for adding a packet to a seed.

    Attributes:
        again (BooleanField): Checkbox for whether or not to keep adding
            packets on submit.
        price (DecimalField): Field for price in US Dollars.
        quantity (StringField): Field for amount of seed in a packet.
        unit (StringField): Unit
    """
    again = BooleanField('Add another packet after this.', default='checked')
    price = DecimalField('Or enter a price', places=2, validators=[Optional()])
    prices = SelectField('Select a price', coerce=int)
    quantities = SelectField('Select a quantity', coerce=str)
    quantity = StringField('Or enter a quantity')
    unit = StringField('Or enter a unit of measurement',
                       validators=[Length(1, 32), Optional()])
    units = SelectField('Select a unit of measurement', coerce=int)
    sku = StringField('SKU', validators=[Length(1, 32)])
    submit = SubmitField('Add Packet')

    def set_selects(self):
        """Set selects with values loaded from db."""
        prices = [(0, '---')]
        prices += [(p.id, '${0}'.format(p.price)) for p in
                   Price.query.order_by('price')]
        self.prices.choices = prices
        units = [(0, '---')]
        units += [(u.id, u.unit) for u in
                  Unit.query.order_by('unit')]
        self.units.choices = units
        quantities = [('0', '---')]
        quantities += [(str(qd.value), str(qd.value)) for qd in
                       QtyDecimal.query.order_by('value')]
        quantities += [(str(qf.value), str(qf.value)) for qf in
                       QtyFraction.query.order_by('value')]
        quantities += [(str(qi.value), str(qi.value)) for qi in
                       QtyInteger.query.order_by('value')]
        self.quantities.choices = quantities

    def validate_prices(self, field):
        """Raise ValidationError if both or neither prices/price have values.
        """
        if field.data is None or field.data == 0:
            if self.price.data is None or self.price.data == '':
                raise ValidationError('No price selected or entered.')
        else:
            if self.price.data is not None and self.price.data != '':
                price = Price.query.get(field.data)
                if price.price != self.price.data:
                    raise ValidationError('Price entered conflicts with price '
                                          'selected!')

    def validate_quantities(self, field):
        """Raise ValidationError if both/neither quantities/quantity set."""
        if field.data is None or field.data == 'None' or field.data == '0':
            if self.quantity.data is None or self.quantity.data == '':
                raise ValidationError('No quantity selected or entered.')
        else:
            if self.quantity.data is not None and self.quantity.data != '':
                if field.data != self.quantity.data:
                    raise ValidationError('Quantity entered conflicts with '
                                          'quantity selected!')

    def validate_quantity(self, field):
        """Raise ValidationError if quantity cannot be parsed as valid."""
        if field.data:
            packet = Packet()
            try:
                packet.quantity = field.data
            except ValueError as e:
                raise ValidationError(str(e))

    def validate_sku(self, field):
        """Raise ValidationError if sku already exists in database."""
        packet = Packet.query.filter_by(sku=field.data).first()
        if packet is not None:
            raise ValidationError('The SKU \'{0}\' is already in use by: {1}!'.
                                  format(packet.sku, packet.seed.fullname))

    def validate_units(self, field):
        """Raise a ValidationError if both/neither units/unit set."""
        if field.data is None or field.data == 0:
            if self.unit.data is None or self.unit.data == '':
                raise ValidationError('No unit of measure selected or '
                                      'entered.')
        else:
            if self.unit.data is not None and self.unit.data != '':
                unit = Unit.query.get(field.data)
                if self.unit.data != unit.unit:
                    raise ValidationError('Unit of measure entered conflicts '
                                          'with unit selected!')


class AddSeedForm(Form):
    """Form for adding a new seed to the database.

    Attributes:
        botanical_names (SelectMultipleField): Field for selecting botanical
            names associated with seed.
        categories (SelectMultipleField): Field for selecting categories
            associated with seed.
        common_names (SelectMultipleField): Field for selecting common names
            associated with seed.
        description (TextAreaField): Field for seed product description.
        name (StringField): The cultivar name of the seed.
        submit (SubmitField): Submit button.
        thumbnail (FileField): Field for uploading thumbnail image.
    """
    botanical_names = SelectField('Select Botanical Name', coerce=int)
    categories = SelectMultipleField('Select Categories', coerce=int)
    common_names = SelectField('Select Common Name',
                               coerce=int,
                               validators=[DataRequired()])
    description = TextAreaField('Description')
    dropped = BooleanField('Dropped/Inactive')
    gw_common_names = SelectMultipleField('Common Names')
    gw_seeds = SelectMultipleField('Cultivars')
    in_stock = BooleanField('In Stock', default='checked')
    name = StringField('Seed Name (Cultivar)', validators=[Length(1, 64)])
    series = SelectField('Select Series', coerce=int)
    submit = SubmitField('Add Seed')
    synonyms = StringField('Synonyms')
    thumbnail = FileField('Thumbnail Image',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Sets botanical_names, categories, and common_names from db."""
        self.botanical_names.choices = botanical_name_select_list()
        self.categories.choices = category_select_list()
        self.common_names.choices = common_name_select_list()
        self.gw_common_names.choices = common_name_select_list()
        self.gw_seeds.choices = seed_select_list()
        self.series.choices = [(0, 'None')] + series_select_list()

    def validate_name(self, field):
        """Raise ValidationError if seed exists in db with this name."""
        seed = Seed.query.filter_by(_name=field.data.title()).first()
        if seed is not None:
            raise ValidationError('The seed \'{0}\' already exists in the '
                                  'database!'.format(field.data))

    def validate_thumbnail(self, field):
        """Raise a ValidationError if file exists with thumbnail's name."""
        if field.data is not None and field.data != '':
            image = Image.query.\
                filter_by(filename=secure_filename(field.data.filename)).\
                first()
            if image is not None:
                raise ValidationError('An image named \'{0}\' already exists! '
                                      'Please choose a different name.'.
                                      format(image.filename))


class AddSeriesForm(Form):
    """Form for adding a Series to the database.

    Attributes:
        common_names (SelectField): Field for selecting a common name.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
    """
    common_names = SelectField('Select Common Name', coerce=int)
    description = TextAreaField('Description')
    name = StringField('Series Name', validators=[Length(1, 64)])
    submit = SubmitField('Add Series')

    def set_common_names(self):
        """Set common names choices with common names from db."""
        self.common_names.choices = common_name_select_list()

    def validate_name(self, field):
        """Raise ValidationError if name already exists in db."""
        if field.data is not None and field.data != '':
            series = Series.query.filter_by(name=field.data.title()).first()
            if series is not None:
                raise ValidationError('The series \'{0}\' already exists!'.
                                      format(series.name))


class EditBotanicalNameForm(Form):
    """Form for editing an existing botanical name in the database.

    Attributes:
        common_names (SelectMultipleField): Select/deselect common names to
            add/remove.
        name (StringField): Botanical name to edit.
        submit (SubmitField): The submit button.
    """
    common_names = SelectField('Select to add, deselect to remove',
                                       coerce=int)
    name = StringField('Botanical Name', validators=[Length(1, 64)])
    submit = SubmitField('Edit Botanical Name')

    def populate(self, bn):
        """Load a BotanicalName from the db and populate form with it."""
        self.name.data = bn.name
        if bn.common_name:
            self.common_names.data = bn.common_name.id

    def set_common_names(self):
        """Set add/remove_common_names with common names from the database."""
        self.common_names.choices = common_name_select_list()


class EditCategoryForm(Form):
    """Form for editing an existing category in the database.

    Attributes:
        category (StringField): Category name to edit.
        description (TextAreaField): Description to edit.
    """
    category = StringField('Category', validators=[Length(1, 64)])
    description = TextAreaField('Description')
    submit = SubmitField('Edit Category')

    def populate(self, category):
        """Load category from database and populate form with it.

        Args:
            category (Category): A category object to populate the form from.
        """
        self.category.data = category.category
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
    description = TextAreaField('Description')
    gw_common_names = SelectMultipleField('Common Names', coerce=int)
    gw_seeds = SelectMultipleField('Cultivars', coerce=int)
    instructions = TextAreaField('Planting Instructions')
    name = StringField('Common Name', validators=[Length(1, 64)])
    parent_cn = SelectField('Subcategory of', coerce=int)
    submit = SubmitField('Edit Common Name')
    synonyms = StringField('Synonyms')

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


class EditPacketForm(Form):
    """Form for adding a packet to a seed.

    Attributes:
        price (DecimalField): Field for price in US Dollars.
        prices (SelectField): Field for selecting an existing price.
        quantity (StringField): Field for amount of seed in a packet.
        quantities (SelectField): Field for selecting existing quantity.
        unit (StringField): Field for unit of measure.
        units (SelectField): Field for selecting existing unit.
        sku (StringField): Field for product SKU.
        submit (SubmitField: Submit button.
    """
    price = DecimalField('Or enter a price', places=2, validators=[Optional()])
    prices = SelectField('Select Price', coerce=int)
    quantities = SelectField('Select Quantity', coerce=str)
    quantity = StringField('Or enter a quantity')
    unit = StringField('Or enter a unit of measurement',
                       validators=[Length(1, 32), Optional()])
    units = SelectField('Select Unit', coerce=int)
    sku = StringField('SKU', validators=[Length(1, 32)])
    submit = SubmitField('Edit Packet')

    def populate(self, packet):
        """Populate form elements with data from database."""
        self.prices.data = packet._price.id
        self.units.data = packet._unit.id
        self.quantities.data = str(packet.quantity)
        self.sku.data = packet.sku

    def set_selects(self):
        """Set selects with values loaded from db."""
        self.prices.choices = [(p.id, '${0}'.format(p.price)) for p in
                               Price.query.order_by('price')]
        self.units.choices = [(u.id, u.unit) for u in
                              Unit.query.order_by('unit')]
        quantities = []
        quantities += [(str(qd.value), str(qd.value)) for qd in
                       QtyDecimal.query.order_by('value')]
        quantities += [(str(qf.value), str(qf.value)) for qf in
                       QtyFraction.query.order_by('value')]
        quantities += [(str(qi.value), str(qi.value)) for qi in
                       QtyInteger.query.order_by('value')]
        self.quantities.choices = quantities

    def validate_quantity(self, field):
        """Raise ValidationError if quantity cannot be parsed as valid."""
        if field.data:
            packet = Packet()
            try:
                packet.quantity = field.data
            except ValueError as e:
                raise ValidationError(str(e))


class EditSeriesForm(Form):
    """Form for editing a Series to the database.

    Attributes:
        common_names (SelectField): Field for selecting a common name.
        description (TextAreaField): Field for series description.
        name (StringField): Field for series name.
    """
    common_names = SelectField('Select Common Name', coerce=int)
    description = TextAreaField('Description')
    name = StringField('Series Name', validators=[Length(1, 64)])
    submit = SubmitField('Edit Series')

    def set_common_names(self):
        """Set common names choices with common names from db."""
        self.common_names.choices = common_name_select_list()

    def populate(self, series):
        """Populate fields with information from a db entry."""
        self.name.data = series.name
        self.common_names.data = series.common_name.id
        self.description.data = series.description

                
class EditSeedForm(Form):
    """Form for editing an existing seed in the database.
    """
    botanical_names = SelectField('Botanical Names', coerce=int)
    categories = SelectMultipleField('Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    common_name = SelectField('Common Name',
                              coerce=int,
                              validators=[DataRequired()])
    description = TextAreaField('Description')
    dropped = BooleanField('Dropped/Inactive')
    in_stock = BooleanField('In Stock')
    name = StringField('Seed Name', validators=[Length(1, 64)])
    submit = SubmitField('Edit Seed')
    thumbnail = FileField('Upload New Thumbnail',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Set choices for all select fields with values from database."""
        self.botanical_names.choices = botanical_name_select_list()
        self.categories.choices = category_select_list()
        self.common_name.choices = common_name_select_list()

    def populate(self, seed):
        """Populate form with data from a Seed object."""
        if seed.botanical_name:
            self.botanical_names.data = seed.botanical_name.id
        self.categories.data = [cat.id for cat in seed.categories]
        self.common_name.data = seed.common_name.id
        self.description.data = seed.description
        if seed.in_stock:
            self.in_stock.data = True
        if seed.dropped:
            self.dropped.data = True
        self.name.data = seed.name


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


class RemoveBotanicalNameForm(Form):
    """Form for removing a botanical name."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Botanical Name')


class RemoveCategoryForm(Form):
    """Form for removing a category."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Category')


class RemoveCommonNameForm(Form):
    """Form for removing a common name."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Common Name')


class RemovePacketForm(Form):
    """Form for removing a packet."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Packet')


class RemoveSeriesForm(Form):
    """Form for removing a series."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Series')


class RemoveSeedForm(Form):
    """Form for removing a seed."""
    delete_images = BooleanField('Also delete all images for this seed')
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Seed')

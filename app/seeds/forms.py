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
from wtforms import BooleanField, DecimalField, SelectField, \
    SelectMultipleField, StringField, SubmitField, TextAreaField, \
    ValidationError
from wtforms.validators import DataRequired, Length, Optional
from .models import BotanicalName, Category, CommonName, Image, Packet, \
    Price, QtyDecimal, QtyFraction, QtyInteger, Seed, Unit


IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']


def botanical_name_select_list():
    """Generate a list of all BotanicalNames for populating Select fields.

    Returns:
        list: A list of tuples containing the id and name of each botanical
            name in the database.
    """
    return [(bn.id, bn.name) for bn in BotanicalName.query.order_by('_name')]


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
    return [(cn.id, cn.name) for cn in CommonName.query.order_by('_name')]


def seed_select_list():
    """"Generate a list of all Seeds for populating select fields.

    Returns:
        list: A list of tuples containing the ids and strings containing name
            and SKU of each seed in the database.
    """
    return [(seed.id, seed.fullname) for seed in Seed.query.order_by('_name')]


class AddBotanicalNameForm(Form):
    """Form for adding a new botanical name to the database.

    Attributes:
        name (StringField): Field for botanical name.
        common_names (SelectMultipleField): Field for selecting common names
            to associate with a botanical name.
        submit (SubmitField): Submit button.
    """
    name = StringField('Botanical Name', validators=[Length(1, 64)])
    common_names = SelectMultipleField('Common Names', coerce=int)
    submit = SubmitField('Add Botanical Name')

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
        additional_categories (StringField): Field for categories not listed
            in the .categories Select.
        categories (SelectMultipleField): Select field with categories from
            the database to associate with this CommonName.
        name (StringField): Field for the common name itself.
        description (TextAreaField): Field for description of common name.
        submit (SubmitField): Submit button.
    """
    additional_categories = StringField('Additional Categories',
                                        validators=[Optional()])
    categories = SelectMultipleField('Select Categories', coerce=int)
    description = TextAreaField('Description')
    name = StringField('Common Name', validators=[Length(1, 64)])
    submit = SubmitField('Add Common Name')

    def set_categories(self):
        """Populate categories with Categories from the database."""
        self.categories.choices = category_select_list()

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

    def validate_additional_categories(self, field):
        """Raise error if contains any categories that are too long.

        Raises:
            ValidationError: If any category listed is more than 64 characters
                in length.
        """
        for category in field.data.split(','):
            if len(category.strip()) > 64:
                raise ValidationError('Categories can only be up '
                                      'to 64 characters long!')

    def validate_categories(self, field):
        """Raise error if categories and additional_categories are empty.

        Raises:
            ValidationError: If no categories selected and no additional
                categories input.
        """
        if field.data is None or len(field.data) < 1:
            if self.additional_categories.data is None or \
                    len(self.additional_categories.data) < 1:
                raise ValidationError('No categories selected or to be added.'
                                      ' Please select or add at least one '
                                      'category!')


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
    botanical_names = SelectMultipleField('Select Botanical Names', coerce=int)
    categories = SelectMultipleField('Select Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    common_names = SelectField('Select Common Name',
                               coerce=int,
                               validators=[DataRequired()])
    description = TextAreaField('Description')
    name = StringField('Seed Name (Cultivar)', validators=[Length(1, 64)])
    submit = SubmitField('Add Seed')
    thumbnail = FileField('Thumbnail Image',
                          validators=[FileAllowed(IMAGE_EXTENSIONS,
                                                  'Images only!')])

    def set_selects(self):
        """Sets botanical_names, categories, and common_names from db."""
        self.botanical_names.choices = botanical_name_select_list()
        self.categories.choices = category_select_list()
        self.common_names.choices = common_name_select_list()

    def validate_name(self, field):
        """Raise ValidationError if seed exists in db with this name."""
        seed = Seed.query.filter_by(name=field.data.title()).first()
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


class EditBotanicalNameForm(Form):
    """Form for editing an existing botanical name in the database.

    Attributes:
        add_common_names (SelectMultipleField): Select names to add to
            BotanicalName.common_names.
        name (StringField): Botanical name to edit.
        remove_common_names (SelectMultipleField): Select names to remove
            from BotanicalName.common_names.
        submit (SubmitField): The submit button.
    """
    add_common_names = SelectMultipleField('Add Common Names', coerce=int)
    name = StringField('Botanical Name', validators=[Length(1, 64)])
    remove_common_names = SelectMultipleField('Remove Common Names',
                                              coerce=int)
    submit = SubmitField('Edit Botanical Name')

    def populate(self, bn):
        """Load a BotanicalName from the db and populate form with it."""
        self.name.data = bn.name

    def set_common_names(self):
        """Set add/remove_common_names with common names from the database."""
        choices = common_name_select_list()
        self.add_common_names.choices = choices
        self.remove_common_names.choices = choices


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
        name (StringField): CommonName name to edit.
    """
    add_categories = SelectMultipleField('Add Categories', coerce=int)
    description = TextAreaField('Description')
    name = StringField('Common Name', validators=[Length(1, 64)])
    remove_categories = SelectMultipleField('Remove Categories', coerce=int)
    submit = SubmitField('Common Name')

    def populate(self, cn):
        """Load a common name from the database and populate form with it.

        Args:
            cn (CommonName): A CommonName object to populate the form from.
        """
        self.name.data = cn.name
        self.description.data = cn.description

    def set_categories(self):
        """Set add_categories and remove_categories w/ categories from db."""
        choices = category_select_list()
        self.add_categories.choices = choices
        self.remove_categories.choices = choices


class EditSeedForm(Form):
    """Form for editing an existing seed in the database.
    """
    botanical_names = SelectMultipleField('Botanical Names', coerce=int)
    categories = SelectMultipleField('Categories',
                                     coerce=int,
                                     validators=[DataRequired()])
    common_name = SelectField('Common Name',
                              coerce=int,
                              validators=[DataRequired()])
    description = TextAreaField('Description')
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
        if seed.botanical_names:
            self.botanical_names.data = [bn.id for bn in seed.botanical_names]
        self.categories.data = [cat.id for cat in seed.categories]
        self.common_name.data = seed.common_name.id
        self.description.data = seed.description
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


class SelectSeedForm(Form):
    """Form for selecting a seed."""
    seeds = SelectField('Select Seed', coerce=int)
    submit = SubmitField('Submit')

    def set_seeds(self):
        """Populate seeds with Seeds from the database."""
        self.seeds.choices = seed_select_list()


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

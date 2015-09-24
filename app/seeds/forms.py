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


from flask.ext.wtf import Form
from wtforms import BooleanField, SelectField, SelectMultipleField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import Length, Optional
from .models import BotanicalName, Category, CommonName


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

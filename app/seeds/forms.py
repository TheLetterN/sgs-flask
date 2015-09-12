from flask.ext.wtf import Form
from wtforms import BooleanField, SelectField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import Length
from .models import Category


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
            raise ValidationError('{0} already exists!'.
                                  format(field.data))


class EditCategoryForm(Form):
    """Form for editing an existing category in the database.

    Attributes:
        category (StringField): Category name to edit.
        description (TextAreaField): Description to edit.
        id (HiddenField): ID of the Category loaded from the database.
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


class SelectCategoryForm(Form):
    """Form for selecting a category."""
    categories = SelectField('Select Category', coerce=int)
    submit = SubmitField('Submit')

    def load_categories(self):
        """Populate categories with Categories from the database."""
        self.categories.choices = [(category.id, category.category) for
                                   category in
                                   Category.query.order_by('_category')]


class RemoveCategoryForm(Form):
    """Form for removing a category."""
    verify_removal = BooleanField('Yes')
    submit = SubmitField('Remove Category')

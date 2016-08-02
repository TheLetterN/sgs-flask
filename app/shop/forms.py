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


from flask_wtf import Form
from wtforms import (
    FieldList,
    FormField,
    HiddenField,
    SubmitField
)
from wtforms.fields.html5 import IntegerField
from wtforms.validators import NumberRange


class AddProductForm(Form):
    """Form for adding a product to a customer's shopping cart."""
    quantity = IntegerField(
        'Quantity',
        default=1,
        render_kw={'min': '1'},
        validators=[NumberRange(min=1)]
    )
    number = HiddenField()
    submit = SubmitField('Add to Cart')


class ShoppingCartLineForm(Form):
    """Form for a line in the shopping cart."""
    quantity = IntegerField(
        'Quantity',
        render_kw={'min': '1'},
        validators=[NumberRange(min=1)]
    )
    product_number = HiddenField()
    product_label = HiddenField()


class ShoppingCartForm(Form):
    """Form for shopping cart data."""
    lines = FieldList(FormField(ShoppingCartLineForm))
    save = SubmitField('Save Changes')
    checkout = SubmitField('Checkout')

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
    SelectField,
    StringField,
    SubmitField
)
from wtforms.fields.html5 import IntegerField
from wtforms.validators import NumberRange

from app.shop.models import Country


class AddProductForm(Form):
    """Form for adding a product to a customer's shopping cart."""
    quantity = IntegerField(
        'Quantity',
        default=1,
        render_kw={'min': '1'},
        validators=[NumberRange(min=1)]
    )
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


class AddressForm(Form):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    business_name = StringField('Business Name')
    address_line1 = StringField('Address Line 1')
    address_line2 = StringField('Address Line 2')
    city = StringField('City')
    country = SelectField('Country')
    usa_state = SelectField('State')
    can_state = SelectField('Province')
    aus_state = SelectField('State')
    unlisted_state = StringField('Other State/Provice/Region')
    email = StringField('Email Address')
    phone = StringField('Phone Number')
    fax = StringField('Fax Number')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_selects()

    def set_selects(self):
        self.country.choices = (
            (c.alpha3, c.name) for c in Country.query.all()
        )
        usa = Country.get_with_alpha3('USA')
        self.usa_state.choices = (
            (s.abbreviation, s.name) for s in usa.states
        )
        can = Country.get_with_alpha3('CAN')
        self.can_state.choices = (
            (s.abbreviation, s.name) for s in can.states
        )
        aus = Country.get_with_alpha3('AUS')
        self.aus_state.choices = (
            (s.abbreviation, s.name) for s in aus.states
        )


class CheckoutForm(Form):
    billing_address = FormField(AddressForm)
    shipping_address = FormField(AddressForm)
    submit = SubmitField('Review Order')

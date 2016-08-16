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
    SubmitField,
    ValidationError
)
from wtforms.fields.html5 import IntegerField
from wtforms.validators import DataRequired, Length, NumberRange

from app.form_helpers import Email, StrippedStringField
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
    first_name = StrippedStringField(
        'First Name',
        validators=[DataRequired(message='Please enter a first name.'),
                    Length(max=254)]
    )
    last_name = StrippedStringField(
        'Last Name',
        validators=[DataRequired(message='Please enter a last name.'),
                    Length(max=254)]
    )
    business_name = StrippedStringField(
        'Business Name',
        validators=[Length(max=254)]
    )
    address_line1 = StrippedStringField(
        'Address Line 1',
        validators=[DataRequired(message='Please enter an address.'),
                    Length(max=254)]
    )
    address_line2 = StrippedStringField(
        'Address Line 2',
        validators=[Length(max=254)]
    )
    city = StrippedStringField(
        'City',
        validators=[DataRequired(message='Please enter a city.'),
                    Length(max=254)]
    )
    postalcode = StrippedStringField(
        'Zip/Postal Code',
        validators=[Length(max=16)]
    )
    country = SelectField('Country')
    usa_state = SelectField('State')
    can_state = SelectField('Province')
    aus_state = SelectField('State')
    unlisted_state = StrippedStringField(
        'State/Provice/Region',
        validators=[Length(max=254)]
    )
    email = StrippedStringField(
        'Email Address',
        validators=[Email(message='Please enter a valid email address'),
                    Length(max=254)]
    )
    phone = StrippedStringField(
        'Phone Number',
        validators=[DataRequired(message='Please enter a phone number.'),
                    Length(max=32)]
    )
    fax = StrippedStringField('Fax Number', validators=[Length(max=32)])

    def set_selects(self, filter_noship=False):
        countries = Country.query.all()
        if filter_noship:
            self.country.choices = (
                [(c.alpha3, c.name) for c in countries if not c.noship]
            )
        else:
            self.country.choices = (
                [(c.alpha3, c.name) for c in countries]
            )
        usa = Country.get(alpha3='USA')
        self.usa_state.choices = (
            [(s.abbreviation, s.name) for s in usa.states]
        )
        self.usa_state.choices.insert(0, ('0', ''))
        can = Country.get(alpha3='CAN')
        self.can_state.choices = (
            [(s.abbreviation, s.name) for s in can.states]
        )
        self.can_state.choices.insert(0, ('0', ''))
        aus = Country.get(alpha3='AUS')
        self.aus_state.choices = (
            [(s.abbreviation, s.name) for s in aus.states]
        )
        self.aus_state.choices.insert(0, ('0', ''))

    def validate_usa_state(self, field):
        """Raise ValidationError if country is USA and no state selected."""
        if self.country.data == 'USA' and field.data == '0':
            raise ValidationError('Please select a state.')

    def validate_can_state(self, field):
        """Raise ValidationError if country is CAN and no state selected."""
        if self.country.data == 'CAN' and field.data == '0':
            raise ValidationError('Please select a province.')

    def validate_aus_state(self, field):
        """Raise ValidationError if country is AUS and no state selected."""
        if self.country.data == 'AUS' and field.data == '0':
            raise ValidationError('Please select a state.')


class CheckoutForm(Form):
    billing_address = FormField(AddressForm)
    shipping_address = FormField(AddressForm)
    submit = SubmitField('Review Order')

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
    BooleanField,
    FieldList,
    FormField,
    HiddenField,
    SelectField,
    SubmitField,
    ValidationError
)
from wtforms.fields.html5 import IntegerField
from wtforms.validators import InputRequired, Length, NumberRange

from app.form_helpers import Email, StrippedStringField, StrippedTextAreaField
from app.shop.models import Address, Country


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
        validators=[InputRequired(message='Please enter a first name.'),
                    Length(max=254)]
    )
    last_name = StrippedStringField(
        'Last Name',
        validators=[InputRequired(message='Please enter a last name.'),
                    Length(max=254)]
    )
    business_name = StrippedStringField(
        'Business Name',
        validators=[Length(max=254)]
    )
    address_line1 = StrippedStringField(
        'Address Line 1',
        validators=[InputRequired(message='Please enter an address.'),
                    Length(max=254)]
    )
    address_line2 = StrippedStringField(
        'Address Line 2',
        validators=[Length(max=254)]
    )
    city = StrippedStringField(
        'City',
        validators=[InputRequired(message='Please enter a city.'),
                    Length(max=254)]
    )
    postalcode = StrippedStringField(
        'ZIP/Postal Code',
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
        validators=[InputRequired(message='Please enter a phone number.'),
                    Length(max=32)]
    )
    fax = StrippedStringField('Fax Number', validators=[Length(max=32)])

    def __eq__(self, other):
        ret = (
            self.first_name.data == other.first_name.data and
            self.last_name.data == other.last_name.data and
            self.business_name.data == other.business_name.data and
            self.address_line1.data == other.address_line1.data and
            self.address_line2.data == other.address_line2.data and
            self.city.data == other.city.data and
            self.postalcode.data == other.postalcode.data and
            self.country.data == other.country.data and
            self.email.data == other.email.data and
            self.phone.data == other.phone.data and
            self.fax.data == other.fax.data
        )
        if ret:  # We know self.country.data == other.country.data
            if self.country.data == 'USA':
                ret &= self.usa_state.data == other.usa_state.data
            elif self.country.data == 'CAN':
                ret &= self.can_state.data == other.can_state.data
            elif self.country.data == 'AUS':
                ret &= self.aus_state.data == other.aus_state.data
            else:
                ret &= self.unlisted_state.data == other.unlisted_state.data
        return ret

    def equals_address(self, address):
        """Check if the data in form is equal to given address."""
        if not address:
            return False
        ret = (
            self.first_name.data == address.first_name and
            self.last_name.data == address.last_name and
            self.business_name.data == address.business_name and
            self.address_line1.data == address.address_line1 and
            self.address_line2.data == address.address_line2 and
            self.city.data == address.city and
            self.postalcode.data == address.postalcode and
            self.country.data == address.country.alpha3 and
            self.email.data == address.email and
            self.phone.data == address.phone and
            self.fax.data == address.fax
        )
        if ret:
            if self.country.data == 'USA':
                ret &= self.usa_state.data == address.state.abbreviation
            elif self.country.data == 'CAN':
                ret &= self.can_state.data == address.state.abbreviation
            elif self.country.data == 'AUS':
                ret &= self.aus_state.data == address.state.abbreviation
            else:
                ret &= self.unlisted_state.data == address.unlisted_state
        return ret

    def populate_address(self, address):
        """Populate an `Address` with data from `AddressForm`.

        Args:
            address: the `Address` instance to populate.
        """
        address.first_name = self.first_name.data
        address.last_name = self.last_name.data
        address.business_name = self.business_name.data
        address.address_line1 = self.address_line1.data
        address.address_line2 = self.address_line2.data
        address.city = self.city.data
        address.postalcode = self.postalcode.data
        address.country = Country.get(alpha3=self.country.data)
        address.email = self.email.data
        address.phone = self.phone.data
        address.fax = self.fax.data
        if self.country.data == 'USA':
            address.state = address.country.get_state(
                abbreviation=self.usa_state.data
            )
        elif self.country.data == 'CAN':
            address.state = address.country.get_state(
                abbreviation=self.can_state.data
            )
        elif self.country.data == 'AUS':
            address.state = address.country.get_state(
                abbreviation=self.aus_state.data
            )
        else:
            address.unlisted_state = self.unlisted_state.data

    def get_or_create_address(self):
        """Get an `Address` with corresponding data or create it."""
        addresses = Address.query.filter(
            Address.address_line1 == self.address_line1.data
        ).filter(
            Address.city == self.city.data
        ).all()
        for address in addresses:
            if self.equals_address(address):
                return address
        else:
            address = Address()
            self.populate_address(address)
            return address

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
        self.usa_state.choices.insert(0, ('0', 'Select a state:'))
        can = Country.get(alpha3='CAN')
        self.can_state.choices = (
            [(s.abbreviation, s.name) for s in can.states]
        )
        self.can_state.choices.insert(0, ('0', 'Select a province:'))
        aus = Country.get(alpha3='AUS')
        self.aus_state.choices = (
            [(s.abbreviation, s.name) for s in aus.states]
        )
        self.aus_state.choices.insert(0, ('0', 'Select a state:'))

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

    def populate_from_address(self, addr):
        """Populate an `AddressForm` with data from an`Address` instance.

        Args:
            addr: The `Address` instance to populate form with.
        """
        self.first_name.data = addr.first_name
        self.last_name.data = addr.last_name
        self.business_name.data = addr.business_name
        self.address_line1.data = addr.address_line1
        self.address_line2.data = addr.address_line2
        self.city.data = addr.city
        self.postalcode.data = addr.postalcode
        self.country.data = addr.country.alpha3
        if addr.country.alpha3 == 'USA':
            self.usa_state.data = addr.state.abbreviation
        elif addr.country.alpha3 == 'CAN':
            self.can_state.data = addr.state.abbreviation
        elif addr.country.alpha3 == 'AUS':
            self.aus_state.data = addr.state.abbreviation
        else:
            self.unlisted_state.data = addr.unlisted_state
        self.email.data = addr.email
        self.phone.data = addr.phone
        self.fax.data = addr.fax


class CheckoutForm(Form):
    billing_address = FormField(AddressForm)
    shipping_address = FormField(AddressForm)
    shipping_comments = StrippedTextAreaField(
        'Shipping Comments',
        validators=[Length(max=5120)]
    )
    nonce = HiddenField(id='card-nonce')
    review_order = SubmitField('Review Order')


class ShippingForm(Form):
    address = FormField(AddressForm)
    comments = StrippedTextAreaField(
        'Shipping Comments',
        validators=[Length(max=5120)]
    )
    # TODO: shipping method
    proceed = SubmitField('Proceed to Billing')


class BillingForm(Form):
    same_as_shipping = BooleanField('Same as shipping address')
    address = FormField(AddressForm)
    stripeToken = HiddenField('stripeToken')  # Stripe needs this camelcase.
    proceed = SubmitField('Review Order')


class ConfirmOrderForm(Form):
    proceed = SubmitField('Place Order')

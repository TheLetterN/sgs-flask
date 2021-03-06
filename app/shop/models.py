# -*- coding: utf-8 -*-
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

import json
from decimal import Decimal
from pathlib import Path


from flask import current_app, session
from flask_login import current_user
from pycountry import countries
from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError

from app import db
from app.db_helpers import FourPlaceDecimal, TimestampMixin, USDollar


class OrderExistsError(Exception):
    """Error for attempting to replace an existing `Order`."""
    def __init__(self, message):
        self.message = message


class State(db.Model):
    """Table for first-level administration divisions of countries.

    Even though this table is for all forms of first-level administration
    division (State, Province, Region, Canton, etc.) it is called 'State'
    for the sake of simplicity, and since this is meant for a company in the
    United States that primarly ships to the United States, 'State' is the
    most straightforward term to use.

    Attributes:
        name - The full name of the administrative division, e.g. "California"
            or "British Columbia".
        abbreviation - The abbreviation of the admin division, e.g. "CA" or
            "BC".
        country - The `Country` the admin division belongs to.
        noship_cultivars - A list of `Cultivars` that can't be shipped to the
            given admin division. For example, Baby's Breath can't be shipped
            to California.
    """
    __tablename__ = 'states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.UnicodeText)
    abbreviation = db.Column(db.UnicodeText)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id'))
    country = db.relationship('Country', back_populates='states')
    tax = db.Column(FourPlaceDecimal())
    # noship_cultivars - backref from seeds.models.Cultivar

    def __repr__(self):
        return '<State/Provice/Region/etc: "{}">'.format(self.name)

    @classmethod
    def generate_from_dict(cls, d):
        """Generate `State` instances from a dict.

        The dict should contain alpha3 country codes as keys with dicts
        containing admin districts. Example:

        { 'USA': {'AL': 'Alabama', 'AK': 'Alaska', ... } ... }

        Args:
            d - the `dict` to get state data from.
        """
        for alpha3 in d:
            country = Country.get(alpha3=alpha3)
            if not country:
                raise RuntimeError(
                    'Could not generate first level administration districts '
                    'because no country with the alpha3 code "{}" was found '
                    'in the database!'.format(alpha3)
                )
            divs = d[alpha3]
            for abbr in sorted(divs, key=lambda x: divs[x]):
                yield cls(
                    abbreviation=abbr,
                    name=divs[abbr],
                    country=country
                )

    @classmethod
    def get(cls, country, abbreviation=None, name=None):
        return country.get_state(abbreviation=abbreviation, name=name)

    @property
    def html(self):
        """str: HTML5 abbreviation tag for a state."""
        return '<abbr title="{}">{}</abbr>'.format(self.name,
                                                   self.abbreviation)


class Country(db.Model):
    """Table for countries.

    Attributes:
        alpha3 - The alpha3 code for a country, e.g. "USA", "CAN", or "AUS".
        noship - Whether or not the `Country` can be shipped to.
        safe_to_ship - A boolean for whether or not a country has been
            confirmed safe to ship to. (In other words, not at own risk or
            unable to ship to.) Defaults to False so that if we don't know
            whether or not we can ship to a country, it defaults to `False`,
            which means at own risk.
        at_own_risk_threshold - A price in US dollars above which shipping to
            a given `Country` becomes unsafe/at own risk. For example, it is
            safe to ship orders under $50 to Norway, but over that it becomes
            at own risk.
        states - First-level administrative divisions belonging
            to `Country`; For example, US states or Canadian provinces.
        noship_cultivars - A list of `Cultivars` that can't be shipped to the
            given `Country`. Defaults to `False`.
    """
    __tablename__ = 'countries'
    id = db.Column(db.Integer, primary_key=True)
    _cached = None
    alpha3 = db.Column(db.UnicodeText)
    noship = db.Column(db.Boolean, default=False)
    safe_to_ship = db.Column(db.Boolean, default=False)
    at_own_risk_threshold = db.Column(USDollar)
    states = db.relationship('State', back_populates='country')
    # noship_cultivars - backref from seeds.models.Cultivar

    def __init__(self, alpha3=None):
        self.alpha3 = alpha3

    def __repr__(self):
        return '<Country: "{}">'.format(self.name)

    @classmethod
    def get(cls,
            alpha3=None,
            alpha2=None,
            name=None,
            numeric=None,
            official_name=None):
        """Load a `Country` with the given parameter.

        Passed values will take precedence in this order: alpha3, alpha2,
        name, official_name, numeric. The first argument in that order to
        contain data will be used, and all others will not be used.

        Args:
            alpha3: The alpha3 code of the `Country` to load.
            alpha2: The alpha2 code of the `Country` to load.
            name: The name of the `Country` to load. Note: This needs to be
                as it is in the ISO 3166-1 standard, so "Taiwan" needs to be
                "Taiwan, Province of China" and "Palestine" needs to be
                "Palestine, State of", even though we alter them in the
                property `Country.name`.
            official_name: The official name of the `Country` to load.
            numeric: The numeric of the `Country` to load.

        Returns:
            The `Country` from the database with the given data.
        """
        if alpha3:
            pass
        elif alpha2:
            try:
                alpha3 = countries.get(alpha2=alpha2).alpha3
            except KeyError:
                return None
        elif name:
            try:
                alpha3 = countries.get(name=name).alpha3
            except KeyError:
                return None
        elif numeric:
            try:
                alpha3 = countries.get(numeric=numeric).alpha3
            except KeyError:
                return None
        elif official_name:
            try:
                alpha3 = countries.get(official_name=official_name).alpha3
            except KeyError:
                return None
        return cls.query.filter(cls.alpha3 == alpha3.upper()).one_or_none()

    @classmethod
    def generate_from_alpha3s(cls, alpha3s):
        """Generate a list of `Country` instances from list of alpha3 codes.

        Args:
            alpha3s - a list of alpha3 country codes.
        """
        for alpha3 in alpha3s:
            yield(cls(alpha3=alpha3))

    @property
    def _country(self):
        """pycountry.db.Country: A cached object with country data."""
        if not self._cached:
            self._cached = countries.get(alpha3=self.alpha3)
        return self._cached

    @property
    def alpha2(self):
        """str: The alpha2 code of `Country`."""
        return self._country.alpha2

    @property
    def name(self):
        """str: The common name of `Country`."""
        # The ISO standard for some country names is debatable, and may be
        # offensive to some. As such, we change them to a less potentially
        # offensive version here to avoid ruffling too many feathers.
        if 'Taiwan' in self._country.name:
            return 'Taiwan'
        elif 'Palestine' in self._country.name:
            return 'Palestine'
        else:
            return self._country.name

    @property
    def numeric(self):
        """str: The numeric code of `Country`."""
        return self._country.numeric

    @property
    def official_name(self):
        """str: The official (long form) name of `Country`."""
        return self._country.official_name

    def get_state(self, abbreviation=None, name=None):
        """Get a `State` belonging to `Country`.

        Args:
            abbreviation: The abbreviation for the `State`.
            name: The full name of the `State`.
        """
        if abbreviation:
            return next(
                (d for d in self.states if d.abbreviation == abbreviation),
                None
            )
        elif name:
            return next(
                (d for d in self.states if d.name == name),
                None
            )
        else:
            raise ValueError('Need an abbreviation or name to get a state!')

    def get_state_by_abbr(self, abbr):
        """Return l1 admin division with given abbr, or `None`."""
        abbr = abbr.upper()
        return next(
            (d for d in self.states if d.abbreviation == abbr),
            None
        )

    def at_own_risk(self, usd=None):
        """Whether or not shipping to a `Country` is at own risk.

        Args:
            usd: Optional USD value above which an order becomes at own risk.

        Returns:
            bool: Whether or not shipping is at own risk for `Country`.
        """
        if usd and self.at_own_risk_threshold:
            return usd > self.at_own_risk_threshold
        elif self.safe_to_ship:
            return False
        else:
            return True


class Address(db.Model, TimestampMixin):
    """Table for addresses.

    Attributes:

        customer - The `Customer` an `Address` belongs to.
        first_name - The first name of the person the address belongs to.
        last_name - The last name of the person the address belongs to.
        business name - Optional business the address belongs to.
        city - The city portion of the address.
        postalcode - The zip/postal code of the address.
        country - The country the address is in.
        state - The first-level administrative division the address is in.
        unlisted_state - A first-level admin division that doesn't have a
            `State` instance in the database.
        email - The email address of the person the address belongs to.
        phone - Phone number of person address belongs to.
        fax - Optional fax number of person address belongs to.
    """
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        back_populates='addresses'
    )
    first_name = db.Column(db.UnicodeText)
    last_name = db.Column(db.UnicodeText)
    business_name = db.Column(db.UnicodeText)
    address_line1 = db.Column(db.UnicodeText)
    address_line2 = db.Column(db.UnicodeText)
    city = db.Column(db.UnicodeText)
    postalcode = db.Column(db.UnicodeText)
    country_id = db.Column(db.ForeignKey('countries.id'))
    country = db.relationship('Country')
    state_id = db.Column(db.ForeignKey('states.id'))
    state = db.relationship('State')
    unlisted_state = db.Column(db.UnicodeText)
    email = db.Column(db.UnicodeText)
    phone = db.Column(db.UnicodeText)
    fax = db.Column(db.UnicodeText)

    def __repr__(self):
        return '<{0} for: "{1}">'.format(self.__class__.__name__,
                                         self.fullname)

    @property
    def fullname(self):
        """str: The full name of the person the address belongs to."""
        parts = (self.first_name, self.last_name)
        return ' '.join(n for n in parts if n)

    @property
    def page_json(self):
        """Return a JSON object suitable for embedding on a page."""
        data = dict(
            first_name=self.first_name,
            last_name=self.last_name,
            business_name=self.business_name,
            address_line1=self.address_line1,
            address_line2=self.address_line2,
            city=self.city,
            postalcode=self.postalcode,
            country=self.country.alpha3,
            state=self.state.abbreviation,
            unlisted_state=self.unlisted_state,
            email=self.email,
            phone=self.phone,
            fax=self.fax
        )
        return json.dumps(data)



class Customer(db.Model, TimestampMixin):
    """Table for customer data.

    Attributes:

    billing_address - The billing address of the customer.
    shipping_address - The last-used shipping address of the customer.
    addresses - All addresses belonging to the customer.
    orders - `Order` instances belonging to customer.
    current_order - `Order` in progress.
    """
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    billing_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    billing_address = db.relationship(
        'Address',
        foreign_keys=billing_address_id,
        post_update=True
    )
    shipping_address_id = db.Column(
        db.Integer,
        db.ForeignKey('addresses.id')
    )
    shipping_address = db.relationship(
        'Address',
        foreign_keys=shipping_address_id,
        post_update=True
    )
    addresses = db.relationship(
        'Address',
        foreign_keys='Address.customer_id',
        back_populates='customer'
    )
    orders = db.relationship(
        'Order',
        foreign_keys='Order.customer_id',
        back_populates='customer'
    )
    current_order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id')
    )
    current_order = db.relationship(
        'Order',
        foreign_keys=current_order_id,
        post_update=True
    )
    stripe_id = db.Column(db.UnicodeText)

    def __repr__(self):
        return '<{0} #{1}: "{2}">'.format(
            self.__class__.__name__,
            self.id,
            self.billing_address.fullname if self.billing_address else ''
        )

    @property
    def first_name(self):
        """str: First name of customer from billing address.

        Setter sets name in `billing_address`, creating `billing_address` if
        it doesn't exist.
        """
        try:
            return self.billing_address.first_name
        except AttributeError:
            return None

    @first_name.setter
    def first_name(self, value):
        if not self.billing_address:
            self.billing_address = Address()
        self.billing_address.first_name = value

    @property
    def last_name(self):
        """str: Last name of customer from billing address."""
        try:
            return self.billing_address.last_name
        except AttributeError:
            return None

    @last_name.setter
    def last_name(self, value):
        if not self.billing_address:
            self.billing_address = Address()
        self.billing_address.last_name = value

    @property
    def fullname(self):
        """str: The full name of the customer taken from billing address."""
        try:
            return self.billing_address.fullname
        except AttributeError:
            return None

    def save_id_to_session(self):
        if self.id:
            session['customer id'] = self.id
        else:
            raise RuntimeError(
                'Attempted to save nonexistent customer id to session!'
            )

    @classmethod
    def get_from_session(cls):
        try:
            return cls.query.get(session['customer id'])
        except KeyError:
            return None


@event.listens_for(Customer.billing_address, 'set')
def add_billing_address_event(target, value, oldvalue, initiator):
    """If a billing address is added to a `Customer`, add it to addresses."""
    if value is not None and value not in target.addresses:
        target.addresses.append(value)


@event.listens_for(Customer.shipping_address, 'set')
def add_shipping_address_event(target, value, oldvalue, initiator):
    """If a shipping address is added to `Customer`, add to addresses."""
    if value is not None and value not in target.addresses:
        target.addresses.append(value)


@event.listens_for(Customer.current_order, 'set')
def add_current_order_event(target, value, oldvalue, initiator):
    """Don't allow replacing `Customer.current_order` with another.

    Raises:
        OrderExistsError - If a current order already exists.
    """
    if value is not None:
        if target.current_order is not None:
            raise OrderExistsError(
                '{0} already has an order in progress!'
                .format(target)
            )
        else:
            if value not in target.orders:
                target.orders.append(value)


class Product(db.Model, TimestampMixin):
    """Table for products.

    Attributes:

    number - The ID number (usually a SKU) of the `Product`.
    label - The string used to label the `Product`.
    price - The price for one unit of the `Product`.
    order_lines - `LineItem` instances with a given `Product`.
    packet - A `Packet` corresponding to a `Product`.
    """
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    type_ = db.Column(db.Enum('packet', 'bulk', name='type_'))
    number = db.Column(db.UnicodeText, unique=True)
    label = db.Column(db.UnicodeText)
    price = db.Column(USDollar)
    order_lines = db.relationship(
        'LineItem',
        back_populates='product'
    )
    # packet: backref from app.seeds.models.Packet

    def __init__(self, number=None):
        self.number = number

    def __repr__(self):
        return '<{0} {1}: ${2} for "{3}">'.format(self.__class__.__name__,
                                                  self.number,
                                                  self.price,
                                                  self.label)

    @classmethod
    def get_or_create(cls, number=None):
        """Load a product from db if it exists, otherwise create it.

        Args:
            number - The ID number of the `Product` to load or create.

        Returns:
            Product - The loaded or created `Product`.
        """
        if number:
            obj = cls.query.filter(cls.number == number).one_or_none()
            if not obj:
                obj = cls(number=number)
        else:
            obj = cls()
        return obj

    @property
    def cultivar(self):
        """Cultivar: The `Cultivar` assiociated with `Product` if it exists."""
        try:
            return self.packet.cultivar
        except AttributeError:
            return None

    @property
    def in_stock(self):
        """bool: Whether or not the `Product` is in stock."""
        try:
            return self.cultivar.in_stock
        except AttributeError:
            return False


class LineItem(db.Model, TimestampMixin):
    """Table for lines in an order.

    Note:
        The columns of `Product` are reproduced here because we want to keep
        the `Product` data as it was when the `LineItem` was last
        modified, regardless of changes to the `Product`.

    Attributes:
        order - The `Order` a `LineItem` belongs to.
        product - The `Product` the `LineItem` is for.
        quantity - The number of units of `Product`.
        product_number - The ID number of `Product`.
        label - The label of `Product`.
        price - The price of `Product`.
    """
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    order = db.relationship('Order', back_populates='lines')
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product = db.relationship('Product', back_populates='order_lines')
    quantity = db.Column(db.Integer)
    # Copied Product columns.
    product_number = db.Column(db.UnicodeText)
    label = db.Column(db.UnicodeText)
    price = db.Column(USDollar)

    def __init__(self, product=None, product_number=None, quantity=None):
        if product and product_number and product.number != product_number:
            raise ValueError(
                'Attempted to initialize a Order with a product and a '
                'product_number that corresponds to a different product!'
            )
        if not product and product_number is not None:
            product = Product.query.filter(
                Product.number == product_number
            ).one_or_none()
            if not product:
                raise ValueError(
                    'No product exists with number: {}'.format(product_number)
                )
        self.product = product
        self.quantity = quantity
        if self.product:
            self.product_number = self.product.number
            self.label = self.product.label
            self.price = self.product.price

    def __repr__(self):
        return '<{0}: {1} of "{2}" at ${3} each>'.format(
            self.__class__.__name__,
            self.quantity,
            self.label,
            self.price
        )

    @classmethod
    def from_session_data(cls, data):
        """Create a `LineItem` from `session_data`.

        Args:
            data: A `dict` as generated by `session_data`.
        """
        return cls(
            product_number=data['product number'],
            quantity=data['quantity']
        )

    @property
    def session_data(self):
        """dict: `LineItem` data to store in the user session.

        This is just the product number and quantity, as that's the only
        information that is necessary to create a `LineItem`.
        """
        return {
            'product number': self.product_number,
            'quantity': self.quantity
        }

    @property
    def text(self):
        """str: A string representing a `LineItem`'s data."""
        return '{0} of product #{1}: "{2}"'.format(self.quantity,
                                                   self.product_number,
                                                   self.label)

    @property
    def customer(self):
        """Customer: The `Customer` ordering the `LineItem`."""
        return self.order.customer

    @property
    def shipping_address(self):
        """Address: The shipping address of `Customer` if present."""
        return self.customer.shipping_address

    @property
    def cultivar(self):
        """Cultivar: The `Cultivar` this `LineItem` is for."""
        return self.product.cultivar

    @property
    def in_stock(self):
        """bool: Whether or not the product on the line is in stock."""
        try:
            return self.cultivar.in_stock
        except AttributeError:
            return False

    @property
    def noship_country(self):
        """bool: Whether product can be shipped to country in shipping addr."""
        try:
            if self.shipping_address.country in self.cultivar.noship_countries:
                return True
        except AttributeError:
            pass
        return False

    @property
    def noship_state(self):
        """bool: Whether product can be shipped to state in shipping addr."""
        try:
            if self.shipping_address.state in self.cultivar.noship_states:
                return True
        except AttributeError:
            pass
        return False

    @property
    def noship(self):
        """bool: Whether or not product can be shipped to customer."""
        return self.noship_state or self.noship_country

    @property
    def total(self):
        """Decimal: The total cost of products in a `LineItem`."""
        try:
            if not self.noship and self.in_stock:
                return self.quantity * self.price
            else:
                return Decimal(0)
        except TypeError:
            return None

    @property
    def taxable(self):
        """bool: Whether or not `LineItem` is taxable."""
        return self.cultivar.taxable



@event.listens_for(LineItem.product, 'set')
def order_line_set_product_event(target, value, oldvalue, initiator):
    """Copy relevant values when setting `LineItem.product`."""
    if value is not None:
        target.product_number = value.number
        target.label = value.label
        target.price = value.price


class Order(db.Model, TimestampMixin):
    """Table for orders.
    
    Capitalized attributes are integers representing `Order.status`.

    Attributes:

    INCOMPLETE - An order is considered incomplete until the customer has
        entered all shipping and billing information.
    PENDING - All information has been entered by the customer, but they
        have not reviewed their order and submitted

    lines - `LineItem` instances belonging to this `Order`.
    status - The state the `Order` is in.
    customer - The `Customer` the `Order` belongs to.
    billed_to - The `Address` the `Order` was billed to.
    shipped_to - The `Address` the `Order` was shipped to.
    shipping_comments - Any notes on shipping left by customer.
    """
    __tablename__ = 'orders'

    INCOMPLETE = 1
    PENDING = 2
    PROCESSED = 3
    PAID = 4


    id = db.Column(db.Integer, primary_key=True)
    lines = db.relationship(
        'LineItem',
        back_populates='order',
        cascade='all, delete-orphan'
    )
    status = db.Column(db.Integer, default=INCOMPLETE)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        back_populates='orders'
    )
    billed_to_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    billed_to = db.relationship('Address', foreign_keys=billed_to_id)
    shipped_to_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    shipped_to = db.relationship('Address', foreign_keys=shipped_to_id)
    shipping_comments = db.Column(db.UnicodeText)

    def __init__(self, lines=None, status=None, customer=None):
        self.lines = lines if lines else []
        self.status = status
        self.customer = customer

    def __repr__(self):
        return '<{0} #{1}: {2} lines>'.format(self.__class__.__name__,
                                              self.id,
                                              len(self.lines))

    @classmethod
    def from_session_data(cls, data):
        """Create an order from session_data.

        Args:
            data: A `dict` containing the data needed to create a new
            `Order`.

        Returns:
            Order - The created `Order`.
        """
        lines = []
        for d in data:
            product = Product.query.filter(
                Product.number == d['product number']
            ).one_or_none()
            if product:
                lines.append(LineItem(
                    product=product,
                    quantity=d['quantity']
                ))
        return cls(lines=lines)

    @classmethod
    def from_session(cls, session_key='cart'):
        """Create an order from session data.

        Args:
            session_key: A string to use as key in session to load session
                data from. Defaults to 'cart'.

        Returns:
            Order - The `Order` created from data in the session.
        """
        try:
            order = cls.from_session_data(session[session_key])
            if len(order.lines) != len(session[session_key]):
                # TODO: Inform customer that items in their cart are gone.
                pnos = [l.product_number for l in order.lines]
                for sline in list(session[session_key]):
                    if sline['product number'] not in pnos:
                        session[session_key].remove(sline)
            if order.lines:
                return order
            else:
                return None
        except KeyError:
            return None

    @property
    def number(self):
        return self.id

    @property
    def number_of_items(self):
        return sum(l.quantity for l in self.lines)

    @property
    def session_data(self):
        return [l.session_data for l in self.lines]

    @property
    def text(self):
        lines_text = '\n'.join(l.text for l in self.lines)
        return 'Order #{0} with lines:\n{1}'.format(self.id, lines_text)

    @property
    def shipping_address(self):
        try:
            return self.customer.shipping_address
        except AttributeError:
            return None

    @property
    def before_tax_total(self):
        return sum(l.total for l in self.lines)

    @property
    def tax(self):
        """Decimal: The total sales tax to add."""
        try:
            tax_rate = self.customer.shipping_address.state.tax
            if tax_rate:
                taxable_total = sum(l.total for l in self.lines if l.taxable)
                return (
                    taxable_total * (tax_rate / 100)
                ).quantize(Decimal('.00'))
        except:
            pass
        return Decimal(0)

    @property
    def after_tax_total(self):
        return self.before_tax_total + self.tax

    @property
    def shipping_cost(self):
        rfile = Path(current_app.config.get('JSON_FOLDER'), 'rates.json')
        with rfile.open('r', encoding='utf-8') as ifile:
            rates = json.loads(ifile.read())
        try:
            if self.shipping_address.country.alpha3 == 'USA':
                if self.before_tax_total < rates['free US shipping threshold']:
                    return Decimal(str(rates['US shipping']))
            else:
                # TODO: Handle additional itl shipping charges.
                return Decimal(str(rates['international shipping']))
        except AttributeError:
            pass
        return Decimal(0)

    @property
    def total(self):
        return self.after_tax_total + self.shipping_cost

    @property
    def total_cents(self):
        # TODO: Check if this needs to be quantized before converting to int.
        return int(self.total * 100)

    def add_line(self, product_number, quantity):
        """Add a `LineItem`.

        Note:
            This creates a new `LineItem` instance regardless of whether
            or not the product is already in the `Order` so that the
            returned line reflects the quantity of product added rather than
            the total. If the product already exists in the `Order`, the
            created line will not be added to it, instead `quantity` will be
            added to the existing line.

        Args:
            product_number: The identifier of the product to add.
            quantity: The quantity of product to add.

        Returns:
            The created `LineItem` instance so its data can be used
            by the caller of `add_line`.
        """
        line = LineItem(
            product_number=product_number,
            quantity=quantity
        )
        existing = self.get_line(product_number)
        if existing:
            existing.quantity += quantity
        else:
            self.lines.append(line)
        return line

    def get_line(self, product_number):
        """Get `LineItem` with given `product_number`.

        Args:
            product_number: The product number of the line to return.

        Returns:
            A `LineItem` with given `product_number`, or None if not
            present in `lines`.
        """
        return next(
            (l for l in self.lines if l.product_number == product_number),
            None
        )

    def change_line_quantity(self, product_number, quantity):
        """Set quantity of a given `LineItem`.

        Args:
            product_number: The number of the `Product` on the line.
            quantity: The new quantity of `Product` on the line.
        """
        self.get_line(product_number).quantity = quantity

    def delete_line(self, line):
        """Remove a `LineItem` and ensure it's deleted.

        Args:
            line: The `LineItem` to delete.
        """
        self.lines.remove(line)
        try:
            db.session.delete(line)
            db.session.flush()
        except InvalidRequestError:
            pass  # line was not persisted to the database.
        if self.lines:
            self.save()
        else:
            self.save_to_session()
            # There is no reason to keep the order around if it's empty.
            try:
                db.session.delete(self)
                db.session.commit()
            except InvalidRequestError:
                pass

    def save_to_session(self, session_key='cart'):
        """Save a `Order` to the session.

        Args:
            session_key: A string to use as key in session under which to
                store order data.
        """
        session[session_key] = self.session_data

    def save(self, session_key='cart'):
        """Save a `Order` to the session and (if applicable) database.

        The `Order` will be saved to the database if it belongs to a
        logged in user, otherwise it will only be saved to the session.

        Args:
            session_key: A string to use as a key in session to save session
                data to. Defaults to 'cart'.
        """
        if not current_user.is_anonymous:
            if not current_user.customer_data:
                current_user.customer_data = Customer()
            if (self.customer and
                    self.customer is not current_user.customer_data):
                raise RuntimeError(
                    'Cannot attach a new customer to an order that '
                    'already has a customer associated with it!'
                )
            self.customer = current_user.customer_data
            db.session.commit()

        self.save_to_session(session_key)

    @classmethod
    def load(cls, user=None):
        """Load an order.

        Args:
            user: An optional `User` whom the order belongs to.

        Returns:
            The `User`'s current_order if present, otherwise the
            order from the session if present, otherwise `None`.
        """
        if not user.is_anonymous:
            if not user.current_order:
                user.current_order = cls.from_session()
                db.session.commit()
            return user.current_order
        else:
            c = Customer.get_from_session()
            if c and c.current_order:
                return c.current_order
            else:
                return cls.from_session()

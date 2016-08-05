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


from flask import session
from flask_login import current_user
from pycountry import countries
from sqlalchemy import event
from sqlalchemy.exc import InvalidRequestError

from app import db
from app.db_helpers import TimestampMixin, USDollar
from app.shop.forms import AddProductForm


class TransactionExistsError(Exception):
    """Error for attempting to replace an existing `Transaction`."""
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
    name = db.Column(db.Text)
    abbreviation = db.Column(db.Text)
    country_id = db.Column(db.Integer, db.ForeignKey('countries.id'))
    country = db.relationship('Country', back_populates='states')
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
            country = Country.get_with_alpha3(alpha3)
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


class Country(db.Model):
    """Table for countries.

    Attributes:
        alpha3 - The alpha3 code for a country, e.g. "USA", "CAN", or "AUS".
        noship - Whether or not the `Country` can be shipped to.
        at_own_risk - Whether or not shipping to the `Country` is considered
            at the customer's own risk.
        states - First-level administrative divisions belonging
            to `Country`; For example, US states or Canadian provinces.
        noship_cultivars - A list of `Cultivars` that can't be shipped to the
            given `Country`.
    """
    __tablename__ = 'countries'
    id = db.Column(db.Integer, primary_key=True)
    _cached = None
    alpha3 = db.Column(db.Text)
    noship = db.Column(db.Boolean)
    at_own_risk = db.Column(db.Boolean)
    states = db.relationship('State', back_populates='country')
    # noship_cultivars - backref from seeds.models.Cultivar

    def __init__(self, alpha3=None):
        self.alpha3 = alpha3

    def __repr__(self):
        return '<Country: "{}">'.format(self.name)

    @classmethod
    def get_with_alpha3(cls, alpha3):
        """Load a `Country` with the given alpha3 from the database.

        Args:
            alpha3: The alpha3 code of the `Country` to load.

        Returns:
            The `Country` from the database with the given alpha3 code.
        """
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
        return self._country.name

    @property
    def numeric(self):
        """str: The numeric code of `Country`."""
        return self._country.numeric

    @property
    def official_name(self):
        """str: The official (long form) name of `Country`."""
        return self._country.official_name

    def get_state_by_abbr(self, abbr):
        """Return l1 admin division with given abbr, or `None`."""
        abbr = abbr.upper()
        return next(
            (d for d in self.states if d.abbreviation == abbr),
            None
        )


class Address(db.Model, TimestampMixin):
    """Table for addresses.

    Attributes:

        customer - The `Customer` an `Address` belongs to.
        first_name - The first name of the person the address belongs to.
        last_name - The last name of the person the address belongs to.
        business name - Optional business the address belongs to.
        city - The city portion of the address.
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
        back_populates='addresses')
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    business_name = db.Column(db.Text)
    address_line1 = db.Column(db.Text)
    address_line2 = db.Column(db.Text)
    city = db.Column(db.Text)
    country_id = db.Column(db.ForeignKey('countries.id'))
    country = db.relationship('Country')
    state_id = db.Column(db.ForeignKey('states.id'))
    state = db.relationship('State')
    unlisted_state = db.Column(db.Text)
    email = db.Column(db.Text)
    phone = db.Column(db.Text)
    fax = db.Column(db.Text)

    def __repr__(self):
        return '<{0} for: "{1}">'.format(self.__class__.__name__,
                                         self.fullname)

    @property
    def fullname(self):
        """str: The full name of the person the address belongs to."""
        parts = (self.first_name, self.last_name)
        return ' '.join(n for n in parts if n)


class Customer(db.Model, TimestampMixin):
    """Table for customer data.

    Attributes:

    billing_address - The billing address of the customer.
    shipping_address - The last-used shipping address of the customer.
    addresses - All addresses belonging to the customer.
    transactions - `Transaction` instances belonging to customer.
    current_transaction - `Transaction` in progress.
    """
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    billing_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    billing_address = db.relationship(
        'Address',
        foreign_keys=billing_address_id
    )
    shipping_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    shipping_address = db.relationship(
        'Address',
        foreign_keys=shipping_address_id
    )
    addresses = db.relationship(
        'Address',
        foreign_keys='Address.customer_id',
        back_populates='customer'
    )
    transactions = db.relationship(
        'Transaction',
        foreign_keys='Transaction.customer_id',
        post_update=True,
        back_populates='customer'
    )
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    current_transaction = db.relationship(
        'Transaction',
        foreign_keys=transaction_id
    )
    user = db.relationship(
        'User',
        back_populates='customer_data',
        uselist=False
    )

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
        if self.billing_address:
            return self.billing_address.first_name
        else:
            return None

    @first_name.setter
    def first_name(self, value):
        if not self.billing_address:
            self.billing_address = Address()
        self.billing_address.first_name = value


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


@event.listens_for(Customer.current_transaction, 'set')
def add_current_transaction_event(target, value, oldvalue, initiator):
    """Don't allow replacing `Customer.current_transaction` with another.

    Raises:
        TransactionExistsError - If a current transaction already exists.
    """
    if value is not None:
        if target.current_transaction is not None:
            raise TransactionExistsError(
                '{0} already has a transaction in progress!'
                .format(target)
            )
        else:
            if value not in target.transactions:
                target.transactions.append(value)


class Product(db.Model, TimestampMixin):
    """Table for products.

    Attributes:

    number - The ID number (usually a SKU) of the `Product`.
    label - The string used to label the `Product`.
    price - The price for one unit of the `Product`.
    transaction_lines - `TransactionLine` instances with a given `Product`.
    packet - A `Packet` corresponding to a `Product`.
    """
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    type_ = db.Column(db.Enum('packet', 'bulk', name='type_'))
    number = db.Column(db.Text, unique=True)
    label = db.Column(db.Text)
    price = db.Column(USDollar)
    transaction_lines = db.relationship(
        'TransactionLine',
        back_populates='product'
    )
    # packet: backref from app.seeds.models.Packet

    _form = None

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
    def form(self):
        """AddProductForm: A form for adding a `Product` to a transaction."""
        if not self._form:
            self._form = AddProductForm()
            self._form.number.data = self.number
        return self._form

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


class TransactionLine(db.Model, TimestampMixin):
    """Table for lines in a transaction.

    Note:
        The columns of `Product` are reproduced here because we want to keep
        the `Product` data as it was when the `TransactionLine` was last
        modified, regardless of changes to the `Product`.

    Attributes:
        transaction - The `Transaction` a `TransactionLine` belongs to.
        product - The `Product` the `TransactionLine` is for.
        quantity - The number of units of `Product`.
        product_number - The ID number of `Product`.
        label - The label of `Product`.
        price - The price of `Product`.
    """
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    transaction = db.relationship('Transaction', back_populates='lines')
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product = db.relationship('Product', back_populates='transaction_lines')
    quantity = db.Column(db.Integer)
    # Copied Product columns.
    product_number = db.Column(db.Text)
    label = db.Column(db.Text)
    price = db.Column(USDollar)

    def __init__(self, product=None, product_number=None, quantity=None):
        if product and product_number and product.number != product_number:
            raise ValueError(
                'Attempted to initialize a Transaction with a product and a '
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
        """Create a `TransactionLine` from `session_data`.

        Args:
            data: A `dict` as generated by `session_data`.
        """
        return cls(
            product_number=data['product number'],
            quantity=data['quantity']
        )

    @property
    def session_data(self):
        """dict: `TransactionLine` data to store in the user session.

        This is just the product number and quantity, as that's the only
        information that is necessary to create a `TransactionLine`.
        """
        return {
            'product number': self.product_number,
            'quantity': self.quantity
        }

    @property
    def text(self):
        """str: A string representing a `TransactionLine`'s data."""
        return '{0} of product #{1}: "{2}"'.format(self.quantity,
                                                   self.product_number,
                                                   self.label)

    @property
    def total(self):
        """Decimal: The total cost of products in a `TransactionLine`."""
        try:
            return self.quantity * self.price
        except TypeError:
            return None

    @property
    def in_stock(self):
        """bool: Whether or not the product on the line is in stock."""
        try:
            return self.product.in_stock
        except AttributeError:
            return False


@event.listens_for(TransactionLine.quantity, 'set')
def transaction_line_set_quantity_event(target, value, oldvalue, initiator):
    """Set the quantity of the associated product's form quantity."""
    # TODO: Make sure this doesn't result in undefined behavior.
    if value is not None and target.product:
        target.product.form.quantity.data = value


@event.listens_for(TransactionLine.product, 'set')
def transaction_line_set_product_event(target, value, oldvalue, initiator):
    """Copy relevant values when setting `TransactionLine.product`."""
    if value is not None:
        target.product_number = value.number
        target.label = value.label
        target.price = value.price


class Transaction(db.Model, TimestampMixin):
    """Table for transactions.

    Attributes:

    lines - `TransactionLine` instances belonging to this `Transaction`.
    status - The state the `Transaction` is in.
    customer - The `Customer` the `Transaction` belongs to.
    billed_to - The `Address` the `Transaction` was billed to.
    shipped_to - The `Address` the `Transaction` was shipped to.
    """
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    lines = db.relationship(
        'TransactionLine',
        back_populates='transaction',
        cascade='all, delete-orphan'
    )
    status = db.Column(db.Enum(
        'in progress',
        'pending payment',
        'payment rejected',
        'paid',
        'refunded',
        'shipped',
        name='status',
    ))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        post_update=True,
        back_populates='transactions'
    )
    billed_to_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    billed_to = db.relationship('Address', foreign_keys=billed_to_id)
    shipped_to_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    shipped_to = db.relationship('Address', foreign_keys=shipped_to_id)

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
        """Create a transaction from session_data.

        Args:
            data: A `dict` containing the data needed to create a new
            `Transaction`.

        Returns:
            Transaction - The created `Transaction`.
        """
        lines = []
        for d in data:
            product = Product.query.filter(
                Product.number == d['product number']
            ).one_or_none()
            if product:
                lines.append(TransactionLine(
                    product=product,
                    quantity=d['quantity']
                ))
        return cls(lines=lines)

    @classmethod
    def from_session(cls, session_key='cart'):
        """Create a transaction from session data.

        Args:
            session_key: A string to use as key in session to load session
                data from. Defaults to 'cart'.

        Returns:
            Transaction - The `Transaction` created from data in the session.
        """
        try:
            transaction = cls.from_session_data(session[session_key])
            if len(transaction.lines) != len(session[session_key]):
                # TODO: Inform customer that items in their cart are gone.
                pnos = [l.product_number for l in transaction.lines]
                for sline in list(session[session_key]):
                    if sline['product number'] not in pnos:
                        session[session_key].remove(sline)
            if transaction.lines:
                return transaction
            else:
                return None
        except KeyError:
            return None

    @property
    def session_data(self):
        return [l.session_data for l in self.lines]

    @property
    def text(self):
        lines_text = '\n'.join(l.text for l in self.lines)
        return 'Transaction #{0} with lines:\n{1}'.format(self.id, lines_text)

    @property
    def total(self):
        return sum(l.total for l in self.lines)

    def add_line(self, product_number, quantity):
        """Add a `TransactionLine`.

        Note:
            This creates a new `TransactionLine` instance regardless of whether
            or not the product is already in the `Transaction` so that the
            returned line reflects the quantity of product added rather than
            the total. If the product already exists in the `Transaction`, the
            created line will not be added to it, instead `quantity` will be
            added to the existing line.

        Args:
            product_number: The identifier of the product to add.
            quantity: The quantity of product to add.

        Returns:
            The created `TransactionLine` instance so its data can be used
            by the caller of `add_line`.
        """
        line = TransactionLine(
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
        """Get `TransactionLine` with given `product_number`.

        Args:
            product_number: The product number of the line to return.

        Returns:
            A `TransactionLine` with given `product_number`, or None if not
            present in `lines`.
        """
        return next(
            (l for l in self.lines if l.product_number == product_number),
            None
        )

    def change_line_quantity(self, product_number, quantity):
        """Set quantity of a given `TransactionLine`.

        Args:
            product_number: The number of the `Product` on the line.
            quantity: The new quantity of `Product` on the line.
        """
        self.get_line(product_number).quantity = quantity

    def delete_line(self, line):
        """Remove a `TransactionLine` and ensure it's deleted.

        Args:
            line: The `TransactionLine` to delete.
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
            # There is no reason to keep the transaction around if it's empty.
            try:
                db.session.delete(self)
                db.session.commit()
            except InvalidRequestError:
                pass

    def save_to_session(self, session_key='cart'):
        """Save a `Transaction` to the session.

        Args:
            session_key: A string to use as key in session under which to
                store transaction data.
        """
        session[session_key] = self.session_data

    def save(self, session_key='cart'):
        """Save a `Transaction` to the session and (if applicable) database.

        The `Transaction` will be saved to the database if it belongs to a
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
                    'Cannot attach a new customer to a transaction that '
                    'already has a customer associated with it!'
                )
            self.customer = current_user.customer_data
            db.session.commit()

        self.save_to_session(session_key)

    @classmethod
    def load(cls, user=None):
        """Load a transaction.

        Args:
            user: An optional `User` whom the transaction belongs to.

        Returns:
            The `User`'s current_transaction if present, otherwise the
            transaction from the session if present, otherwise `None`.
        """
        if not user.is_anonymous:
            if not user.current_transaction:
                user.current_transaction = cls.from_session()
                db.session.commit()
            return user.current_transaction
        else:
            return cls.from_session()

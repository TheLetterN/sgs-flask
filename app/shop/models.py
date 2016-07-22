import json
from pathlib import Path

from flask import session
from flask_login import current_user
from flask_sqlalchemy import SignallingSession
from pycountry import countries
from sqlalchemy import event

from app import current_app, db
from app.db_helpers import TimestampMixin, USDollar
from app.shop.forms import AddProductForm


class TransactionExistsError(Exception):
    """Error for attempting to replace an existing `Transaction`."""
    def __init__(self, message):
        self.message = message


US_POSTAL_ABBRS = {
    'AA': 'Armed Forces Americas (except Canada)',
    'AE': 'Armed Forces (Africa, Canada, Europe, Middle East)',
    'AP': 'Armed Forces Pacific',
    'AL': 'Alabama',
    'AK': 'Alaska',
    'AS': 'American Samoa',
    'AZ': 'Arizona',
    'AR': 'Arkansas',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DE': 'Delaware',
    'DC': 'District Of Columbia',
    'FM': 'Federated States Of Micronesia',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
    'HI': 'Hawaii',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'IA': 'Iowa',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'ME': 'Maine',
    'MH': 'Marshall Islands',
    'MD': 'Maryland',
    'MA': 'Massachusetts',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MS': 'Mississippi',
    'MO': 'Missouri',
    'MT': 'Montana',
    'NE': 'Nebraska',
    'NV': 'Nevada',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NY': 'New York',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'MP': 'Northern Mariana Islands',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PW': 'Palau',
    'PA': 'Pennsylvania',
    'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VT': 'Vermont',
    'VI': 'Virgin Islands',
    'VA': 'Virginia',
    'WA': 'Washington',
    'WV': 'West Virginia',
    'WI': 'Wisconsin',
    'WY': 'Wyoming'
}


class Address(db.Model, TimestampMixin):
    """An address."""
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        back_populates='addresses')
    first_name = db.Column(db.String(40))
    last_name = db.Column(db.String(40))
    middle_initials = db.Column(db.String(5))
    business_name = db.Column(db.String(100))
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(100))
    us_postal_abbr = db.Column(db.Enum(*US_POSTAL_ABBRS.keys()))
    country = db.Column(db.Enum(*(c.alpha3 for c in countries)))
    province_or_state = db.Column(db.String(40))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(25))
    fax = db.Column(db.String(25))

    def __repr__(self):
        return '<{0} for: "{1}">'.format(self.__class__.__name__,
                                         self.fullname)

    @property
    def fullname(self):
        parts = (self.first_name, self.middle_initials, self.last_name)
        return ' '.join(n for n in parts if n)


class Customer(db.Model, TimestampMixin):
    """A customer's data."""
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    billing_address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'))
    billing_address = db.relationship(
        'Address',
        foreign_keys=billing_address_id
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
    if value is not None and value not in target.addresses:
        target.addresses.append(value)


@event.listens_for(Customer.current_transaction, 'set')
def add_current_transaction_event(target, value, oldvalue, initiator):
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
    """A single product."""
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    type_ = db.Column(db.Enum('packet', 'bulk'))
    number = db.Column(db.String(15), unique=True)
    label = db.Column(db.String(100))
    price = db.Column(USDollar)
    transaction_lines = db.relationship(
        'TransactionLine',
        back_populates='product'
    )
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
        if number:
            obj = cls.query.filter(cls.number == number).one_or_none()
            if not obj:
                obj = cls(number=number)
        else:
            obj = cls()
        return obj

    @property
    def form(self):
        if not self._form:
            self._form = AddProductForm()
            self._form.number.data = self.number
        return self._form


class TransactionLine(db.Model, TimestampMixin):
    """Table for lines in a transaction.
    
    Note:
        The columns of `Product` are reproduced here because we want to keep
        the `Product` data as it was when the `TransactionLine` was last
        modified, regardless of changes to the `Product`.
    """
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'))
    transaction = db.relationship('Transaction', back_populates='lines')
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product = db.relationship('Product', back_populates='transaction_lines')
    quantity = db.Column(db.Integer)
    # Copied Product columns.
    product_number = db.Column(db.String(15))
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
    def from_session_data(self, data):
        """Create a `TransactionLine` from `session_data`.

        Args:
            data: A `dict` as generated by `session_data`.
        """
        return cls(
            product_number = data['product number'],
            quantity = data['quantity']
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
        return '{0} of product #{1}: "{2}"'.format(self.quantity,
                                                   self.product_number,
                                                   self.label)

    @property
    def total(self):
        """Return the total cost of products on line."""
        return self.quantity * self.price


@event.listens_for(TransactionLine.quantity, 'set')
def transaction_line_set_quantity_event(target, value, oldvalue, initiator):
    if value is not None and target.product:
        target.product.form.quantity.data = value


@event.listens_for(TransactionLine.product, 'set')
def transaction_line_set_product_event(target, value, oldvalue, initiator):
    if value is not None:
        target.product_number = value.number
        target.label = value.label
        target.price = value.price


class Transaction(db.Model, TimestampMixin):
    """A table for transactions."""
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    lines = db.relationship('TransactionLine', back_populates='transaction')
    status = db.Column(db.Enum(
        'in progress',
        'pending payment',
        'payment rejected',
        'paid',
        'refunded',
        'shipped',
    ))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        post_update=True,
        back_populates='transactions'
    )
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
        """Create a transaction from session_data."""
        lines = []
        for d in data:
            product = Product.query.filter(
                Product.number == d['product number']
            ).one_or_none()
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
        """
        try:
            return cls.from_session_data(session[session_key])
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
        if (user and not user.is_anonymous and user.customer_data and
                user.customer_data.current_transaction):
            return user.customer_data.current_transaction
        else:
            return cls.from_session()

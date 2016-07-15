import json
from pathlib import Path
from pycountry import countries
from sqlalchemy import event
from flask_sqlalchemy import SignallingSession

from app import current_app, db
from app.shop.forms import AddProductForm

#TMP
class TimestampMixin(object):
    """A mixin for classes that would benefit from tracking modifications.

    Attributes:

    created_on: The date and time an instance was created.
    updated_on: The date and time an instance was last updated.
    """
    created_on = db.Column(db.DateTime, server_default=db.func.now())
    updated_on = db.Column(db.DateTime, onupdate=db.func.now())


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
    price = db.Column(db.Numeric)
    transaction_lines = db.relationship(
        'TransactionLine',
        back_populates='product'
    )
    _form = None

    def __init__(self, number=None):
        self.number = number

    def __repr__(self):
        return '<{0} {1}: {2}$ for "{3}">'.format(self.__class__.__name__,
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
    price = db.Column(db.Numeric)

    def __init__(self, product=None, quantity=None):
        self.product = product
        self.quantity = quantity

    def __repr__(self):
        return '<{0}: {1} of "{2}">'.format(self.__class__.__name__,
                                            self.quantity,
                                            self.label)


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
    _status = db.Column(db.Enum(
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

    def __repr__(self):
        return '<{0} #{1}: {2} lines>'.format(self.__class__.__name__,
                                              self.id,
                                              len(self.lines))

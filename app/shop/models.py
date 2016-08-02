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


class USState(db.Model):
    __tablename__ = 'us_states'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True)
    abbreviation = db.Column(db.Text, unique=True)
    # noship_cultivars - backref from seeds.models.Cultivar

    def __repr__(self):
        return '<US State/Territory: "{}">'.format(self.name)

    @classmethod
    def generate_from_dict(cls, d):
        """Generate `USState` instances from a dict.

        The dict should countain abbreviations as keys and full names as
        values, eg: {'AL': 'Alabama', 'AK': 'Alaska', ... }

        Args:
            d - the `dict` to get state data from.
        """
        for abbr in d:
            yield cls(abbreviation=abbr, name=d[abbr])


class Address(db.Model, TimestampMixin):
    """An address."""
    __tablename__ = 'addresses'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    customer = db.relationship(
        'Customer',
        foreign_keys=customer_id,
        back_populates='addresses')
    first_name = db.Column(db.Text)
    last_name = db.Column(db.Text)
    middle_initials = db.Column(db.Text)
    business_name = db.Column(db.Text)
    address_line1 = db.Column(db.Text)
    address_line2 = db.Column(db.Text)
    city = db.Column(db.Text)
    us_state_id = db.Column(db.ForeignKey('us_states.id'))
    us_state = db.relationship('USState')
    country = db.Column(
        db.Enum(*(c.alpha3 for c in countries), name='country')
    )
    province_or_state = db.Column(db.Text)
    email = db.Column(db.Text)
    phone = db.Column(db.Text)
    fax = db.Column(db.Text)

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

    @property
    def cultivar(self):
        try:
            return self.packet.cultivar
        except AttributeError:
            return None


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
        return '{0} of product #{1}: "{2}"'.format(self.quantity,
                                                   self.product_number,
                                                   self.label)

    @property
    def total(self):
        """Return the total cost of products on line."""
        try:
            return self.quantity * self.price
        except TypeError:
            return None

    @property
    def in_stock(self):
        try:
            return self.product.cultivar.in_stock
        except AttributeError:
            return False


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

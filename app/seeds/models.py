from decimal import Decimal
from fractions import Fraction
from slugify import slugify
from sqlalchemy.ext.hybrid import hybrid_property
from app import db


def is_480th(value, verify_fraction=True):
    """Test whether or not a fraction can be converted to 480ths.

    Args:
        value: Value to test whether or not can be converted to 480ths.
        verify_fraction (optional[bool]): Whether or not to run is_fraction()
            during execution. Defaults to True, but can be turned off so we
            don't unnecessarily run is_fraction() again when running is_480th()
            in a block after is_fraction() has been run.

    Returns:
        True: If value can be converted to 480ths.
        False: If value cannot be converted to 480ths.
    """
    if verify_fraction:
        if not is_fraction(value):
            return False
    if isinstance(value, Fraction):
        if 480 % value.denominator == 0:
            return True
        else:
            return False
    elif isinstance(value, str):
        parts = value.strip().split('/')
        if 480 % int(parts[1]) == 0:
            return True
        else:
            return False
    else:
        return False


def is_decimal(value):
    """Test whether or not a value explicitly represents a decimal number.

    Note:
        Even though integers are valid decimal numbers, they should return
        False because we want to be able to differentiate between integers
        and decimal numbers.

    Args:
        value: A value to test type and contents of to determine whether or
            not it is a decimal number.

    Returns:
        True: If value represents a valid decimal number.
        False: If value does not represent a valid decimal number.
    """
    if isinstance(value, Decimal) or isinstance(value, float):
        return True
    elif isinstance(value, str):
        if value.count('.') == 1:
            parts = value.strip().split('.')
            if parts[0].isdigit() and parts[1].isdigit():
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def is_fraction(value):
    """Test whether or not a value represents a fraction.

    Args:
        value: A value to test type and contents of to determine whether
            or not it is a fraction.
    Returns:
        True: If value represents a valid fraction.
        False: If value does not represent a valid fraction.
    """
    if isinstance(value, Fraction):
        return True
    elif isinstance(value, str):
        if value.count('/') == 1:
            if ' ' in value:
                if value.strip().count(' ') == 1:
                    mixed = value.strip().split(' ')
                    if mixed[0].isdigit():
                        parts = mixed[1].split('/')
                        if parts[0].isdigit() and parts[1].isdigit():
                            if int(parts[1]) != 0:
                                return True
                            else:
                                return False
                        else:
                            return False
                    else:
                        return False
                else:
                    return False
            else:
                parts = value.split('/')
                if parts[0].isdigit() and parts[1].isdigit():
                    if int(parts[1]) != 0:
                        return True
                    else:
                        return False
        else:
            return False
    else:
        return False


def is_int(value):
    """Test whether or not a value is or contains an integer.

    Args:
        value: A value to test the type and contents of to determine whether
            or not it is/contains and integer.

    Returns:
        True: If value represents a valid integer.
        False: If value does not represent a valid integer.
    """
    if isinstance(value, int):
        return True
    elif isinstance(value, str):
        if value.strip().isdigit():
            return True
        else:
            return False
    else:
        return False


botanical_names_to_common_names = db.Table(
    'botanical_names_to_common_names',
    db.Model.metadata,
    db.Column('botanical_names_id',
              db.Integer,
              db.ForeignKey('botanical_names.id')),
    db.Column('common_names_id', db.Integer, db.ForeignKey('common_names.id'))
)


categories_to_seeds = db.Table(
    'categories_to_seeds',
    db.Model.metadata,
    db.Column('categories_id', db.Integer, db.ForeignKey('categories.id')),
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id'))
)


common_names_to_categories = db.Table(
    'common_names_to_categories',
    db.Model.metadata,
    db.Column('common_names_id',
              db.Integer,
              db.ForeignKey('common_names.id')),
    db.Column('categories_id', db.Integer, db.ForeignKey('categories.id'))
)


seeds_to_botanical_names = db.Table(
    'seeds_to_botanical_names',
    db.Model.metadata,
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('botanical_names_id',
              db.Integer,
              db.ForeignKey('botanical_names.id'))
)


seeds_to_common_names = db.Table(
    'seeds_to_common_names',
    db.Model.metadata,
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('common_names_id',
              db.Integer,
              db.ForeignKey('common_names.id'))
)


seeds_to_packets = db.Table(
    'seeds_to_packets',
    db.Model.metadata,
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('packets_id', db.Integer, db.ForeignKey('packets.id'))
)


class Quantity480th(db.TypeDecorator):
    """Type to store fractional quantities that can be converted to x/480.

    This covers every denominator between 1-16 except 7, 9, 11, 13, 14, which
    includes the most commonly used quantity denominators. It covers anything
    480 is divisible by in addition, though it's unlikely any denominators
    greater than 16 will be used in the context of seed quantities.

    Attributes:
        impl (Integer): The column type to decorate.
    """
    impl = db.Integer

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        else:
            return Quantity480th.to_480ths(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        else:
            return Quantity480th.from_480ths(value)

    @staticmethod
    def from_480ths(value):
        """Convert an int representing 480ths to a Fraction.

        Examples:
            >>> Quantity480th.from_480ths(240)
            Fraction(1, 2)

            >>> Quantity480th.from_480ths(400)
            Fraction(5, 6)

            >>> Quantity480th.from_480ths(6180)
            Fraction(103, 8)

        Args:
            value (int): An int representing 480ths.

        Returns:
            Fraction: A fraction with value as the numerator and 480 as the
                denominator.

        Raises:
            TypeError: if value is not an int.
        """
        if isinstance(value, int):
            return Fraction(value, 480)
        else:
            raise TypeError('value must be an int!')

    @staticmethod
    def to_480ths(value):
        """Convert a fraction to an int representing 480ths.

        We need to convert fractions to the lcd of 480 and store their
        numerators as integers in the database to maintain their relative
        sizes, thus allowing queries based on < or > to work correctly.

        Examples:
            >>> Quantity480th.to_480ths(Fraction(1, 2))
            240

            >>> Quantity480th.to_480ths('5/6')
            400

            >>> Quantity480th.to_480ths('12 7/8')
            6180

        Args:
            value: String representing a fraction, or a Fraction.

        Returns:
            int: Value converted to an int representing 480ths.

        Raises:
            ValueError: If value is a string that can't be parsed into a
                fraction.
            ValueError: If 480 is not divisible by value's denominator.
            TypeError: If value is not a Fraction or str.
        """
        if isinstance(value, str):
            if value.count('/') == 1 and value.count(' ') <= 1:
                if ' ' in value:
                    parts = value.split(' ')
                    frac = parts[1].split('/')
                    try:
                        num = int(parts[0]) * int(frac[1]) + int(frac[0])
                        den = int(frac[1])
                        value = Fraction(num, den)
                    except:
                        raise ValueError('string does not contain'
                                         ' a valid fraction!')
                else:
                    try:
                        parts = value.split('/')
                        value = Fraction(int(parts[0]), int(parts[1]))
                    except:
                        raise ValueError('string does not contain'
                                         ' a valid fraction!')
            else:
                raise ValueError('string does not contain a valid fraction!')
        if isinstance(value, Fraction):
            if 480 % value.denominator == 0:
                return value.numerator * (480 // value.denominator)
            else:
                raise ValueError('480 must be divisible by denominator!')
        raise TypeError('value must be a Fraction or a string!')


class QuantityDecimal(db.TypeDecorator):
    """Type to store decimal quantities as integers in the database.

    Since it is extremely unlikely we will ever need to represent a quantity
    as a decimal number with more than 4 digits to the right of the decimal,
    we just need to multiply all decimals by 10**4 and int them to store, and
    do the reverse to retrieve.

    Attributes:
        impl (Integer): Column type to decorate.
    """
    impl = db.Integer

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        else:
            return QuantityDecimal.decimal_to_int(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        else:
            return QuantityDecimal.int_to_decimal(value)

    @staticmethod
    def decimal_to_int(value):
        """Convert a decimal number to an int for use in the db.

        Anything past 4 digits to the right of the decimal will be truncated.

        Examples:
        >>> QuantityDecimal.decimal_to_int(Decimal('1.025'))
        10250

        >>> QuantityDecimal.decimal_to_int('1.4')
        14000

        >>> QuantityDecimal.decimal_to_int(3.14159256)
        31415

        Args:
            value: A Decimal or type that can be coerced to Decimal.

        Returns:
            int: Value as it should be stored in the database.

        Raises:
            ValueError: If value could not be coerced to Decimal.
        """
        if not isinstance(value, Decimal):
            # Prevent unexpected results from Decimal(float) conversion.
            if isinstance(value, float):
                value = str(value)
            try:
                value = Decimal(value)
            except:
                raise ValueError('value could not be parsed'
                                 ' as a decimal number!')
        return int(value * 10**4)

    @staticmethod
    def int_to_decimal(value):
        """Convert an int used in the db to a Decimal.

        Args:
            value (int): An int from the db to be converted back to a Decimal.

        Returns:
            Decimal: The decimal number the db int represents.

        Raises:
            TypeError: If value is not an int.
        """
        if isinstance(value, int):
            return Decimal(value) / 10**4
        else:
            raise TypeError('value can only be an int!')


class USDInt(db.TypeDecorator):
    """Type to store US dollar amounts in the database as integers.

    Since we don't know for sure how the database will handle decimal numbers,
    it is safer to store our dollar amounts as integers to avoid the risk of
    floating point errors leading to incorrect data.

    A USDInt column will store a value of 2.99 as 299 in the database, and
    return it as 2.99 when retrieved.
    """
    impl = db.Integer

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return USDInt.usd_to_int(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return USDInt.int_to_usd(value)

    @staticmethod
    def int_to_usd(amount):
        """Convert a db int to a Decimal representing a US dollar amount.

        Args:
            amount (int): The amount to convert from cents (int) to US
                dollars (Decimal).

        Returns:
            Decimal: US cents converted to US dollars and quantized to
                always have two digits to the right of the decimal.

        Raises:
            TypeError: If amount is not an integer.
        """
        if isinstance(amount, int):
            return (Decimal(amount) / 10**2).\
                quantize(Decimal('1.00'))
        else:
            raise TypeError('amount must be an integer!')

    @staticmethod
    def usd_to_int(amount):
        """Convert a dollar value to db int.

        Examples:

        Args:
            amount: Amount in US dollars to convert to an int (cents) for
                storage in db. Valid types are strings which appear to contain
                a dollar amount, or any type that can be converted to int.

        Returns:
            int: US dollar amount conveted to US cents so it can be stored in
                the database as an integer.

        Raises:
            ValueError: If given a string that can't be parsed as an amount in
                US dollars.
            TypeError: If given a non-string that can't be converted to int.
        """
        if isinstance(amount, str):
            try:
                amt = Decimal(amount.replace('$', '').strip())
                return int(amt * 10**2)
            except:
                raise ValueError('amount contains invalid '
                                 'characters or formatting!')
        elif isinstance(amount, Fraction):
            raise TypeError('amount must be a decimal or integer!')
        else:
            try:
                return int(amount * 10**2)
            except:
                raise TypeError('amount is of a type that could'
                                ' not be converted to int!')


class BotanicalName(db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. A correctly-formatted botanical name begins with a genus and species
    in binomial name format, or at least a genus followed by a descriptive
    comment.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        common_names (relationship): MtM relatinship with CommonName.
        _name (str): A botanical name associated with one or more seeds. Get
            and set via the name property.
        _seeds (backref): Backref from seeds table to allow us to look up seeds
            by botanical name.
    """
    __tablename__ = 'botanical_names'
    id = db.Column(db.Integer, primary_key=True)
    common_names = db.relationship('CommonName',
                                   secondary=botanical_names_to_common_names,
                                   backref='botanical_names')
    _name = db.Column(db.String(64), unique=True)

    def __init__(self, name=None):
        """Construct an instance of BotanicalName.

        Args:
            name (Optional[str]): A botanical name for a species of plant.
        """
        if name is not None:
            self.name = name

    def __repr__(self):
        """Return representation of BotanicalName in human-readable format.

        Returns:
            str: Representation formatted <BotanicalName '<.name>'> for
                 example: <BotanicalName 'Asclepias incarnata'>
        """
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.name)

    @hybrid_property
    def name(self):
        """str: The botanical name stored in ._name.

        Setter:
            Run data through .validate() and set ._name to it if valid.
            Raise a ValueError if data is not valid.
        """
        return self._name

    @name.setter
    def name(self, name):
        if self.validate(name):
            self._name = name
        else:
            raise ValueError('Botanical name must begin with two words in '
                             'the format of a binomen/scientific name!')

    @staticmethod
    def validate(botanical_name):
        """Return True if botanical_name is a validly formatted binomen.

        Valid within reason; some may contain more than 2 words, so we only
        check the first two words. This check is mostly to make it easier to
        avoid capitalization issues.

        Examples:
            >>> BotanicalName.validate('Asclepias incarnata')
            True

            >>> BotanicalName.validate('asclepias incarnata')
            False

            >>> BotanicalName.validate('ASCLEPIAS INCARNATA')
            False

            >>> BotanicalName.validate('Asclepias Incarnata')
            False

            >>> BotanicalName.validate('Digitalis interspecies hybrid')
            True

        Args:
            botanical_name (str): A string containing a botanical name to
                                  check for valid formatting.

        Returns:
            bool: True if botanical_name's first word looks like a valid genus
                  and the second word is all lowercase.
            bool: False if there are formatting errors in the first two words.
            bool: False if botanical_name.split() raises an exception, usually
                  due to botanical_name not being a string.
        """
        try:
            nomens = botanical_name.split(' ')
            if nomens[0][0].isupper() and \
                    nomens[0][1:].islower() and \
                    nomens[1].islower():
                return True
            else:
                return False
        except:
            return False


class Category(db.Model):
    """Table for seed categories.

    Categories are the first/broadest divisions we use to sort seeds. The
    category a seed falls under is usually based on what type of plant it is
    (herb, vegetable) or its life cycle. (perennial flower, annual flower)

    Attributes:
        __tablename__ (str): Name of the table: 'categories'
        id (int): Auto-incremented ID # for use as primary key.
        _category (str): The label for the category itself, such as 'Herb'
            or 'Perennial Flower'.
        description (str): HTML description information for the category.
        seeds (relationship): MtM relationship with Seed.
        slug (str): URL-friendly version of the category label.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    _category = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    seeds = db.relationship('Seed',
                            secondary=categories_to_seeds,
                            backref='_categories')
    slug = db.Column(db.String(64), unique=True)

    def __init__(self, category=None, description=None):
        """Construct an instance of Category.

        Args:
            category (Optional[str]): A category name.
            description (Optional[str]): A description for this category.
                This should be in raw HTML to allow for special formatting.
        """
        self.category = category
        self.description = description

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.category)

    @hybrid_property
    def category(self):
        """str: contents of ._category.

        Setter:
            Sets ._category, and generates a slugified version and sets .slug
            to it.
        """
        return self._category

    @category.expression
    def category(cls):
        return cls._category

    @category.setter
    def category(self, category):
        self._category = category
        if self._category is not None:
            self.slug = slugify(category)
        else:
            self.slug = None


class CommonName(db.Model):
    """Table for common names.

    A CommonName is the next subdivision below Category in how we sort seeds.
    It is usually the common name for the species or group of species a seed
    belongs to.

    Attributes:
        __tablename__ (str): Name of the table: 'seed_types'
        id (int): Auto-incremented ID # for use as primary_key.
        description (str): An optional description for the species/group
            of species with the given common name.
        name (str): The common name of a seed. Examples: Coleus, Tomato,
            Lettuce, Zinnia.
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    categories = db.relationship('Category',
                                 secondary=common_names_to_categories,
                                 backref='_common_names')
    description = db.Column(db.Text)
    _name = db.Column(db.String(64), unique=True)
    slug = db.Column(db.String(64), unique=True)

    def __init__(self, name=None, description=None):
        """Construct an instance of CommonName

        Args:
            name (Optional[str]): The common name for a seed or group of seeds.
            description (Optional[str]): An optional description for use on
            pages listing seeds of a given common name.
        """
        self.name = name
        self.description = description

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)

    @hybrid_property
    def name(self):
        """str: Return ._name

        Setter:
            Set ._name, and set .slug to a slugified version of ._name.
        """
        return self._name

    @name.expression
    def name(cls):
        return cls._name

    @name.setter
    def name(self, name):
        self._name = name
        if name is not None:
            self.slug = slugify(name)
        else:
            self.slug = None


class Packet(db.Model):
    """Table for seed packet information.

    Packet information includes data for each individual type of packet we
    sell, such as the size and price of a given packet. Each seed can have
    multiple different associated packets, due to different sizes (such as
    jumbo) and prices associated with different packet sizes.

    Attributes:
        __tablename__ (str): Name of the table: 'packets'
        id (int): Auto-incremented ID # for use as a primary key.
        _price (USDInt): Price (in US dollars) for this packet.
        _qty_decimal (relationship): MtO relationship with QtyDecimal.
        _qty_fraction (relationship): MtO relationship with QtyFraction.
        _qty_integer (relationship): MtO relationship with QtyInteger.
        unit_id (int): ForeignKey for associated Unit.
        _unit (relationship): MtO relationship with Unit.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    _price = db.Column(USDInt)
    qty_decimal_id = db.Column(db.Integer, db.ForeignKey('qty_decimals.id'))
    _qty_decimal = db.relationship('QtyDecimal', backref='_packets')
    qty_fraction_id = db.Column(db.Integer, db.ForeignKey('qty_fractions.id'))
    _qty_fraction = db.relationship('QtyFraction', backref='_packets')
    qty_integer_id = db.Column(db.Integer, db.ForeignKey('qty_integers.id'))
    _qty_integer = db.relationship('QtyInteger', backref='_packets')
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    _unit = db.relationship('Unit', backref='_packets')
    __table_args__ = (db.UniqueConstraint('_price',
                                          'unit_id'),)

    @hybrid_property
    def price(self):
        """Decimal: The value of ._price.

        Setter:
            Check type of data, set it as a Decimal if it's Decimal, int, or
            str, and raise a TypeError if not.
        """
        return self._price

    @price.expression
    def price(cls):
        return cls._price

    @price.setter
    def price(self, price):
        self._price = price

    @hybrid_property
    def quantity(self):
        """int/Decimal/Fraction: the quantity for this packet.

        Setter:
            Check type of data, set to ._qty_decimal, ._qty_fraction,
            or ._qty_decimal if possible, if not raise a ValueError.
        """
        retqty = None
        for qty in [self._qty_decimal, self._qty_fraction, self._qty_integer]:
            if qty is not None:
                if retqty is None:
                    retqty = qty
                else:
                    raise RuntimeError('More than one type of quantity'
                                       ' was detected for this packet. Only'
                                       ' one type of quantity may be set!')
        return retqty.value

# TODO: Get this working or scrap it.

#    class QuantityComparator(Comparator):
#        """Allow queries to search for quantities with the .quantity property.
#        """
#        def __init__(self, qty_decimal, qty_fraction, qty_integer):
#            self.qty_decimal = qty_decimal
#            self.qty_fraction = qty_fraction
#            self.qty_integer = qty_integer
#
#        def __eq__(self, other):
#            if is_decimal(other):
#                return self.qty_decimal.value == other
#            elif is_fraction(other):
#                if is_480th(other):
#                    return self.qty_fraction.value == other
#                else:
#                    raise ValueError('Cannot query using a fraction with a '
#                                     'denominator 480 is not divisible by!')
#            elif is_int(other):
#                return self.qty_fraction.value == other
#            else:
#                raise ValueError('Could not parse query value'
#                                 ' as a valid quantity!')
#
#    @quantity.comparator
#    def quantity(self):
#        return self.QuantityComparator(self._qty_decimal,
#                                        self._qty_fraction,
#                                        self._qty_integer)
#
    @quantity.setter
    def quantity(self, value):
        if is_decimal(value):
            self.clear_quantity()
            self._qty_decimal = QtyDecimal.query.filter_by(value=value).\
                first() or QtyDecimal(value)
        elif is_fraction(value):
            if is_480th(value):
                self.clear_quantity()
                self._qty_fraction = QtyFraction.query.filter_by(value=value).\
                    first() or QtyFraction(value)
            else:
                raise ValueError('Fractions must have denominators'
                                 ' 480 is divisible by!')
        elif is_int(value):
            self.clear_quantity()
            self._qty_integer = QtyInteger.query.filter_by(value=value).\
                first() or QtyInteger(value)
        else:
            raise ValueError('Could not determine appropriate type for '
                             'quantity! Please make sure it is a integer, '
                             'decimal number, or fraction.')

    @hybrid_property
    def unit(self):
        """str: The unit of measure associated with .quantity.

        Setter:
            Set ._unit with a Unit from the database if it exists, or a new
            Unit of not.
        """
        return self._unit.unit

    @unit.expression
    def unit(cls):
        return Unit.unit

    @unit.setter
    def unit(self, unit):
        uom = Unit.query.filter_by(unit=unit).first()  # uom = Unit of Measure
        if uom is not None:
            self._unit = uom
        else:
            self._unit = Unit(unit=unit)

    def clear_quantity(self):
        """Remove all quantities if any exist.

        Quantities are in ._quantity_decimal, ._quantity_fraction, or
        ._quantity_integer.

        Returns:
            int: Number of quantities removed. Should always return 1 or 0 if
                quantities are being used correctly.
        """
        count = 0
        if self._qty_decimal is not None:
            self._qty_decimal = None
            count += 1
        if self._qty_fraction is not None:
            self._qty_fraction = None
            count += 1
        if self._qty_integer is not None:
            self._qty_integer = None
            count += 1
        return count

    @staticmethod
    def quantity_equals(value):
        """Return a query that selects packets where .quantity = value.

        Args:
            value: The value to detect the type of and run an appropriate
                query for the type.

        Returns:
            Query: A Query object of the appropriate ._qty column where value
                = qty_<type>.value.
        """
        if is_decimal(value):
            return Packet.query.join(Packet._qty_decimal).\
                filter(QtyDecimal.value == value)
        elif is_fraction(value):
            if is_480th(value):
                return Packet.query.join(Packet._qty_fraction).\
                    filter(QtyFraction.value == value)
            else:
                raise ValueError('Fraction could not be converted to 480ths!')
        elif is_int(value):
            return Packet.query.join(Packet._qty_integer).\
                filter(QtyInteger.value == value)


class QtyDecimal(db.Model):
    """Table for quantities as decimals.

    Attributes:
        __tablename__ (str): Name of the table: 'qty_decimals'
        id (int): Auto-incremented ID # used as primary key.
        value (int): The quantity decimal stored as an integer in the db.
    """
    __tablename__ = 'qty_decimals'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(QuantityDecimal, unique=True)

    def __init__(self, value=None):
        if value is not None:
            self.value = value

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.value)


class QtyFraction(db.Model):
    """Table for quantities as fractions.

    Attributes:
        __tablename__ (str): Name of the table: 'qty_fractions'
        id (int): Auto-incremented ID # used as primary key.
        value (int): The quantity fraction stored as an integer in the db.
    """
    __tablename__ = 'qty_fractions'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(Quantity480th, unique=True)

    def __init__(self, value=None):
        if value is not None:
            self.value = value

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.value)


class QtyInteger(db.Model):
    """Table for quantities as integers.

    Attributes:
        __tablename__ (str): Name of the table: 'qty_integers'
        id (int): Auto-incremented ID # used as primary key.
        value (int): The quantity integer to store in db.
    """
    __tablename__ = 'qty_integers'
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, unique=True)

    def __init__(self, value=None):
        if value is not None:
            self.value = value

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.value)


class Seed(db.Model):
    """Table for seed data.

    This table contains the primary identifying information for a seed
    we sell. Generally, this is the table called to get and display seed
    data on the website.

    Attributes:
        __tablename__ (str): Name of the table: 'seeds'
        id (int): Auto-incremented ID # for use as primary key.
        botanical_name_id (int): Foreign key for BotanicalName.
        _botanical_name (relationship): MtO relationship with BotanicalName.
        _botanical_names (relationship): MtM relationship with BotanicalName.
        category_id (int): Foreign key for Category.
        _category (relationship): MtO relationship with Category.
        common_name_id (int): Foreign key for CommonName
        _common_name (relationship): MtO relationship with CommonName.
        _common_names (relationship): MtM relationship with CommonName.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
            if it will be discontinued when low.
        in_stock (bool): True if a seed is in stock, False if not.
        name (str): The name of the seed (cultivar); the main product name.
        packets (relationship): MtM relationship with Packet.
        sku (int): Product SKU.

    Backrefs:
        _categories: MtM backref fron Category.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    botanical_name_id = db.Column(db.Integer,
                                  db.ForeignKey('botanical_names.id'))
    _botanical_name = db.relationship('BotanicalName',
                                      foreign_keys=[botanical_name_id])
    _botanical_names = db.relationship('BotanicalName',
                                       secondary=seeds_to_botanical_names,
                                       backref='_seeds')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    _category = db.relationship('Category', foreign_keys=[category_id])
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    _common_name = db.relationship('CommonName',
                                   foreign_keys=[common_name_id])
    _common_names = db.relationship('CommonName',
                                    secondary=seeds_to_common_names,
                                    backref='_seeds')
    description = db.Column(db.Text)
    dropped = db.Column(db.Boolean)
    in_stock = db.Column(db.Boolean)
    name = db.Column(db.String(64), unique=True)
    packets = db.relationship('Packet',
                              secondary=seeds_to_packets,
                              backref='seeds')
    sku = db.Column(db.Integer, unique=True)

    def __repr__(self):
        """Return representation of Seed in human-readable format."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.name)

    @hybrid_property
    def botanical_name(self):
        """Return a single string botanical name for this seed.

        This is the primary botanical name for the seed.

        Returns:
            string: Botanical name for this seed.
        """
        return self._botanical_name.name

    @botanical_name.expression
    def botanical_name(cls):
        """Make botanical_name property usable in Seed.query."""
        return BotanicalName._name

    @botanical_name.setter
    def botanical_name(self, name):
        """Set _botanical_name from string to new or existing BotanicalName.

        Args:
            name (str): The botanical name to set.

        Raises:
            TypeError: If name is not a string.
        """
        if isinstance(name, str):
            bn = BotanicalName.query.filter_by(_name=name).first()
            if bn is not None:
                self._botanical_name = bn
            elif name in self.botanical_names:
                for bn in self._botanical_names:
                    if bn.name == name:
                        self._botanical_name = bn
            else:
                self._botanical_name = BotanicalName(name=name)
        else:
            raise TypeError('Botanical name must be a string!')

    @hybrid_property
    def botanical_names(self):
        """Return a list of the botanical names associated with this seed.

        Returns:
            list: A list of strings containing botanical names associated with
                  this seed.
        """
        return [bn.name for bn in self._botanical_names]

    @botanical_names.setter
    def botanical_names(self, names):
        """Clear _botanical_names and set it from given string or iterable.

        Args:
            names (list, str): A list of strings containing
                               botanical names, or a single string
                               containing a botanical name.

        Raises:
            TypeError: If names is iterable and contains non-strings.
            TypeError: If names is not a string or an iterable.
        """
        if isinstance(names, str):
            self.clear_botanical_names()
            if ',' in names:
                for bn in names.split(','):
                    self.add_botanical_name(bn.strip())
            else:
                self.add_botanical_name(names)
        else:
            try:
                if all(isinstance(bn, str) for bn in names):
                    self.clear_botanical_names()
                    for bn in names:
                        self.add_botanical_name(bn)
                else:
                    raise TypeError('An iterable passed to botanical_names '
                                    'can only contain strings!')
            except TypeError:
                raise TypeError('botanical_names can only be '
                                'a string or an iterable!')

    @hybrid_property
    def categories(self):
        """Return a list of ._categories.category.

        Returns:
            list: A list of strings containing categories associated with this
                  seed.
        """
        return [cat.category for cat in self._categories]

    @categories.setter
    def categories(self, categories):
        """Clear ._categories and set from a string or iterable.

        categories can either be a string containing a list with commas, a
        string containing a single category, or an iterable containing
        strings.

        Args:
            categories (str, iterable): A list of categories.
        """
        if isinstance(categories, str):
            self.clear_categories()
            if ',' in categories:
                for cat in categories.split(','):
                    self.add_category(cat.strip())
            else:
                self.add_category(categories)
        else:
            try:
                if all(isinstance(cat, str) for cat in categories):
                    self.clear_categories()
                    for cat in categories:
                        self.add_category(cat)
                else:
                    raise TypeError('Iterables set to categories '
                                    'must only contain strings!')
            except TypeError:
                raise TypeError('categories can only be set with a string '
                                'or an iterable containing strings!')

    @hybrid_property
    def category(self):
        """Return the primary category associated with this seed.

        Returns:
            str: Category for this seed.
        """
        return self._category.category

    @category.expression
    def category(cls):
        """Make the .category property usable in Seed.query."""
        return Category.category

    @category.setter
    def category(self, category):
        """Set ._category to a new or existing Category.

        Args:
            category (str): The primary category for this seed.
        """
        if isinstance(category, str):
            if category in self.categories:
                for cat in self._categories:
                    if cat.category == category:
                        self._category = cat
            else:
                cat = Category.query.filter_by(category=category).first()
                if cat is not None:
                    self._category = cat
                else:
                    self._category = Category(category=category)
        else:
            raise TypeError('.category must be a string!')

    @hybrid_property
    def common_name(self):
        """Return the primary common name associated with this seed.

        Returns:
            str: Common name for this seed.
        """
        return self._common_name.name

    @common_name.expression
    def common_name(cls):
        """Make common_name property usable in Seed.query."""
        return CommonName.name

    @common_name.setter
    def common_name(self, name):
        """Set ._common_name to a new or existing CommonName.

        Args:
            name (str): The common name to set.
        Raises:
            TypeError: If name is not a string.
        """
        if isinstance(name, str):
            cn = CommonName.query.filter_by(name=name).first()
            if cn is not None:
                self._common_name = cn
            elif name in self.common_names:
                for cn in self._common_names:
                    if cn.name == name:
                        self._common_name = cn
            else:
                self._common_name = CommonName(name=name)
        else:
            raise TypeError('Common name must be a string!')

    @hybrid_property
    def common_names(self):
        """Return a list of common names associated with this seed as strs.

        Returns:
            list: A list of strings containing common names associated with
                  this seed.
        """
        return [cn.name for cn in self._common_names]

    @common_names.setter
    def common_names(self, names):
        """Set a string or iterable of strings to .common_names.

        Args:
            names (str, iterable): The name or names to set.
        """
        if isinstance(names, str):
            self.clear_common_names()
            if ',' in names:
                for cn in names.split(','):
                    self.add_common_name(cn.strip())
            else:
                self.add_common_name(names)
        else:
            try:
                if all(isinstance(cn, str) for cn in names):
                    self.clear_common_names()
                    for cn in names:
                        self.add_common_name(cn)
                else:
                    raise TypeError('An iterable passed to common_names '
                                    'may only contain strings!')
            except TypeError:
                raise TypeError('common_names can only be set '
                                'with a string or an iterable!')

    def add_botanical_name(self, name):
        """Add a botanical name to _botanical_names.

        Args:
            name (str): A botanical name to add to _botanical_names.
        """
        if name not in self.botanical_names:
            if self._botanical_name is not None and \
                    self.botanical_name == name:
                self._botanical_names.append(self._botanical_name)
            else:
                bn = BotanicalName.query.filter_by(name=name).\
                    first()
                if bn is not None:
                    self._botanical_names.append(bn)
                else:
                    self._botanical_names.append(BotanicalName(name=name))
        # Do nothing if name is in self.botanical_names already.

    def add_category(self, category):
        """Add a category to ._categories.

        Args:
            category (str): A category to add to ._categories.

        Raises:
            TypeError: If category is not a string.
        """
        if isinstance(category, str):
            if category not in self.categories:
                if self._category is not None and self.category == category:
                    self._categories.append(self._category)
                else:
                    cat = Category.query.filter_by(category=category).first()
                    if cat is not None:
                        self._categories.append(cat)
                    else:
                        self._categories.append(Category(category=category))
            # Do nothing if category is already in self.categories.
        else:
            raise TypeError('Category must be a string!')

    def add_common_name(self, name):
        """Add a common name to ._common_names.

        Args:
            name (str): A common name to add to _common_names.

        Raises:
            TypeError: If name is not a string.
        """
        if isinstance(name, str):
            if name not in self.common_names:
                if self._common_name is not None and self.common_name == name:
                    self._common_names.append(self._common_name)
                else:
                    cn = CommonName.query.filter_by(name=name).first()
                    if cn is not None:
                        self._common_names.append(cn)
                    else:
                        self._common_names.append(CommonName(name=name))
            # Do nothing if name is in self.common_names already.
        else:
            raise TypeError('Common name must be a string!')

    def clear_botanical_names(self):
        """Clear _botanical_names without deleting them from the database.

        To delete them from the database, use Seed._botanical_names.delete().

        Returns:
            int: The number of botanical names removed.
        """
        count = 0
        while len(self._botanical_names) > 0:
            self._botanical_names.remove(self._botanical_names[0])
            count += 1
        return count

    def clear_categories(self):
        """Clear ._categories without deleting them from the database.

        To delete them from the database, use Seed._categories.delete().

        Returns:
            int: The number of categories removed.
        """
        count = 0
        while len(self._categories) > 0:
            self._categories.remove(self._categories[0])
            count += 1
        return count

    def clear_common_names(self):
        """Clear ._common_names without deleting them from the database.

        This only unlinks them from ._common_names. To delete them from the
        database, use Seed._common_names.delete()

        Returns:
            int: The number of common names removed.
        """
        count = 0
        while len(self._common_names) > 0:
            self._common_names.remove(self._common_names[0])
            count += 1
        return count

    def remove_botanical_name(self, name):
        """Remove a botanical name from _botanical_names.

        This does not delete it form the database, as other seeds may still
        need to use it.

        Args:
            name (str): The botanical name to remove.

        Returns:
            bool: False if name is not in _botanical_names.
            bool: True if name was in _botanical_names and has been removed.
        """
        bn = None
        for bot_name in self._botanical_names:
            if bot_name._name == name:
                bn = bot_name
        if bn is None:
            return False
        else:
            self._botanical_names.remove(bn)
            return True


class Series(db.Model):
    """Table for seed series.

    A series is an optional subclass of a given seed type, usually created by
    the company that created the cultivars within the series. Examples include
    Benary's Giant (zinnias), Superfine Rainbow (coleus), and Heat Elite Mambo
    (petunias).

    Attributes:
        __tablename__ (str): Name of the table: 'series'
        id (int): Auto-incremented ID # for use as primary key.
        label (str): The name of the series.
    """
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)


class SeriesDesc(db.Model):
    """Table for the optional description for a series.

    Attributes:
        __tablename__ (str): Name of the table: 'series_desc'
        id (int): Auto-incremented ID # for use as primary key.
        content (str): The actual description of the series.
    """
    __tablename__ = 'series_desc'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)


class Unit(db.Model):
    """Table for units of measure.

    Attributes:
        __tablename__ (str): Name of the table: 'units'
        id (int): Auto-incremented ID # for use as primary key.
        unit (str): The unit of measurement for a packet's quantity.

    Backrefs:
        _packets: backref from Packet to allow us to look up packets
                  by unit.
    """
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.String(32), unique=True)

    def __init__(self, unit=None):
        """Construct an instance of Unit.

        Args:
            unit (str): A unit of measure for use in a Packet. Examples:
                'count', 'oz', 'grams'.
        """
        self.unit = unit

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.unit)


if __name__ == '__main__':  # pragma: no cover
    import doctest
    doctest.testmod()

from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from decimal import Decimal
from app import db


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
        return int(value * 10**2)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(value) / 10**2

categories_to_seeds = db.Table(
    'categories_to_seeds',
    db.Model.metadata,
    db.Column('categories_id', db.Integer, db.ForeignKey('categories.id')),
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id'))
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


class BotanicalName(db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. A correctly-formatted botanical name begins with a genus and species
    in binomial name format, or at least a genus followed by a descriptive
    comment.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        _name (str): A botanical name associated with one or more seeds. Get
            and set via the name property.
        _seeds (backref): Backref from seeds table to allow us to look up seeds
            by botanical name.
    """
    __tablename__ = 'botanical_names'
    id = db.Column(db.Integer, primary_key=True)
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
        category (str): The label for the category itself, such as 'Herb'
                        or 'Perennial Flower'.
        description (str): HTML description information for the category.
        _seeds (relationship): MtM relationship with Seed.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)
    _seeds = db.relationship('Seed',
                             secondary=categories_to_seeds,
                             backref='_categories')

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
    description = db.Column(db.Text)
    name = db.Column(db.String(64), unique=True)

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


class Packet(db.Model):
    """Table for seed packet information.

    Packet information includes data for each individual type of packet we
    sell, such as the size and price of a given packet. Each seed can have
    multiple different associated packets, due to different sizes (such as
    jumbo) and prices associated with different packet sizes.

    Attributes:
        __tablename__ (str): Name of the table: 'packets'
        id (int): Auto-incremented ID # for use as a primary key.
        _price (str): Price (in US dollars) for this packet.
        _quantity (str): Amount of seeds in packet.
        unit_id (int): ForeignKey for associated Unit.
        _unit (relationship): MtO relationship with Unit.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    _price = db.Column(USDInt)
    _quantity = db.Column(db.Integer)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    _unit = db.relationship('Unit', backref='_packets')
    __table_args__ = (db.UniqueConstraint('_price',
                                          '_quantity',
                                          'unit_id'),)

    @hybrid_property
    def price(self):
        """Decimal: The value of ._price.

        Setter:
            Check type of data, set it as a Decimal if it's Decimal, int, or
            str, and raise a TypeError if not.
        """
        return self._price.quantize(Decimal('1.00'))

    class PriceComparator(Comparator):
        """Allow Packets to be queried by price without needing to use Decimals.

        Without this comparator, to get all packets with a price of 2.99 you
        would need to query:

        Packet.query.filter_by(price=Decimal('2.99')).all()
        """
        def __eq__(self, other):
            return self.__clause_element__() == Packet.price_to_decimal(other)

        def __lt__(self, other):
            return self.__clause_element__() < Packet.price_to_decimal(other)

        def __gt__(self, other):
            return self.__clause_element__() > Packet.price_to_decimal(other)

    @price.comparator
    def price(cls):
        return Packet.PriceComparator(cls._price)

    @price.setter
    def price(self, price):
        self._price = Packet.price_to_decimal(price)

    @hybrid_property
    def quantity(self):
        """str: ._quantity in human readable format.

        See .quantity_str_from_int() and .quantity_int_from_str() for more
        details.

        Setter:
            Converts a string containing a quantity to an integer and sets
            ._quantity to it.
        """
        return self.quantity_str_from_int(self._quantity)

    @quantity.setter
    def quantity(self, quantity):
        self._quantity = self.quantity_int_from_str(quantity)

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

    @staticmethod
    def price_to_decimal(price):
        """Convert an integer, float, or string to a Decimal value.

        Examples:
            >>> Packet.price_to_decimal(1)
            Decimal('1')

            >>> Packet.price_to_decimal(2.99)
            Decimal('2.99')

            >>> Packet.price_to_decimal('2.99')
            Decimal('2.99')

        Returns:
            Decimal: Decimal value of price.

        Raises:
            ValueError: If given a string containing invalid characters.
            TypeError: If given data that is not an int, float, string, or
                Decimal.
        """
        if isinstance(price, Decimal):
            return price
        elif isinstance(price, int) or isinstance(price, str):
            try:
                return Decimal(price)
            except:
                raise ValueError('Could not convert price to a Decimal value,'
                                 ' perhaps it contains invalid characters?')
        elif isinstance(price, float):
            return Decimal(str(price))
        else:
            raise TypeError('price must be a Decimal, str, int, or float!')

    @staticmethod
    def quantity_int_from_str(quantity):
        """Convert a string representing a quantity into an integer for db.

        The lowest digit  of the integer represents how many digits are to
        the right of the . or the / in the number if it contains a fractional
        part.

        If the fractional part is decimal, the resulting integer will be
        positive.
        If the fractional part is a fraction, the resulting integer will be
        negative.

        Examples:
            >>> Packet.quantity_int_from_str('100')
            1000

            >>> Packet.quantity_int_from_str('1/4')
            -141

            >>> Packet.quantity_int_from_str('3.14159265')
            3141592658

        Args:
            quantity (str): The size/quantity of a packet.

        Returns:
            int: The converted integer value for use in the database.

        Raises:
            TypeError: If quantity is not a string.
            ValueError: If quantity contains both . and /.
            ValueError: If quantity is decimal and contains a fractional
                part with more than 9 digits.
            ValueError: If quantity can't be parsed as a valid number.
            ValueError: If quantity contains more than one decimal.
            ValueError: If quantity is a fraction and contains a denominator
                with more than 9 digits.
            ValueError: If quantity contains more than one forward slash.
        """
        if not isinstance(quantity, str):
            raise TypeError('quantity must be a string!')
        quantity = quantity.replace(' ', '')
        if '.' in quantity and '/' in quantity:
            raise ValueError('quantity must be a decimal '
                             'or fraction, not both!')
        if '.' in quantity:
            parts = quantity.split('.')
            if len(parts) == 2:
                if len(parts[1]) > 9:
                        raise ValueError('quantity can only hold '
                                         'up to 9 decimal places!')
                if parts[0].isdigit() and parts[1].isdigit():
                    return int(''.join(parts)) * 10 + len(parts[1])
                else:
                    raise ValueError('quantity must be a number!')
            else:
                raise ValueError('quantity can only contain one decimal!')
        elif '/' in quantity:
            parts = quantity.split('/')
            if len(parts) == 2:
                if len(parts[1]) > 9:
                    raise ValueError('quantity can only have a denominator '
                                     'of up to 9 digits!')
                if parts[0].isdigit() and parts[1].isdigit():
                    return -(int(''.join(parts)) * 10 + len(parts[1]))
                else:
                    raise ValueError('quantity must be a number!')
            else:
                raise ValueError('quantity can only contain '
                                 'one forward slash!')
        else:
            if quantity.isdigit():
                return int(quantity) * 10
            else:
                raise ValueError('quantity must be a number!')

    @staticmethod
    def quantity_str_from_int(quantity):
        """Convert an int in db storage format to a readable string.

        The lowest digit of the int represents the number of digits in the
        fractional part, and the integer is positive if it represents a
        decimal value, negative if it represents a fraction.

        Examples:
            >>> Packet.quantity_str_from_int(1000)
            '100'

            >>> Packet.quantity_str_from_int(-141)
            '1/4'

            >>> Packet.quantity_str_from_int(3141592658)
            '3.14159265'

        Args:
            quantity (int): An integer presumably from the database that
                represents a quantity as stored in the db.

        Returns:
            str: A string containing the quantity in a human-readable format.

        Raises:
            ValueError: Negative integers ending in 0 cannot be converted, as
                they would result in a fraction with no denominator.
            TypeError: If given non-int data.
        """
        if isinstance(quantity, int):
            if quantity > 0:
                decimal = quantity % 10
                if decimal == 0:
                    return str(quantity)[:-1]
                else:
                    return str(quantity)[:-1 - decimal] + \
                        '.' + str(quantity)[-1 - decimal:-1]
            else:
                quantity = quantity * -1
                fractional = quantity % 10
                if fractional == 0:
                    raise ValueError('The fraction generated by this '
                                     'number would have no denominator!')
                else:
                    numerator = quantity // 10**(1 + fractional)
                    denominator = (quantity % 10**(1 + fractional) // 10)
                    return str(numerator) + '/' + str(denominator)
        else:
            raise TypeError('quantity must be an integer!')


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
        common_name_id (int): Foreign key for CommonName
        _common_name (relationship): MtO relationship with CommonName.
        _common_names (relationship): MtM relationship with CommonName.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
                        if it will be discontinued when low.
        in_stock (bool): True if a seed is in stock, False if not.
        name (str): The name of the seed (cultivar); the main product name.
        _packets (relationship): MtM relationship with Packet.

    Backrefs:
        _categories: MtM backref fron Category.

    Properties:
        botanical_name: Used to interface with the ._botanical_name MtO
                        relationship.
        botanical_names: Used to interface with the ._botanical_names MtM
                         relationship.
        common_name: Used to interface with the ._common_name MtO
                     relationship.
        common_names: Used to interface with the ._common_names MtM
                      relationship.
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
    _packets = db.relationship('Packet',
                               secondary=seeds_to_packets,
                               backref='_seeds')

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

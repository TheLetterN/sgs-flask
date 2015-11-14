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


import os
from decimal import Decimal
from flask import current_app
from fractions import Fraction
from inflection import pluralize
from slugify import slugify
from sqlalchemy.ext.hybrid import hybrid_property
from titlecase import titlecase
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


botanical_name_synonyms = db.Table(
    'botanical_name_synonyms',
    db.Model.metadata,
    db.Column('syn_parents_id',
              db.Integer,
              db.ForeignKey('botanical_names.id')),
    db.Column('synonyms_id', db.Integer, db.ForeignKey('botanical_names.id'))
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


common_name_synonyms = db.Table(
    'common_name_synonyms',
    db.Model.metadata,
    db.Column('syn_parents_id', db.Integer, db.ForeignKey('common_names.id')),
    db.Column('synonyms_id', db.Integer, db.ForeignKey('common_names.id'))
)


cns_to_gw_cns = db.Table(
    'cns_to_gw_cns',
    db.Model.metadata,
    db.Column('common_name_id', db.Integer, db.ForeignKey('common_names.id')),
    db.Column('gw_common_name_id',
              db.Integer, 
              db.ForeignKey('common_names.id'))
)


gw_common_names_to_gw_seeds = db.Table(
    'gw_common_names_to_gw_seeds',
    db.Model.metadata,
    db.Column('common_names_id', db.Integer, db.ForeignKey('common_names.id')),
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id'))
)


seeds_to_gw_seeds = db.Table(
    'seeds_to_gw_seeds',
    db.Model.metadata,
    db.Column('seed_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('gw_seed_id', db.Integer, db.ForeignKey('seeds.id'))
)


seed_synonyms = db.Table(
    'seed_synonyms',
    db.Model.metadata,
    db.Column('syn_parents_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('synonyms_id', db.Integer, db.ForeignKey('seeds.id'))
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
        if value is None:  # pragma: no cover
            return None
        return USDInt.usd_to_int(value)

    def process_result_value(self, value, dialect):
        if value is None:  # pragma: no cover
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
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='botanical_names')
    syn_parents = db.relationship('BotanicalName',
                                  secondary=botanical_name_synonyms,
                                  backref='synonyms',
                                  primaryjoin=id==botanical_name_synonyms.c.syn_parents_id,
                                 secondaryjoin=id==botanical_name_synonyms.c.synonyms_id)
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

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas."""
        return ', '.join([syn.name for syn in self.synonyms])

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas."""
        syns = synlist.split(', ')
        syns = [titlecase(syn) for syn in syns]
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents:
                        db.session.delete(synonym)
                        db.session.commit()
        for syn in syns:
            synonym = BotanicalName.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                synonym = BotanicalName()
                synonym.name = syn
                self.synonyms.append(synonym)


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
                            backref='categories')
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
            Sets ._category, and sets .slug to a pluralized, slugified version
                of ._category.
        """
        return self._category

    @category.expression
    def category(cls):
        return cls._category

    @category.setter
    def category(self, category):
        self._category = category
        if category is not None:
            self.slug = slugify(pluralize(category))
        else:
            self.slug = None

    @property
    def header(self):
        """str: contents of ._category in a str for headers, titles, etc."""
        # TODO : Maybe make the string setable via config?
        return '{0} Seeds'.format(self._category)

    @property
    def plural(self):
        """str: plural form of ._category."""
        return pluralize(self._category)


class CommonName(db.Model):
    """Table for common names.

    A CommonName is the next subdivision below Category in how we sort seeds.
    It is usually the common name for the species or group of species a seed
    belongs to.

    Attributes:
        __tablename__ (str): Name of the table: 'seed_types'
        id (int): Auto-incremented ID # for use as primary_key.
        categories (relationship): MtM relationship with Category.
        description (str): An optional description for the species/group
            of species with the given common name.
        _name (str): The common name of a seed. Examples: Coleus, Tomato,
            Lettuce, Zinnia.
        parent_id (int): Foreign key for parent/children relationship.
        parent (relationship): OtM relationship with CommonName allowing for
            subcategories of common name, such as Coleus > Dwarf Coleus
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    categories = db.relationship('Category',
                                 secondary=common_names_to_categories,
                                 backref='common_names')
    description = db.Column(db.Text)
    gw_common_names = db.relationship('CommonName',
                                      secondary=cns_to_gw_cns,
                                      primaryjoin=id==cns_to_gw_cns.c.common_name_id,
                                      secondaryjoin=id==cns_to_gw_cns.c.gw_common_name_id)
    instructions = db.Column(db.Text)
    _name = db.Column(db.String(64), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    parent = db.relationship('CommonName',
                             backref='children',
                             foreign_keys=parent_id,
                             remote_side=[id])
    slug = db.Column(db.String(64), unique=True)
    syn_parents = db.relationship('CommonName',
                                 secondary=common_name_synonyms,
                                 backref='synonyms',
                                 primaryjoin=id==common_name_synonyms.c.syn_parents_id,
                                 secondaryjoin=id==common_name_synonyms.c.synonyms_id)

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

    @property
    def header(self):
        """str: ._name formatted for headers and titles."""
        return '{0} Seeds'.format(self._name)

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

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas."""
        return ', '.join([syn.name for syn in self.synonyms])

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas."""
        if not synlist:
            self.synonyms = None
        syns = synlist.split(', ')
        syns = [titlecase(syn) for syn in syns]
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents:
                        db.session.delete(synonym)
                        db.session.commit()
        for syn in syns:
            synonym = CommonName.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                synonym = CommonName()
                synonym.name = syn
                self.synonyms.append(synonym)


class Image(db.Model):
    """Table for image information.

    Any image uploaded to be used with the seed model should utilize this
    table for important image data like filename and location.
    __tablename__ (str): Name of the table: 'images'
    id (int): Auto-incremended ID # for use as primary key.
    filename (str): File name of an image.
    seed_id (int): Foreign key from Seed to allow Seed to have a OtM
        relationship with Image.
    """
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(32))
    seed_id = db.Column(db.Integer, db.ForeignKey('seeds.id', use_alter=True))

    def __init__(self, filename=None):
        self.filename = filename

    @property
    def full_path(self):
        """Return the full absolute path to this Image's file."""
        return os.path.join(current_app.config.get('IMAGES_FOLDER'),
                            self.filename)

    def delete_file(self):
        """Deletes the image file associated with this Image object.

        Note:
            The lack of exception handling is intentional, exceptions should
            be handled where this function is called.
        """
        os.remove(self.full_path)

    def exists(self):
        """Check whether or not file associated with this Image exists."""
        return os.path.exists(self.full_path)


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
        sku (str): Product SKU for the packet.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    price_id = db.Column(db.Integer, db.ForeignKey('prices.id'))
    _price = db.relationship('Price', backref='_packets')
    qty_decimal_id = db.Column(db.Integer, db.ForeignKey('qty_decimals.id'))
    _qty_decimal = db.relationship('QtyDecimal', backref='_packets')
    qty_fraction_id = db.Column(db.Integer, db.ForeignKey('qty_fractions.id'))
    _qty_fraction = db.relationship('QtyFraction', backref='_packets')
    qty_integer_id = db.Column(db.Integer, db.ForeignKey('qty_integers.id'))
    _qty_integer = db.relationship('QtyInteger', backref='_packets')
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    _unit = db.relationship('Unit', backref='_packets')
    seed_id = db.Column(db.Integer, db.ForeignKey('seeds.id'))
    sku = db.Column(db.String(32), unique=True)

    @hybrid_property
    def price(self):
        """Decimal: The value of ._price.

        Setter:
            Check type of data, set it as a Decimal if it's Decimal, int, or
            str, and raise a TypeError if not.
        """
        return self._price.price

    @price.expression
    def price(cls):
        return Price.price

    @price.setter
    def price(self, price):
        pc = Price.query.filter_by(price=price).first()
        if pc is not None:
            self._price = pc
        else:
            self._price = Price(price=price)

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


class Price(db.Model):
    """Table for prices in US Dollars.

    Attributes:
        __tablename__ (str): Name of the table: 'prices'
        id (int): Auto-incremended ID # used as primary key.
        price (USDInt): Column for holding prices in US dollars.
    """
    __tablename__ = 'prices'
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(USDInt, unique=True)

    def __init__(self, price=None):
        if price is not None:
            self.price = price


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
        botanical_names (relationship): MtM relationship with BotanicalName.
        common_names (relationship): MtM relationship with CommonName.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
            if it will be discontinued when low.
        in_stock (bool): True if a seed is in stock, False if not.
        images (relationship): OtM relationship with Image.
        _name (str): The name of the seed (cultivar); the main product name.
        packets (relationship): OtM relationship with Packet.
        slug (str): A URL-friendly version of _name.
        thumbnail_id (int): ForeignKey of Image, used with thumbnail.
        thumbnail (relationship): MtO relationship with Image for specifying
            a thumbnail for seed.

    Backrefs:
        _categories: MtM backref fron Category.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    botanical_name_id = db.Column(db.Integer,
                                  db.ForeignKey('botanical_names.id'))
    botanical_name = db.relationship('BotanicalName',
                                      backref='seeds')
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='seeds')
    description = db.Column(db.Text)
    dropped = db.Column(db.Boolean)
    gw_common_names = db.relationship('CommonName',
                                      secondary=gw_common_names_to_gw_seeds,
                                      backref='gw_seeds')
    gw_seeds = db.relationship('Seed',
                               secondary=seeds_to_gw_seeds,
                               primaryjoin=id==seeds_to_gw_seeds.c.seed_id,
                               secondaryjoin=id==seeds_to_gw_seeds.c.gw_seed_id)
    images = db.relationship('Image', foreign_keys=Image.seed_id)
    in_stock = db.Column(db.Boolean)
    _name = db.Column(db.String(64), unique=True)
    packets = db.relationship('Packet',
                              cascade='all, delete-orphan',
                              backref='seed')
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'))
    series = db.relationship('Series', backref='seeds')
    slug = db.Column(db.String(64), unique=True)
    syn_parents = db.relationship('Seed',
                                 secondary=seed_synonyms,
                                 backref='synonyms',
                                 primaryjoin=id==seed_synonyms.c.syn_parents_id,
                                 secondaryjoin=id==seed_synonyms.c.synonyms_id)
    thumbnail_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    thumbnail = db.relationship('Image', foreign_keys=thumbnail_id)

    def __repr__(self):
        """Return representation of Seed in human-readable format."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.name)

    @hybrid_property
    def fullname(self):
        """str: Full name of seed including common name and series."""
        fn = []
        if self._name:
            fn.append(self._name)
        if self.common_name:
            fn.append(self.common_name.name)
        if fn:
            return ' '.join(fn)
        else:
            return None

    @hybrid_property
    def name(self):
        """str: contents series + _name.

        Setter:
            Sets ._name, and generates a slug and sets .slug.
        """
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        if value is not None:
            self.slug = slugify(value)
        else:
            self.slug = None

    @hybrid_property
    def thumbnail_path(self):
        """str: The full path to this seed's thumbnail file."""
        if self.thumbnail:
            return os.path.join('images',
                                self.thumbnail.filename)
        else:
            return os.path.join('images', 'default_thumb.jpg')

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas."""
        return ', '.join([syn.name for syn in self.synonyms])

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas."""
        syns = synlist.split(', ')
        syns = [titlecase(syn) for syn in syns]
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents:
                        db.session.delete(synonym)
                        db.session.commit()
        for syn in syns:
            synonym = Seed.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                synonym = Seed()
                synonym.name = syn
                self.synonyms.append(synonym)


class Series(db.Model):
    """Table for seed series.

    A series is an optional subclass of a given seed type, usually created by
    the company that created the cultivars within the series. Examples include
    Benary's Giant (zinnias), Superfine Rainbow (coleus), and Heat Elite Mambo
    (petunias).

    Attributes:
        __tablename__ (str): Name of the table: 'series'
        id (int): Auto-incremented ID # for use as primary key.
        description (str): Column for description of a series.
        label (str): The name of the series.
    """
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    name = db.Column(db.String(64), unique=True)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='series')

    @property
    def fullname(self):
        """Return series name with common name."""
        fn = []
        if self.name:
            fn.append(self.name)
        if self.common_name:
            fn.append(self.common_name.name)
        if fn:
            return ' '.join(fn)
        else:
            return None


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

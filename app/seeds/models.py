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
from app import db, dbify


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
        else:
            return USDInt.usd_to_int(value)

    def process_result_value(self, value, dialect):
        if value is None:  # pragma: no cover
            return None
        else:
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

        Examples:
            >>> USDInt.int_to_usd(100)
            Decimal('1.00')

            >>> USDInt.int_to_usd(350)
            Decimal('3.50')

            >>> USDInt.int_to_usd(2999)
            Decimal('29.99')

        """
        if isinstance(amount, int):
            return (Decimal(amount) / 10**2).\
                quantize(Decimal('1.00'))
        else:
            raise TypeError('amount must be an integer!')

    @staticmethod
    def usd_to_int(amount):
        """Convert a dollar value to db int.

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

        Examples:

            >>> USDInt.usd_to_int(Decimal('1.99'))
            199

            >>> USDInt.usd_to_int(5)
            500

            >>> USDInt.usd_to_int('$2.99')
            299

            >>> USDInt.usd_to_int('2.5')
            250
        """
        if isinstance(amount, str):
            try:
                amt = Decimal(amount.replace('$', '').strip())
                return int(amt * 10**2)
            except:
                raise ValueError('Amount contains invalid '
                                 'characters or formatting!')
        elif isinstance(amount, Fraction):
            raise TypeError('Amount must be a decimal or integer!')
        else:
            try:
                return int(amount * 10**2)
            except:
                raise TypeError('amount is of a type that could'
                                ' not be converted to int!')

    @staticmethod
    def usd_to_decimal(val):
        """Convert a value representing USD to a Decimal.

        Args:
            val: Amount in US dollars to convert to a Decimal number.

        Returns:
            Decimal: US Dollar value as a Decimal number.

        Raises:
            ValueError: If val cannot be converted to a Decimal.

        Examples:
            >>> USDInt.usd_to_decimal(1)
            Decimal('1.00')

            >>> USDInt.usd_to_decimal('$3.50')
            Decimal('3.50')

            >>> USDInt.usd_to_decimal('2.99')
            Decimal('2.99')

            >>> USDInt.usd_to_decimal('4.5')
            Decimal('4.50')
        """
        if isinstance(val, float):
            # Decimal will use the exact value of floats instead of the value
            # a float represents (which is a rounded version of stored value)
            # so we must convert to str before converting to Decimal.
            val = str(val)
        if isinstance(val, str):
            val = val.replace('$', '').strip()
        try:
            return Decimal(val).quantize(Decimal('1.00'))
        except:
            raise ValueError('Value could not be converted to a decimal '
                             'number.')


class BotanicalName(db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. A correctly-formatted botanical name begins with a genus and species
    in binomial name format, or at least a genus followed by a descriptive
    comment.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        common_name_id (int): ForeignKey for common_name relationship.
        common_name (relationship): The common name this botanical name belongs
            to.
            botanical_names (backref): The botanical names that belong to the
                related common name.
        _name (str): A botanical name associated with one or more seeds. Get
            and set via the name property.
        syn_only (bool): Whether or not the botanical name exists only as a
            synonym.
        syn_parents (relationship): The botanical names that this botanical
            name is considered a synonym of.
            synonyms (backref): Synonyms of this botanical name.
    """
    __tablename__ = 'botanical_names'
    id = db.Column(db.Integer, primary_key=True)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='botanical_names')
    _name = db.Column(db.String(64), unique=True)
    syn_only = db.Column(db.Boolean, default=False)
    syn_parents = db.relationship(
        'BotanicalName',
        secondary=botanical_name_synonyms,
        backref='synonyms',
        primaryjoin=id == botanical_name_synonyms.c.syn_parents_id,
        secondaryjoin=id == botanical_name_synonyms.c.synonyms_id
    )

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
            self._name = name.strip()
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
            nomens = botanical_name.strip().split(' ')
            if nomens[0][0].isupper() and \
                    nomens[0][1:].islower() and \
                    nomens[1].islower():
                return True
            else:
                return False
        except:
            return False

    def clear_synonyms(self):
        """Remove all synonyms, deleting any that end up with no parent."""
        for synonym in list(self.synonyms):
            self.synonyms.remove(synonym)
            if not synonym.syn_parents and synonym.syn_only:
                db.session.delete(synonym)

    def list_syn_parents_as_string(self):
        """Return a string listing the parents of this if it is a synonym.

        Returns:
            str: A list of botanical names this botanical name is a synonym of
                delineated by commas, or a blank string if it is not a synonym.
        """
        if self.syn_parents:
            return ', '.join([sp.name for sp in self.syn_parents])
        else:
            return ''

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas.

        Returns:
            str: A list of synonyms of this botanical name, or a blank string
                if it has none.
        """
        if self.synonyms:
            return ', '.join([syn.name for syn in self.synonyms])
        else:
            return ''

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas.

        Args:
            synlist (str): A string containing a list of synonyms separated by
                commas.
        """
        syns = synlist.split(', ')
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents and synonym.syn_only:
                        db.session.delete(synonym)
        for syn in syns:
            synonym = BotanicalName.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                if syn and not syn.isspace():
                    synonym = BotanicalName()
                    synonym.name = syn
                    synonym.syn_only = True
                    self.synonyms.append(synonym)


class Category(db.Model):
    """Table for seed categories.

    Categories are the first/broadest divisions we use to sort seeds. The
    category a seed falls under is usually based on what type of plant it is
    (herb, vegetable) or its life cycle. (perennial flower, annual flower)

    Attributes:
        __tablename__ (str): Name of the table: 'categories'
        id (int): Auto-incremented ID # for use as primary key.
        description (str): HTML description information for the category.
        _name (str): The name for the category itself, such as 'Herb'
            or 'Perennial Flower'.
        seeds (relationship): Seeds that fall under this category.
            categories (backref): Categories belonging to a seed.
        slug (str): URL-friendly version of the category name.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    _name = db.Column(db.String(64), unique=True)
    seeds = db.relationship('Seed',
                            secondary=categories_to_seeds,
                            backref='categories')
    slug = db.Column(db.String(64), unique=True)

    def __init__(self, cat_name=None, description=None):
        """Construct an instance of Category.

        Args:
            cat_name (Optional[str]): A category name.
            description (Optional[str]): A description for this category.
                This should be in raw HTML to allow for special formatting.
        """
        self.name = cat_name
        self.description = description

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.name)

    @hybrid_property
    def name(self):
        """str: contents of ._name.

        Setter:
            Sets ._name, and sets .slug to a pluralized, slugified version
                of ._name.
        """
        return self._name

    @name.expression
    def name(cls):
        return cls._name

    @name.setter
    def name(self, cat_name):
        self._name = cat_name
        if cat_name is not None:
            self.slug = slugify(pluralize(cat_name))
        else:
            self.slug = None

    @property
    def header(self):
        """str: contents of ._category in a str for headers, titles, etc."""
        # TODO : Maybe make the string setable via config?
        return '{0} Seeds'.format(self._name)

    @property
    def plural(self):
        """str: plural form of ._category."""
        return pluralize(self._name)


class CommonName(db.Model):
    """Table for common names.

    A CommonName is the next subdivision below Category in how we sort seeds.
    It is usually the common name for the species or group of species a seed
    belongs to.

    Attributes:
        __tablename__ (str): Name of the table: 'seed_types'
        id (int): Auto-incremented ID # for use as primary_key.
        categories (relationship): The categories this common name falls under.
            common_names (backref): The common names associated with a
                category.
        description (str): An optional description for the species/group
            of species with the given common name.
        gw_common_names (relationship): Common names that grow well with this
            common name.
        instructions (str): Planting instructions for seeds with this common
            name.
        _name (str): The common name of a seed. Examples: Coleus, Tomato,
            Lettuce, Zinnia.
        parent_id (int): Foreign key for parent/children relationship.
        parent (relationship): A common name this is a subcategory of. For
            example, if this common name is 'Dwarf Coleus', it would have
            'Coleus' as its parent.
            children (backref): Common names that are subcategories of parent.
        slug (str): The URL-friendly version of this common name.
        syn_only (bool): Whether or not this common name only exists as a
            synonym of other common names.
        syn_parents (relationship): Common names this is a synonym of.
            synonyms (backref): Synonyms of this common name.
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    categories = db.relationship('Category',
                                 secondary=common_names_to_categories,
                                 backref='common_names')
    description = db.Column(db.Text)
    gw_common_names = db.relationship(
        'CommonName',
        secondary=cns_to_gw_cns,
        primaryjoin=id == cns_to_gw_cns.c.common_name_id,
        secondaryjoin=id == cns_to_gw_cns.c.gw_common_name_id
    )
    instructions = db.Column(db.Text)
    _name = db.Column(db.String(64), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    parent = db.relationship('CommonName',
                             backref='children',
                             foreign_keys=parent_id,
                             remote_side=[id])
    slug = db.Column(db.String(64), unique=True)
    syn_only = db.Column(db.Boolean, default=False)
    syn_parents = db.relationship(
        'CommonName',
        secondary=common_name_synonyms,
        backref='synonyms',
        primaryjoin=id == common_name_synonyms.c.syn_parents_id,
        secondaryjoin=id == common_name_synonyms.c.synonyms_id
    )

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

    def clear_synonyms(self):
        """Remove all synonyms, deleting any that end up with no parent."""
        for synonym in list(self.synonyms):
            self.synonyms.remove(synonym)
            if not synonym.syn_parents and synonym.syn_only:
                db.session.delete(synonym)

    def list_syn_parents_as_string(self):
        """Return a string listing the parents of this if it is a synonym.

        Returns:
            str: A list of common names this is a synonym of delineated by
                commas, or a blank string if it is not a synonym.
        """
        if self.syn_parents:
            return ', '.join([sp.name for sp in self.syn_parents])
        else:
            return ''

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas.

        Returns:
            str: A list of synonyms of this common name, or a blank string if
                it has none.
        """
        if self.synonyms:
            return ', '.join([syn.name for syn in self.synonyms])
        else:
            return ''

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas.

        Args:
            synlist (str): A string listing synonyms separated by commas.
        """
        if not synlist:
            self.synonyms = None
        syns = synlist.split(', ')
        syns = [dbify(syn) for syn in syns]
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents and synonym.syn_only:
                        db.session.delete(synonym)
                        db.session.commit()
        for syn in syns:
            synonym = CommonName.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                if syn and not syn.isspace():
                    synonym = CommonName()
                    synonym.name = syn
                    synonym.syn_only = True
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
    filename = db.Column(db.String(32), unique=True)
    seed_id = db.Column(db.Integer, db.ForeignKey('seeds.id', use_alter=True))

    def __init__(self, filename=None):
        self.filename = filename

    def __repr__(self):
        return '<{0} filename: \'{1}\'>'.format(self.__class__.__name__,
                                                self.filename)

    @property
    def full_path(self):
        """str: The full path to the file this image entry represents."""
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
        price (USDInt): Price (in US dollars) for this packet.
        quantity_id (int): ForeignKey for quantity relationship.
        quantity (relationship): Quantity (number and units) of seeds in this
            packet.
        seed_id (int): ForeignKey for relationship with seeds.
        sku (str): Product SKU for the packet.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(USDInt)
    quantity_id = db.Column(db.ForeignKey('quantities.id'))
    quantity = db.relationship('Quantity', backref='packets')
    seed_id = db.Column(db.Integer, db.ForeignKey('seeds.id'))
    sku = db.Column(db.String(32), unique=True)

    def __repr__(self):
        return '<{0} SKU #{1}>'.format(self.__class__.__name__, self.sku)

    @property
    def info(self):
        """str: A formatted string containing the data of this packet."""
        if self.quantity:
            qv = self.quantity.value
            qu = self.quantity.units
        else:
            qv = None
            qu = None
        return 'SKU #{0}: ${1} for {2} {3}'.format(self.sku,
                                                    self.price,
                                                    qv,
                                                    qu)


class Quantity(db.Model):
    """Table for quantities.

    Quantities contain a number and a unit of measure. Since numbers could be
    integer, decimal, or fraction, all quantities are stored as fractions
    and floats, where the floats are only used if the quantity is a decimal
    number, and for querying that needs comparison of sizes of quantity.

    Attributes:
        __tablename__ (str): The name of the table: 'quantities'
        id (int): Auto-incremented primary key ID number.
        _denominator (int): Denominator of fraction version of quantity.
        _float (float): Floating point value for decimal values and comparison.
        is_decimal (bool): Whether or not the stored quantity represents a
            decimal number, as opposed to fraction or int.
        _numerator (int): Numerator of fraction version of quantity.
        units (str): Unit of measurement of a quantity. (seeds, grams, etc.)
        __table_args__: Table-wide arguments, such as constraints.
    """
    __tablename__ = 'quantities'
    id = db.Column(db.Integer, primary_key=True)
    _denominator = db.Column(db.Integer)
    _float = db.Column(db.Float)
    is_decimal = db.Column(db.Boolean, default=False)
    _numerator = db.Column(db.Integer)
    units = db.Column(db.String(32))
    __table_args__ = (db.UniqueConstraint('_float',
                                          'units',
                                          name='_float_units_uc'),)

    def __init__(self, value=None, units=None):
        if value:
            self.value = value
        if units:
            self.units = units

    def __repr__(self):
        return '<{0} \'{1} {2}\'>'.format(self.__class__.__name__,
                                          self.value,
                                          self.units)

    @staticmethod
    def dec_check(val):
        """Check if a given value is a decimal number.

        Args:
            val: A value to check the (perfectly cromulent) decimalness of.

        Returns:
            True: If value appears to be a decimal number.
            False: If value can't be determined to be a decimal number.

        Examples:
            >>> Quantity.dec_check(3.14)
            True

            >>> Quantity.dec_check(42)
            False

            >>> Quantity.dec_check('3.50')
            True

            >>> Quantity.dec_check('tree fiddy')
            False

            >>> Quantity.dec_check('8675309')
            False

            >>> Quantity.dec_check(Decimal('1.99'))
            True

            >>> Quantity.dec_check(Fraction(3, 4))
            False

            >>> Quantity.dec_check('127.0.0.1')
            False
        """
        if isinstance(val, Decimal) or isinstance(val, float):
            return True
        if isinstance(val, Fraction):
            return False
        try:
            float(val)
            try:
                int(val)
                return False
            except:
                return True
        except:
            return False

    @staticmethod
    def fraction_to_str(val):
        """Convert a Fraction to a string containing a mixed number.

        Args:
            val (Fraction): A fraction to convert to a string fraction or
                mixed number.

        Returns:
            str: A string containing a fraction or mixed number.

        Raises:
            TypeError: If given a non-Fraction value.

        Examples:
            >>> Quantity.fraction_to_str(Fraction(1, 2))
            '1/2'

            >>> Quantity.fraction_to_str(Fraction(11, 4))
            '2 3/4'

            >>> Quantity.fraction_to_str(Fraction(123, 11))
            '11 2/11'
        """
        if isinstance(val, Fraction):
            if val.numerator > val.denominator:
                whole = val.numerator // val.denominator
                part = Fraction(val.numerator % val.denominator,
                                val.denominator)
                return '{0} {1}'.format(whole, part)
            else:
                return str(val)
        else:
            raise TypeError('val must be of type Fraction')

    @staticmethod
    def for_cmp(val):
        """Convert a value into appropriate type for use in comparisons.

        Args:
            val: Value to convert to a similar format to how they're stored to
                make querying more reliable.

        Returns:
            float: If value is a decimal number.
            int: If value is an integer.
            Fraction: If value is a fraction.
        """
        if Quantity.dec_check(val):
            return float(val)
        elif isinstance(val, str):
            frac = Quantity.str_to_fraction(val)
        else:
            frac = Fraction(val)
        if frac.denominator == 1:
            return int(frac)
        else:
            return frac

    @staticmethod
    def str_to_fraction(val):
        """Convert a string containing a number into a fraction.

        Args:
            val (str): String containing a fraction or mixed number to convert
                to a Fraction.

        Returns:
            Fraction: Fraction of given value.

        Raises:
            TypeError: If val is not a string.
            ValueError: If val could not be converted to Fraction.

        Examples:
            >>> Quantity.str_to_fraction('5')
            Fraction(5, 1)

            >>> Quantity.str_to_fraction('3/4')
            Fraction(3, 4)

            >>> Quantity.str_to_fraction('11 2/11')
            Fraction(123, 11)

            >>> Quantity.str_to_fraction('1.1')
            Fraction(11, 10)
        """
        if isinstance(val, str):
            val = val.strip()
            try:
                return Fraction(val)
            except:
                if ' ' in val:
                    parts = val.split(' ')
                    if len(parts) == 2 and '/' in parts[1]:
                        try:
                            whole = int(parts[0])
                            frac = Fraction(parts[1])
                            return frac + whole
                        except:
                            pass
            raise ValueError('val could not be converted to Fraction')
        else:
            raise TypeError('val must be a str')

    @property
    def html_value(self):
        """str: A representation of a fraction in HTML."""
        if isinstance(self.value, Fraction):
            if self.value == Fraction(1, 4):
                return '&frac14;'
            elif self.value == Fraction(1, 2):
                return '&frac12;'
            elif self.value == Fraction(3, 4):
                return '&frac34;'
            elif self.value == Fraction(1, 3):
                return '&#8531;'
            elif self.value == Fraction(2, 3):
                return '&#8532;'
            elif self.value == Fraction(1, 5):
                return '&#8533;'
            elif self.value == Fraction(2, 5):
                return '&#8534;'
            elif self.value == Fraction(3, 5):
                return '&#8535;'
            elif self.value == Fraction(4, 5):
                return '&#8536;'
            elif self.value == Fraction(1, 6):
                return '&#8537;'
            elif self.value == Fraction(5, 6):
                return '&#8537;'
            elif self.value == Fraction(1, 8):
                return '&#8539;'
            elif self.value == Fraction(3, 8):
                return '&#8540;'
            elif self.value == Fraction(5, 8):
                return '&#8541;'
            elif self.value == Fraction(7, 8):
                return '&#8542;'
            else:
                return '<span class="fraction"><sup>{0}</sup>&frasl;'\
                    '<sub>{1}</sub></span>'.format(self._numerator,
                                                   self._denominator)
        return self.value

    @hybrid_property
    def value(self):
        """"int, float, Fraction: The value of a quantity in the same format
                it was entered.

            Setter:
                Convert value a Fraction, store its numerator and denominator,
                and store a floating point version to allow querying based on
                quantity value. Flag is_decimal if the initial value is a
                decimal (floating point) number.
        """
        if self._float is not None:
            if self.is_decimal:
                return self._float
            elif self._denominator == 1:
                return self._numerator
            else:
                return Fraction(self._numerator, self._denominator)
        else:
            return None

    @value.expression
    def value(cls):
        return cls._float

    @value.setter
    def value(self, val):
        if val is not None:
            if Quantity.dec_check(val):
                self.is_decimal = True
                self._float = float(val)
                self._numerator = None
                self._denominator = None
            else:
                if isinstance(val, str):
                    frac = Quantity.str_to_fraction(val)
                else:
                    frac = Fraction(val)
                self._numerator = frac.numerator
                self._denominator = frac.denominator
                self._float = float(frac)
        else:
            self._numerator = None
            self._denominator = None
            self._float = None


class Seed(db.Model):
    """Table for seed data.

    This table contains the primary identifying information for a seed
    we sell. Generally, this is the table called to get and display seed
    data on the website.

    Attributes:
        __tablename__ (str): Name of the table: 'seeds'
        id (int): Auto-incremented ID # for use as primary key.
        botanical_name_id (int): ForeignKey for botanical_name relationship.
        botanical_name (relationship): Botanical name for this seed.
        common_name_id (int): ForeignKey for common_name relationship.
        common_name (relationship): Common name this seed belongs to.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
            if it will be discontinued when low.
        gw_common_names (relationship): Common names this seed grows well with.
            gw_seeds (backref): Seeds that grow well with a common name.
        gw_seeds (relationship): Other seeds this one grows well with.
        images (relationship): Images associated with this seed.
        in_stock (bool): True if a seed is in stock, False if not.
        _name (str): The name of the seed (cultivar); the main product name.
        packets (relationship): Packets for sale of this seed.
        series_id (int): ForeignKey for series relationship.
        series (relationship): Series this seed belongs to.
            seeds (backref): Seeds in given series.
        slug (str): A URL-friendly version of _name.
        syn_only (bool): Whether or not this seed only exists as a synonym.
        syn_parents (relationship): Seeds that have this one as a synonym.
            synonyms (backref): Synonyms of this seed.
        thumbnail_id (int): ForeignKey of Image, used with thumbnail.
        thumbnail (relationship): MtO relationship with Image for specifying
            a thumbnail for seed.
        __table_args__: Table-wide arguments, such as constraints.
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
    gw_seeds = db.relationship(
        'Seed',
        secondary=seeds_to_gw_seeds,
        primaryjoin=id == seeds_to_gw_seeds.c.seed_id,
        secondaryjoin=id == seeds_to_gw_seeds.c.gw_seed_id
    )
    images = db.relationship('Image', foreign_keys=Image.seed_id)
    in_stock = db.Column(db.Boolean)
    _name = db.Column(db.String(64))
    packets = db.relationship('Packet',
                              cascade='all, delete-orphan',
                              backref='seed')
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'))
    series = db.relationship('Series', backref='seeds')
    slug = db.Column(db.String(64))
    syn_only = db.Column(db.Boolean, default=False)
    syn_parents = db.relationship(
        'Seed',
        secondary=seed_synonyms,
        backref='synonyms',
        primaryjoin=id == seed_synonyms.c.syn_parents_id,
        secondaryjoin=id == seed_synonyms.c.synonyms_id
    )
    thumbnail_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    thumbnail = db.relationship('Image', foreign_keys=thumbnail_id)
    __table_args__ = (db.UniqueConstraint('_name',
                                          'common_name_id',
                                          name='_name_common_name_uc'),)

    def __repr__(self):
        """Return representation of Seed in human-readable format."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.name)

    @hybrid_property
    def fullname(self):
        """str: Full name of seed including common name and series."""
        fn = []
        if self.series:
            fn.append(self.series.name)
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
        """str: contents _name.

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
        """str: The path to this seed's thumbnail file.

        Returns:
            str: Local path to thumbnail if it exists, path to default thumb
                image if it does not.
        """
        if self.thumbnail:
            return os.path.join('images',
                                self.thumbnail.filename)
        else:
            return os.path.join('images', 'default_thumb.jpg')

    def clear_synonyms(self):
        """Remove all synonyms, deleting any that end up with no parent."""
        for synonym in list(self.synonyms):
            self.synonyms.remove(synonym)
            if not synonym.syn_parents and synonym.syn_only:
                db.session.delete(synonym)

    def list_syn_parents_as_string(self):
        """Return a string listing the parents of this if it is a synonym.

        Returns:
            str: A list of seeds this is a synonym of delineated by commas, or
                a blank string if it is not a synonym.
        """
        if self.syn_parents:
            return ', '.join([sp.name for sp in self.syn_parents])
        else:
            return ''

    def list_synonyms_as_string(self):
        """Return a string listing of synonyms delineated by commas.

        Returns:
            str: A list of synonyms of this seed separated by commas, or a
            blank string if it has none.
        """
        if self.synonyms:
            return ', '.join([syn.name for syn in self.synonyms])
        else:
            return ''

    def set_synonyms_from_string_list(self, synlist):
        """Set synonyms with data from a string list delineated by commas.

        Args:
            synlist (str): A string listing synonyms separated by commas.
        """
        syns = synlist.split(', ')
        syns = [dbify(syn) for syn in syns]
        if self.synonyms:
            for synonym in list(self.synonyms):
                if synonym.name not in syns:
                    self.synonyms.remove(synonym)
                    if not synonym.syn_parents and synonym.syn_only:
                        db.session.delete(synonym)
                        db.session.commit()
        for syn in syns:
            synonym = Seed.query.filter_by(_name=syn).first()
            if synonym:
                if synonym not in self.synonyms:
                    self.synonyms.append(synonym)
            else:
                if syn and not syn.isspace():
                    synonym = Seed()
                    synonym.name = syn
                    synonym.syn_only = True
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
        common_name_id (int): ForeignKey for common_name relationship.
        common_name (relationship): The common name a series belongs to.
        description (str): Column for description of a series.
        name (str): The name of the series.
    """
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='series')
    description = db.Column(db.Text)
    name = db.Column(db.String(64), unique=True)

    @property
    def fullname(self):
        """str: Series name + common name"""
        fn = []
        if self.name:
            fn.append(self.name)
        if self.common_name:
            fn.append(self.common_name.name)
        if fn:
            return ' '.join(fn)
        else:
            return None


if __name__ == '__main__':  # pragma: no cover
    import doctest
    doctest.testmod()

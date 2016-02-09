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
import os
from decimal import Decimal, ROUND_DOWN
from flask import current_app
from fractions import Fraction
from inflection import pluralize
from slugify import slugify
from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import hybrid_property
from app import db, dbify


botanical_names_to_common_names = db.Table(
    'botanical_names_to_common_names',
    db.Model.metadata,
    db.Column('botanical_names_id',
              db.Integer,
              db.ForeignKey('botanical_names.id')),
    db.Column('common_names_id', db.Integer, db.ForeignKey('common_names.id'))
)


cns_to_gw_cns = db.Table(
    'cns_to_gw_cns',
    db.Model.metadata,
    db.Column('common_name_id', db.Integer, db.ForeignKey('common_names.id')),
    db.Column('gw_common_name_id',
              db.Integer,
              db.ForeignKey('common_names.id'))
)


gw_common_names_to_gw_cultivars = db.Table(
    'gw_common_names_to_gw_cultivars',
    db.Model.metadata,
    db.Column('common_names_id', db.Integer, db.ForeignKey('common_names.id')),
    db.Column('cultivars_id', db.Integer, db.ForeignKey('cultivars.id'))
)


cultivars_to_gw_cultivars = db.Table(
    'cultivars_to_gw_cultivars',
    db.Model.metadata,
    db.Column('cultivar_id', db.Integer, db.ForeignKey('cultivars.id')),
    db.Column('gw_cultivar_id', db.Integer, db.ForeignKey('cultivars.id'))
)


cultivars_to_custom_pages = db.Table(
    'cultivars_to_custom_pages',
    db.Model.metadata,
    db.Column('cultivar_id', db.Integer, db.ForeignKey('cultivars.id')),
    db.Column('custom_pages_id', db.Integer, db.ForeignKey('custom_pages.id'))
)


def indexes_to_json(indexes):
    """Return a list of tuples containing index headers and slugs.

    This way we can dump needed index information into a JSON file so we don't
    have to query the database every time we load a page with the nav bar on
    it.
    """
    return json.dumps({idx.id: (idx.header, idx.slug) for idx in indexes})


def save_indexes_to_json():
    """Save all indexes to indexes.json"""
    with open(current_app.config.get('INDEXES_JSON_FILE'),
              'w',
              encoding='utf-8') as ofile:
        ofile.write(indexes_to_json(Index.query.all()))


class SynonymsMixin(object):
    """A mixin class containing methods that operate on synonyms."""
    def get_synonyms_string(self):
        """Return a comma separated list """
        if self.synonyms:
            return ', '.join([syn.name for syn in self.synonyms])
        else:
            return ''

    def set_synonyms_string(self, synonyms, dbify_syns=True):
        db_changed = False
        if not synonyms:
            for syn in list(self.synonyms):
                if inspect(syn).persistent:
                    db_changed = True
                    db.session.delete(syn)
                else:
                    self.synonyms.remove(syn)
        else:
            syns = [dbify(syn) if dbify_syns else syn
                    for syn in synonyms.split(', ')]
            for syn in list(self.synonyms):
                if syn.name not in syns:
                    if inspect(syn).persistent:
                        db_changed = True
                        db.session.delete(syn)
                    else:
                        self.synonyms.remove(syn)
            for syn in syns:
                if syn.isspace():
                    syn = None
                if syn and syn not in [syno.name for syno in self.synonyms]:
                    db_changed = True
                    self.synonyms.append(Synonym(name=syn))
            if db_changed:
                db.session.commit()


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
            return Decimal(val).quantize(Decimal('1.00'), rounding=ROUND_DOWN)
        except:
            raise ValueError('Value could not be converted to a decimal '
                             'number.')


class Index(db.Model):
    """Table for seed indexes.

    Indexes are the first/broadest divisions we use to sort seeds. The
    index a seed falls under is usually based on what type of plant it is
    (herb, vegetable) or its life cycle. (perennial flower, annual flower)

    Attributes:
        __tablename__ (str): Name of the table: 'indexes'
        id (int): Auto-incremented ID # for use as primary key.
        description (str): HTML description information for the index.
        _name (str): The name for the index itself, such as 'Herb'
            or 'Perennial Flower'.
        slug (str): URL-friendly version of the index name.
    """
    __tablename__ = 'indexes'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    _name = db.Column(db.String(64), unique=True)
    slug = db.Column(db.String(64), unique=True)

    def __init__(self, name=None, description=None):
        """Construct an instance of Index.

        Args:
            name (Optional[str]): A index name.
            description (Optional[str]): A description for this index.
                This should be in raw HTML to allow for special formatting.
        """
        self.name = name
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
    def name(self, idx_name):
        self._name = idx_name
        if idx_name is not None:
            self.slug = slugify(pluralize(idx_name))
        else:
            self.slug = None

    @property
    def header(self):
        """str: contents of ._index in a str for headers, titles, etc."""
        # TODO : Maybe make the string setable via config?
        return '{0} Seeds'.format(self._name)

    @property
    def plural(self):
        """str: plural form of ._index."""
        return pluralize(self._name)


class CommonName(SynonymsMixin, db.Model):
    """Table for common names.

    A CommonName is the next subdivision below Index in how we sort seeds.
    It is usually the common name for the species or group of species a seed
    belongs to.

    Attributes:
        __tablename__ (str): Name of the table: 'common_names'
        id (int): Auto-incremented ID # for use as primary_key.
        index (relationship): The index this common name falls under.
            common_names (backref): The common names associated with a
                index.
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
            children (backref): Common names that are subindexes of parent.
        slug (str): The URL-friendly version of this common name.
        invisible (bool): Whether or not to list this common name in
            automatically generated pages.
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    index_id = db.Column(db.Integer, db.ForeignKey('indexes.id'))
    index = db.relationship('Index', backref='common_names')
    description = db.Column(db.Text)
    gw_common_names = db.relationship(
        'CommonName',
        secondary=cns_to_gw_cns,
        primaryjoin=id == cns_to_gw_cns.c.common_name_id,
        secondaryjoin=id == cns_to_gw_cns.c.gw_common_name_id
    )
    instructions = db.Column(db.Text)
    _name = db.Column(db.String(64))
    parent_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    parent = db.relationship('CommonName',
                             backref='children',
                             foreign_keys=parent_id,
                             remote_side=[id])
    slug = db.Column(db.String(64))
    invisible = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('_name',
                                          'index_id',
                                          name='cn_index_uc'),)

    def __init__(self, name=None, description=None, instructions=None):
        """Construct an instance of CommonName

        Args:
            name (Optional[str]): The common name for a seed or group of seeds.
            description (Optional[str]): An optional description for use on
                pages listing seeds of a given common name.
            instructions(Optional[str]): Optional planting instructions.
        """
        self.name = name
        self.description = description
        self.instructions = instructions

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

    def lookup_dict(self):
        """Return a dictionary with name and index for easy DB lookup."""
        return {
            'Common Name': self._name if self._name else None,
            'Index': self.index.name if self.index else None}

    @classmethod
    def from_lookup_dict(cls, lookup):
        name = lookup['Common Name']
        index = lookup['Index']
        if not name:
            raise ValueError('Cannot look up CommonName without a name!')
        if index:
            return cls.query\
                .join(Index, Index.id == CommonName.index_id)\
                .filter(CommonName._name == name,
                        Index.name == index).one_or_none()
        else:
            return cls.query\
                .filter(CommonName._name == name,
                        CommonName.index == None).one_or_none()  # noqa


class BotanicalName(SynonymsMixin, db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. A correctly-formatted botanical name begins with a genus and species
    in binomial name format, or at least a genus followed by a descriptive
    comment.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        common_names (relationship): The common names this botanical name
            belongs to.
            botanical_names (backref): The botanical names that belong to the
                related common name.
        _name (str): A botanical name associated with one or more seeds. Get
            and set via the name property.
        invisible (bool): Whether or not the botanical name exists only as a
            synonym.
    """
    __tablename__ = 'botanical_names'
    id = db.Column(db.Integer, primary_key=True)
    common_names = db.relationship(
        'CommonName',
        secondary=botanical_names_to_common_names,
        backref='botanical_names'
    )
    _name = db.Column(db.String(64), unique=True)
    invisible = db.Column(db.Boolean, default=False)

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

    def set_synonyms_string(self, synonyms, dbify_syns=False):
        """Validate synonyms as botanical names before adding them.

        Note that dbify_syns is set to False by default here, as we don't
        want to titlecase botanical names.
        """
        if synonyms:
            bad_syns = []
            for syn in synonyms.split(', '):
                if not BotanicalName.validate(syn.strip()):
                    bad_syns.append(syn)
            if bad_syns:
                raise ValueError('One or more synonyms do not appear to be '
                                 'valid botanical names: {0}'
                                 .format(', '.join(bad_syns)))
        super().set_synonyms_string(synonyms, dbify_syns)


class Image(db.Model):
    """Table for image information.

    Any image uploaded to be used with the cultivar model should utilize this
    table for important image data like filename and location.
    __tablename__ (str): Name of the table: 'images'
    id (int): Auto-incremended ID # for use as primary key.
    filename (str): File name of an image.
    cultivar_id (int): Foreign key from Cultivar to allow Cultivar to have a
        OtM relationship with Image.
    """
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(32), unique=True)
    cultivar_id = db.Column(db.Integer,
                            db.ForeignKey('cultivars.id', use_alter=True))

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


class Series(db.Model):
    """Table for seed series.

    A series is an optional subclass of a given cultivar type, usually created
    by the company that created the cultivars within the series. Examples
    include Benary's Giant (zinnias), Superfine Rainbow (coleus), and Heat
    Elite Mambo (petunias).

    Attributes:
        __tablename__ (str): Name of the table: 'series'
        id (int): Auto-incremented ID # for use as primary key.
        common_name_id (int): ForeignKey for common_name relationship.
        common_name (relationship): The common name a series belongs to.
        description (str): Column for description of a series.
        name (str): The name of the series.
        position (int): Int for a constant representing where to put series
            name in relation to cultivar name.
    """
    __tablename__ = 'series'
    id = db.Column(db.Integer, primary_key=True)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='series')
    description = db.Column(db.Text)
    name = db.Column(db.String(64))
    position = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('name',
                                          'common_name_id',
                                          name='_series_name_cn_uc'),)

    BEFORE_CULTIVAR = 0
    AFTER_CULTIVAR = 1

    def __repr__(self):
        """Return a string representing a Series instance."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)

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


class Cultivar(SynonymsMixin, db.Model):
    """Table for cultivar data.

    This table contains the primary identifying information for a cultivar of
    seed we sell. Generally, this is the table called to get and display
    cultivar data on the website.

    Attributes:
        __tablename__ (str): Name of the table: 'cultivars'
        id (int): Auto-incremented ID # for use as primary key.
        botanical_name_id (int): ForeignKey for botanical_name relationship.
        botanical_name (relationship): Botanical name for this cultivar.
        common_name_id (int): ForeignKey for common_name relationship.
        common_name (relationship): Common name this cultivar belongs to.
        description (str): Product description in HTML format.
        active (bool): True if the cultivar will be re-stocked when low,
            False if it will be discontinued when low.
        gw_common_names (relationship): Common names this cultivar grows well
            with. gw_cultivars (backref): Cultivars that grow well with a
            common name.
        gw_cultivars (relationship): Other cultivars this one grows well with.
        images (relationship): Images associated with this cultivar.
        in_stock (bool): True if a cultivar is in stock, False if not.
        _name (str): The name of the cultivar; the main product name.
        packets (relationship): Packets for sale of this cultivar.
        series_id (int): ForeignKey for series relationship.
        series (relationship): Series this cultivar belongs to.
            cultivars (backref): Cultivars in given series.
        slug (str): A URL-friendly version of _name.
        invisible (bool): Whether or not this cultivar should be listed in
            automatically generated pages. Cultivars set to invisible can still
            be listed on custom pages.
        thumbnail_id (int): ForeignKey of Image, used with thumbnail.
        thumbnail (relationship): MtO relationship with Image for specifying
            a thumbnail for cultivar.
        new_for (int): Year a cultivar is new for.
        __table_args__: Table-wide arguments, such as constraints.
    """
    __tablename__ = 'cultivars'
    id = db.Column(db.Integer, primary_key=True)
    botanical_name_id = db.Column(db.Integer,
                                  db.ForeignKey('botanical_names.id'))
    botanical_name = db.relationship('BotanicalName',
                                     backref='cultivars')
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='cultivars')
    description = db.Column(db.Text)
    active = db.Column(db.Boolean)
    gw_common_names = db.relationship(
        'CommonName',
        secondary=gw_common_names_to_gw_cultivars,
        backref='gw_cultivars'
    )
    gw_cultivars = db.relationship(
        'Cultivar',
        secondary=cultivars_to_gw_cultivars,
        primaryjoin=id == cultivars_to_gw_cultivars.c.cultivar_id,
        secondaryjoin=id == cultivars_to_gw_cultivars.c.gw_cultivar_id
    )
    images = db.relationship('Image', foreign_keys=Image.cultivar_id)
    in_stock = db.Column(db.Boolean)
    _name = db.Column(db.String(64))
    packets = db.relationship('Packet',
                              cascade='all, delete-orphan',
                              backref='cultivar')
    series_id = db.Column(db.Integer, db.ForeignKey('series.id'))
    series = db.relationship('Series', backref='cultivars')
    slug = db.Column(db.String(64))
    invisible = db.Column(db.Boolean, default=False)
    thumbnail_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    thumbnail = db.relationship('Image', foreign_keys=thumbnail_id)
    new_for = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('_name',
                                          'common_name_id',
                                          'series_id',
                                          name='_cultivar_name_cn_series_uc'),)

    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description

    def __repr__(self):
        """Return representation of Cultivar in human-readable format."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.fullname)

    @hybrid_property
    def index(self):
        """Index belonging to this cultivar's common name."""
        return self.common_name.index

    @hybrid_property
    def fullname(self):
        """str: Full name of cultivar including common name and series."""
        fn = []
        if self.name_with_series:
            fn.append(self.name_with_series)
        if self.common_name and self.common_name.name != self.name:
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
        self.set_slug()

    @hybrid_property
    def name_with_series(self):
        """str: contents of _name with series.name included in its position."""
        if self.series:
            if self.series.position != Series.AFTER_CULTIVAR or\
                    'Mix' in self.name:
                return '{0} {1}'.format(self.series.name, self._name)
            else:
                return '{0} {1}'.format(self._name, self.series.name)
        else:
            return self._name

    @hybrid_property
    def thumbnail_path(self):
        """str: The path to this cultivar's thumbnail file.

        Returns:
            str: Local path to thumbnail if it exists, path to default thumb
                image if it does not.
        """
        if self.thumbnail:
            return os.path.join('images',
                                self.thumbnail.filename)
        else:
            return os.path.join('images', 'default_thumb.jpg')

    def lookup_dict(self):
        """Return a dict of name, series, common_name, and index.

        Since a Cultivar needs to be a unique combination of name, series, and
        common_name (which requires an Index) the only way to look it up is via
        some combination of cultivar name, series name, commo nname, and index
        name.

        Returns:
            dict: A dict containing Cultivar.name, Cultivar.series.name, and
            Cultivar.common_name.name, substituting None where not present.
        """
        return {
            'Cultivar Name': None if not self.name else self.name,
            'Series': None if not self.series else self.series.name,
            'Common Name': None if not self.common_name else
            self.common_name.name,
            'Index': None if not self.common_name or not self.common_name.index
            else self.common_name.index.name
        }

    @classmethod
    def from_lookup_dict(cls, lookup):
        """Load a Cultivar from db based on lookup dict.

        Args:
            lookup (dict): A dictionary with values to use in querying for
                a cultivar.
        """
        name = lookup['Cultivar Name']
        series = lookup['Series']
        common_name = lookup['Common Name']
        index = lookup['Index']
        return Cultivar.lookup(name, series, common_name, index)

    @classmethod
    def lookup(cls, name, series=None, common_name=None, index=None):
        """Query a Cultivar based on its name, series, and common name.

        Since cultivars don't necessarily need a series or common name (though
        they should in theory always have a common name) we need to be able to
        query for cultivars that may not have a series or common name. This
        method allows querying based on any combination of the necessary
        parameters.

        Args:
            name (str): Name of the cultivar to query.
            series (optional[str]): Name of the series, if applicable, that
                the cultivar belongs to.
            common_name (str): The common name the cultivar belongs to.
            index (str): The index the common name (and thusly cultivar)
                belongs to.
        """
        if common_name and not index:
            raise ValueError('Common name cannot be used without an index!')
        if series and common_name:
            obj = cls.query.join(CommonName,
                                 CommonName.id == Cultivar.common_name_id)\
                .join(Series, Series.id == Cultivar.series_id)\
                .join(Index, Index.id == CommonName.index_id)\
                .filter(Cultivar.name == name,
                        CommonName.name == common_name,
                        Series.name == series).one_or_none()
        elif common_name and not series:
            obj = cls.query.join(CommonName,
                                 CommonName.id == Cultivar.common_name_id)\
                .join(Index, Index.id == CommonName.index_id)\
                .filter(Cultivar.series == None,  # noqa
                        Cultivar.name == name,
                        CommonName.name == common_name,
                        Index.name == index).one_or_none()
        else:
            obj = cls.query.filter(
                Cultivar.name == name,
                Cultivar.series == None,  # noqa
                Cultivar.common_name == None  # noqa
            ).one_or_none()
        return obj

    def set_slug(self):
        """Sets self.slug to a slug made from name and series."""
        if self._name:
            self.slug = slugify(self.name_with_series)
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
        price (USDInt): Price (in US dollars) for this packet.
        quantity_id (int): ForeignKey for quantity relationship.
        quantity (relationship): Quantity (number and units) of seeds in this
            packet.
        cultivar_id (int): ForeignKey for relationship with cultivars.
        sku (str): Product SKU for the packet.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(USDInt)
    quantity_id = db.Column(db.Integer, db.ForeignKey('quantities.id'))
    quantity = db.relationship('Quantity', backref='packets')
    cultivar_id = db.Column(db.Integer, db.ForeignKey('cultivars.id'))
    sku = db.Column(db.String(32), unique=True)

    def __repr__(self):
        return '<{0} SKU #{1}>'.format(self.__class__.__name__, self.sku)

    def __init__(self, sku=None, price=None, quantity=None, units=None):
        self.sku = sku
        self.price = price
        if quantity and units:
            self.quantity = Quantity.query.filter(
                Quantity.value == quantity,
                Quantity.units == units
            ).one_or_none()
            if not self.quantity:
                self.quantity = Quantity(value=quantity, units=units)
        elif quantity or units:
            raise ValueError('Cannot set quantity without both quantity and '
                             'units.')

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
        """Convert a value into appropriate float for querying.

        Args:
            val: Value to convert to a float.

        Returns:
            float: If value is a decimal number.
        """
        if Quantity.dec_check(val):
            return float(val)
        elif isinstance(val, str):
            frac = Quantity.str_to_fraction(val)
        else:
            frac = Fraction(val)
        return float(frac)

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
            raise ValueError('value {0} of type {1} could not be converted to '
                             'Fraction'.format(val, type(val)))
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
                return '&#8538;'
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
        return str(self.value)

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
                self.is_decimal = False
                if isinstance(val, str):
                    frac = Quantity.str_to_fraction(val)
                else:
                    frac = Fraction(val)
                self._numerator = frac.numerator
                self._denominator = frac.denominator
                self._float = float(frac)
        else:
            self.is_decimal = None
            self._numerator = None
            self._denominator = None
            self._float = None

    @property
    def str_value(self):
        if isinstance(self.value, Fraction):
            return self.fraction_to_str(self.value)
        else:
            return str(self.value)


class Synonym(db.Model):
    """Table for synonyms of other objects."""
    __tablename__ = 'synonyms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))
    common_name = db.relationship('CommonName', backref='synonyms')
    botanical_name_id = db.Column(db.Integer,
                                  db.ForeignKey('botanical_names.id'))
    botanical_name = db.relationship('BotanicalName', backref='synonyms')
    cultivar_id = db.Column(db.Integer, db.ForeignKey('cultivars.id'))
    cultivar = db.relationship('Cultivar', backref='synonyms')

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        """Return string representing a synonym."""
        if self.parent:
            return('<{0} \'{1}\' of {2}: \'{3}\'>'
                   .format(self.__class__.__name__,
                           self.name,
                           None if not self.parent else
                           self.parent.__class__.__name__,
                           None if not self.parent else self.parent.name))
        else:
            return('<{0} \'{1}\'>'.format(self.__class__.__name__, self.name))

    @property
    def parent(self):
        """Returns whatever foreign row this synonym belongs to."""
        parents = []
        if self.common_name:
            parents.append(self.common_name)
        if self.botanical_name:
            parents.append(self.botanical_name)
        if self.cultivar:
            parents.append(self.cultivar)
        if len(parents) == 0:
            return None
        if len(parents) == 1:
            return parents.pop()
        else:
            raise ValueError(
                'Each synonym should only be linked to one other table, but '
                'this one is linked to: {0}'
                .format(', '.join([obj.__repr__() for obj in parents]))
            )


class CustomPage(db.Model):
    """Table for custom pages that cover edge cases.

    Since there will always be some edge cases in which we may want to create
    pages that can't easily be automatically generated (for example, a page
    that lists cultivars from multiple common names) this table allows for
    generic pages to be made.

    Attributes:
        __tablename__ (str): Name of the table: 'custom_pages'
        id (int): Auto-incremented ID # as primary key.
        title (str): Page title to be used in <title> and for lookups.
        content (str): The HTML content of the page, including parseable
            tokens.
        cultivars (relationship): Relationship to link cultivars to custom
            pages.
            backref: custom_pages
    """
    __tablename__ = 'custom_pages'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)
    content = db.Column(db.Text)
    cultivars = db.relationship('Cultivar',
                                secondary=cultivars_to_custom_pages,
                                backref='custom_pages')


if __name__ == '__main__':  # pragma: no cover
    import doctest
    doctest.testmod()

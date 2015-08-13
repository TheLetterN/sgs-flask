from app import db


class BotanicalName(db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. Examples include *Asclepias incarnata* (swamp milkweed) and
    *Echinacea purpurea*.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        _botanical_name (str): A botanical name associated with one or more
                              seeds.
    """
    __tablename__ = 'botanical_names'
    id = db.Column(db.Integer, primary_key=True)
    _botanical_name = db.Column(db.String(64), unique=True)

    def __init__(self, botanical_name=None):
        """__init__ for BotanicalName.

        Args:
            botanical_name (str): A botanical name for a species
                                  of plant.
        """
        if botanical_name is not None:
            self.botanical_name = botanical_name

    @property
    def botanical_name(self):
        """Get _botanical_name as-is."""
        return self._botanical_name

    @botanical_name.setter
    def botanical_name(self, botanical_name):
        """Set _botanical_name if botanical_name is valid."""
        if self.validate(botanical_name):
            self._botanical_name = botanical_name
        else:
            raise ValueError('botanical_name must be a valid binomen!')

    @staticmethod
    def validate(botanical_name):
        """Return true if botanical_name is a validly formatted binomen.

        Valid within reason; some may contain more than 2 words, so we only
        check the first two words.

        Args:
            botanical_name (str): A string containing a botanical name to
                                  check for valid formatting."""
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

    Categories are the next subdivision below the all-encompasing "seeds"
    label. The category a seed falls under is usually based on what type of
    plant it is (herb, vegetable) or its life cycle. (perennial flower, annual
    flower)

    Attributes:
        __tablename__ (str): Name of the table: 'categories'
        id (int): Auto-incremented ID # for use as primary key.
        category (str): The name of the category.
        description(str): HTML description information for the category.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(64), unique=True)
    description = db.Column(db.Text)

    def __init__(self, category, description=None):
        """__init__ for Category.

        Args:
            category (str): A category name.
            description (Optional[str]): A description for this category.
                                         Should be set at some point, but is
                                         not needed during creation of a
                                         category.
        """
        self.category = category
        self.description = description


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
        quantity (str): Amount of seeds in packet.

    Relationships:
        unit_type (UnitType): MtO - Each Packet entry needs a unit type so
                              we know what units the quantity is in.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    _price = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    unit_type_id = db.Column(db.Integer, db.ForeignKey('unit_types.id'))
    _unit_type = db.relationship('UnitType', backref='packets')

    @property
    def price(self):
        """Get price converted from int to a string decimal value.

        Returns:
            str: a string containing a decimal number derived from
                 Packet.price
        """
        return self.price_str_from_int(self._price)

    @price.setter
    def price(self, price):
        """Set price as an int from a string representing a decimal value.

        Args:
            price (str): A string containing a decimal version of price.
        """
        self._price = self.price_int_from_str(price)

    @staticmethod
    def price_int_from_str(price):
        """Convert a string price to an integer.

        The lowest two digits of the integer represent the fractional part.
        Therefore, 10.25 = 1025, 1.5 = 150, 12 = 1200, etc.

        Due to potential issues with converting to and from float, price
        data should only accepted in string format. Since the price will
        nearly always come from web forms, it makes sense to default to
        that format.

        Args:
            price (str): A string representing a decimal price value.

        Returns:
            int: An integer with the lowest 2 digits representing the
                 fractional part.
        """
        if not isinstance(price, str):
            raise TypeError('Price must be given as a string!')
        if '.' in price:
            parts = price.split('.')
            if len(parts) != 2:
                raise ValueError('Price must be a string containing only a'
                                 ' 2-point precision decimal number!')
            if not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError('Price contains invalid characters!')
            if len(parts[1]) > 2:
                raise ValueError('Price must contain only 2 decimal places!')
            if len(parts[1]) == 1:
                parts[1] += '0'
            return int(parts[0]) * 100 + int(parts[1])
        else:
            if not price.isdigit():
                raise ValueError('Price must be a number!')
            return int(price) * 100

    @staticmethod
    def price_str_from_int(price):
        """Convert an integer price to a decimal value in a string.

        Args:
            price (int): A price in integer form, as stored in the db.

        Returns:
            str: A string containing the decimal representation of price.
        """
        str_price = str(price)
        return str_price[:-2] + '.' + str_price[-2:]

    @property
    def unit_type(self):
        """Get the unit_type column from the UnitType object in _unit_type.

        Returns:
            str: UnitType.unit_type associated with this packet.
        """
        return self._unit_type.unit_type

    @unit_type.setter
    def unit_type(self, unit_type):
        """Set the unit type for this seed packet.

        If the unit_type submitted corresponds to a pre-existing unit type,
        it will load that one and associate it with the packet, otherwise it
        will create a new one.

        Args:
            unit_type (str): The unit type to set.
        """
        ut = UnitType.query.filter_by(unit_type=unit_type).first()
        if ut is not None:
            self._unit_type = ut
        else:
            self._unit_type = UnitType(unit_type)


class Seed(db.Model):
    """Table for seed data.

    This table contains the primary identifying information for a seed
    we sell. Generally, this is the table called to get and display seed
    data on the website.

    Attributes:
        __tablename__ (str): Name of the table: 'seeds'
        id (int): Auto-incremented ID # for use as primary key.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
                        if it will be discontinued when low.
        in_stock (bool): True if a seed is in stock, False if not.
        name (str): The name of the seed (cultivar); the main product name.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    dropped = db.Column(db.Boolean)
    in_stock = db.Column(db.Boolean)
    name = db.Column(db.String(64), unique=True)


class SeedSubtype(db.Model):
    """"Table for seed subtypes.

    Some seeds fall under subtypes for further categorization. For example,
    strawberries are divided up into **strawberry** and **alpine strawberry**,
    and cosmos are divided into **dwarf cosmos**, **cosmos for cut flowers**,
    and **sulphur cosmos**.

    Attributes:
        __tablename__ (str): Name of the table: 'seed_subtypes'
        id (int): Auto-incremended ID # for use as primary key.
        label (str): The name of the seed subtype.
    """
    __tablename__ = 'seed_subtypes'
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), unique=True)


class SeedType(db.Model):
    """Table for seed types.

    A SeedType is the next tier below Category in how we divide up our seeds
    for display on the site. The SeedType is usually the seed's common name,
    such as coleus, sunflower, cucumber, or tomato.

    Attributes:
        __tablename__ (str): Name of the table: 'seed_types'
        id (int): Auto-incremented ID # for use as primary_key.
        description (str): A description of the seed type for display on that
                           seed type's page.
        label (str): The name of the seed type.
    """
    __tablename__ = 'seed_types'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    label = db.Column(db.String(64), unique=True)


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


class UnitType(db.Model):
    """Table for unit types for packets.

    Units correspond to the quantity of seeds in a packet, labeling what
    units the quantity is in, e.g. seeds, grams, ounces.

    Attributes:
        __tablename__ (str): Name of the table: 'unit_types'
        id (int): Auto-incremented ID # for use as primary key.
        unit_type (str): The unit of measurement for a packet's quantity.

    Backrefs:
        packets (Packet): backref from Packet to allow us to look up packets
                          by unit type.
    """
    __tablename__ = 'unit_types'
    id = db.Column(db.Integer, primary_key=True)
    unit_type = db.Column(db.String(32), unique=True)

    def __init__(self, unit_type=None):
        """__init__ for UnitType.

        Args:
            unit_type (str): A unit of measure for use in a Packet. Examples:
                             'seeds', 'oz', 'grams'.
        """
        self.unit_type = unit_type

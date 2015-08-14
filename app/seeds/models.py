from app import db


seeds_to_botanical_names = db.Table(
    'seeds_to_botanical_names',
    db.Model.metadata,
    db.Column('seeds_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('botanical_names_id',
              db.Integer,
              db.ForeignKey('botanical_names.id'))
)


class BotanicalName(db.Model):
    """Table for botanical (scientific) names of seeds.

    The botanical name is the scientific name of the species a seed belongs
    to. Examples include *Asclepias incarnata* (swamp milkweed) and
    *Echinacea purpurea*.

    Attributes:
        __tablename__ (str): Name of the table: 'botanical_names'
        id (int): Auto-incremented ID # for use as a primary key.
        _botanical_name (str): A botanical name associated with one or more
                              seeds. Get and set via the botanical_name
                              property.

    Properties:
        botanical_name: Getter returns _botanical_name.
                        Setter checks validity of botanical name and assigns
                        it to _botanical_name if valid, or raises a
                        ValueError if not.

    Backrefs:
        _seeds: Backref to seeds table to allow us to look up seeds by
                botanical name.
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

    def __repr__(self):
        """Return representation of BotanicalName in human-readable format."""
        return '<{0} \'{1}\'>'.format(self.__class__.__name__,
                                      self.botanical_name)

    @property
    def botanical_name(self):
        """Get _botanical_name as-is."""
        return self._botanical_name

    @botanical_name.setter
    def botanical_name(self, botanical_name):
        """Set _botanical_name if botanical_name is valid.

        Args:
            botanical_name (str): The botanical name to set.
        """
        if self.validate(botanical_name):
            self._botanical_name = botanical_name
        else:
            raise ValueError('botanical_name must be a valid binomen!')

    @staticmethod
    def validate(botanical_name):
        """Return True if botanical_name is a validly formatted binomen.

        Valid within reason; some may contain more than 2 words, so we only
        check the first two words.

        Args:
            botanical_name (str): A string containing a botanical name to
                                  check for valid formatting.

        Returns:
            bool: True if botanical_name's first two words constitute a
                  a validly formatted binomen.
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
        _price (str): Price (in US dollars) for this packet. Accessed via the
                      price property.
        _quantity (str): Amount of seeds in packet. Accessed via the quantity
                         property.
        unit_type_id (int): ForeignKey for associated UnitType.
        _unit_type (relationship): MtO relationship with UnitType. Accessed
                                   via the unit_type property.

    Properties:
        price: Getter returns a string representation of a decimal monetary
               value, converted from the integer value stored in _price.
               Setter takes a string containing a decimal number and converts
               it to a database-friendly integer before storing it in _price.
        unit_type: Getter returns the value of the UnitType.unit_type stored
                   in _unit_type.
                   Setter takes a string meant for UnitType.unit_type and
                   checks to see if the same UnitType already exists in the
                   database, and assigns it to _unit_type if it exists,
                   otherwise a new UnitType is created and assigned to
                   _unit_type.
        quantity: Getter returns a string representing the quantity converted
                  from the integer stored in _quantity.
                  Setter converts a string representing a quantity which may
                  contain fractional parts into an integer for storage in the
                  database.
    """
    __tablename__ = 'packets'
    id = db.Column(db.Integer, primary_key=True)
    _price = db.Column(db.Integer)
    _quantity = db.Column(db.Integer)
    unit_type_id = db.Column(db.Integer, db.ForeignKey('unit_types.id'))
    _unit_type = db.relationship('UnitType', backref='_packets')

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

        Args:
            quantity (str): The size/quantity of a packet.

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

        Returns:
            int: The converted integer value for use in the database.
        """
        if not isinstance(quantity, str):
            raise TypeError('quantity must be a string!')
        quantity = quantity.replace(' ', '')
        if '.' in quantity and '/' in quantity:
            raise ValueError('quantity must be a decimal or fraction,'
                             ' not both!')
        if '.' in quantity:
            parts = quantity.split('.')
            if len(parts) == 2:
                if len(parts[1]) > 9:
                        raise ValueError('quantity can only hold up to 9'
                                         ' decimal places!')
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
                    raise ValueError('quantity can only have a denominator'
                                     ' of up to 9 digits!')
                if parts[0].isdigit() and parts[1].isdigit():
                    return -(int(''.join(parts)) * 10 + len(parts[1]))
                else:
                    raise ValueError('quantity must be a number!')
            else:
                raise ValueError('quantity can only contain one forward'
                                 ' slash!')
        else:
            if quantity.isdigit():
                return int(quantity) * 10
            else:
                raise ValueError('quantity must be a number!')

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
        _botanical_names (relationship): MtM relationship with BotanicalName.
                                         Accessed via the botanical_names
                                         property.
        description (str): Product description in HTML format.
        dropped (bool): False if the seed will be re-stocked when low, False
                        if it will be discontinued when low.
        in_stock (bool): True if a seed is in stock, False if not.
        name (str): The name of the seed (cultivar); the main product name.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    _botanical_names = db.relationship('BotanicalName',
                                       secondary=seeds_to_botanical_names,
                                       lazy='dynamic',
                                       backref=db.backref('seeds',
                                                          lazy='dynamic'))
    description = db.Column(db.Text)
    dropped = db.Column(db.Boolean)
    in_stock = db.Column(db.Boolean)
    name = db.Column(db.String(64), unique=True)

    @property
    def botanical_names(self):
        """Return a list of the botanical names associated with this seed.

        Returns:
            list: A list of strings containing botanical names gotten from
                  BotanicalName.botanical_name.
        """
        bn_list = []
        for bn in self._botanical_names.all():
            bn_list.append(bn.botanical_name)
        return bn_list

    @botanical_names.setter
    def botanical_names(self, names):
        """Clear _botanical_names and set it from given list or string.

        Args:
            names (list, str): A list of strings containing
                               botanical names, or a single string
                               containing a botanical name.
        """
        self.clear_botanical_names()
        if isinstance(names, str):
            self.add_botanical_name(names)
        elif isinstance(names, list):
            for bn in names:
                self.add_botanical_name(bn)
        else:
            raise TypeError('botanical_names can only be set with a list of'
                            ' strings or a single botanical name string.')

    def add_botanical_name(self, name):
        """Add a botanical name to _botanical_names.

        Args:
            name (str): A botanical name to add to _botanical_names.
        """
        bn = BotanicalName.query.filter_by(_botanical_name=name).first()
        if bn is not None:
            self._botanical_names.append(bn)
        else:
            self._botanical_names.append(BotanicalName(name))

    def clear_botanical_names(self):
        """Clear _botanical_names without deleting them from the database.

        This does not actually delete them because other seeds may still use
        them. To delete them, use Seed._botanical_names.delete().

        Returns:
            int: The number of botanical names removed.
        """
        count = 0
        for bn in self.botanical_names:
            self.remove_botanical_name(bn)
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
        bn = self._botanical_names.filter_by(_botanical_name=name).first()
        if bn is None:
            return False
        else:
            self._botanical_names.remove(bn)
            return True


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
        _packets: backref from Packet to allow us to look up packets
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

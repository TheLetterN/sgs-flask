from app import db

categories_common_names_association = db.Table(
    'categories_common_names_association',
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id')),
    db.Column('common_name_id', db.Integer, db.ForeignKey('common_names.id'))
)

seeds_categories_association = db.Table(
    'seeds_categories_association',
    db.Column('seed_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'))
)


class Seed(db.Model):
    """Table containing seed information for display on the site.

    Database Columns:
        id -- Auto-generated unique identifier.
        binomen -- Scientific name of the seed.
        cultivar -- The cultivar name of the seed. (e.g. Tumbling Tom)
        description -- Product description for seed.
        packet_size -- Quantity or weight of seeds per packet.
        price -- Price of the seed.
        sku -- SKU for the seed.
        stock_status -- 0 = Discontinued 1 = In Stock 2 = Out of Stock
        common_name_id -- id for the CommonName associated with this seed.
    Relationships:
        common_name -- o2m, backref from CommonName.
        categories -- m2m,  backref from Category.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    binomen = db.Column(db.String(64))
    cultivar = db.Column(db.String(64))
    description = db.Column(db.Text)
    packet_size = db.Column(db.String(16))  # TODO verify with Don.
    price = db.Column(db.Float)
    sku = db.Column(db.String(16), unique=True)
    stock_status = db.Column(db.Integer)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


class Category(db.Model):
    """Broad categories for seeds, such as perennial flower, herb, vegetable.

    Database Columns:
        id -- Auto-generated unique identifier.
        meta_description -- Content for meta description tag.
        meta_keywords -- Content for meta keywords tag.
        name -- Name of category. (e.g. Perennial Flower)
    Relationships:
        seeds -- m2m, backref to Seed.
        common_names -- m2m,  backref to CommonName.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    meta_description = db.Column(db.Text)       # TODO verify with Don
    meta_keywords = db.Column(db.Text)          # TODO verify with Don
    name = db.Column(db.String(64), unique=True)
    seeds = db.relationship(
        'Seed',
        secondary=seeds_categories_association,
        backref=db.backref('categories', lazy='dynamic')
    )
    common_names = db.relationship(
        'CommonName',
        secondary=categories_common_names_association,
        backref=db.backref('categories', lazy='dynamic')
    )

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)


class CommonName(db.Model):
    """Common names for seeds, such as butterfly weed, sunflower, agastache.

    Database Columns:
        id -- Auto-generated unique identifier.
        name -- The common name of a seed.
        meta_description -- Content for meta description tag.
        meta_keywords -- Content for meta keywords tag.
    Relationships:
        seeds -- o2m, backref to Seed.
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    meta_description = db.Column(db.Text)       # TODO verify with Don
    meta_keywords = db.Column(db.Text)          # TODO verify with Don
    name = db.Column(db.String(64), unique=True)
    seeds = db.relationship('Seed', backref='common_name', lazy='dynamic')

    def __repr__(self):
        return '<{0} \'{1}\'>'.format(self.__class__.__name__, self.name)

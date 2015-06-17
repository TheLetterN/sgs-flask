from app import db


class Seed(db.Model):
    """Table containing seed information for display on the site.

    Database Columns:
        id -- Auto-generated unique identifier.
        binomen -- Scientific name of the seed.
        cultivar -- The cultivar name of the seed. (e.g. Tumbling Tom)
        description -- Product description for seed.
        price -- Price of the seed.
        sku -- SKU for the seed.
        stock_status -- 0 = Discontinued 1 = In Stock 2 = Out of Stock
        common_name_id -- id for the CommonName associated with this seed.
    Relationships:
        common_name -- backref from CommonName.
        categories -- backref from Category.
    """
    __tablename__ = 'seeds'
    id = db.Column(db.Integer, primary_key=True)
    binomen = db.Column(db.String(64))
    cultivar = db.Column(db.String(64))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    sku = db.Column(db.String(16), unique=True)
    stock_status = db.Column(db.Integer)
    common_name_id = db.Column(db.Integer, db.ForeignKey('common_names.id'))


class Category(db.Model):
    """Broad categories for seeds, such as perennial flower, herb, vegetable.

    Database Columns:
        id -- Auto-generated unique identifier.
        name -- Name of category. (e.g. Perennial Flower)
    Relationships:
        seeds -- backref to Seed.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    seeds = db.relationship(
        'Seed',
        secondary='seeds_categories',
        backref=db.backref('categories', lazy='dynamic')
    )


class CommonName(db.Model):
    """Common names for seeds, such as butterfly weed, sunflower, agastache.

    Database Columns:
        id -- Auto-generated unique identifier.
        name -- The common name of a seed.
    Relationships:
        seeds -- backref to Seed.
    """
    __tablename__ = 'common_names'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    seeds = db.relationship('Seed', backref='common_name', lazy='dynamic')


seeds_categories = db.Table(
    'seeds_categories',
    db.Column('seed_id', db.Integer, db.ForeignKey('seeds.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'))
)

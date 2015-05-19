import os
from flask import flash, url_for, request
from app import app
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate

#Create database
db = SQLAlchemy(app)

#Create our db migration object
migrate = Migrate(app, db)

class Seed(db.Model):
    """Seed is an SQLAlchemy db model for handling seed product data.
    
    Data Attributes:
        id -- Unique numerical ID generated by database.
        name -- Name as we want it to appear on the product page.
        genus -- Genus of seed.
        species -- Species of seed.
        description -- Product description.
        synonyms -- Other names the seed is called.
        series -- Series seed belongs to, if any. (Ex: Benary's Giant)
        variety -- Variety of seed. (Ex: zinnia, coleus, sunflower)
        category -- Type of plant. (Ex: annual flower, herb, vegetable)
        price -- Current price of the seed.
        is_active -- Whether or not the seed is to be restocked.
        in_stock -- Whether or not the seed is in stock.
        thumbnail -- Filename of thumbnail image.

    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    genus = db.Column(db.String(64))
    species = db.Column(db.String(64))
    description = db.Column(db.String(64))
    synonyms = db.relationship('Synonym',
                               backref='seed',
                               lazy='dynamic',
                               cascade='all, merge, delete, delete-orphan')
    series = db.Column(db.String(32))
    variety = db.Column(db.String(32))
    category = db.Column(db.String(32))
    price = db.Column(db.Float)
    is_active = db.Column(db.Boolean)
    in_stock = db.Column(db.Boolean)
    thumbnail = db.Column(db.String(64))
    errors = []
    
    def __init__(self,
                 name=None,
                 binomen=None,
                 description=None,
                 variety=None,
                 category=None,
                 price=None,
                 is_active=None,
                 in_stock=None,
                 thumbnail=None,
                 synonyms=None,
                 series=None):
        self.name = name
        self.set_binomen(binomen)
        self.description = description
        self.set_variety(variety)
        self.set_category(category)
        self.price = price
        self.is_active = is_active
        self.in_stock = in_stock
        self.thumbnail = thumbnail
        self.add_synonyms_from_string(synonyms)
        self.series = series
    
    def populate_from_form(self, form):
        """Populates addseed from a complete form object."""
        self.name = form.name.data
        self.set_binomen(form.binomen.data)
        self.description = form.description.data
        self.set_variety(form.variety.data)
        self.set_category(form.category.data)
        self.price = form.price.data
        self.is_active = form.is_active.data
        self.in_stock = form.in_stock.data
        self.add_synonyms_from_string(form.synonyms.data)
        series = form.series.data
        if form.thumbnail.data:
            thumbfile = request.files[form.thumbnail.name]
            self.save_thumbnail(thumbfile)

    def add_synonym(self, synonym):
        """Adds a synonym linked to our seed object."""
        self.synonyms.append(Synonym(synonym))

    def add_synonyms_from_list(self, synonyms):
        """Adds synonyms from a list."""
        for synonym in synonyms:
            self.add_synonym(synonym)

    def add_synonyms_from_string(self, synonyms):
        if synonyms is not None:
            self.add_synonyms_from_list(string_to_list(synonyms))
        else:
            synonyms = None

    def get_synonyms_list(self):
        """Returns a list of synonyms."""
        synonyms = []
        for synonym in self.synonyms.all():
            synonyms.append(synonym.name)
        return synonyms

    def get_synonyms_string(self):
        """Returns a string containing list of synonyms."""
        return list_to_string(self.get_synonyms_list())

    def get_fullname(self):
        """Returns full seed name including series."""
        if self.series is not None:
            return self.series + ' ' + self.name
        else:
            return self.name

    def set_binomen(self, binomen):
        """Sets genus and species from a binomen string."""
        if binomen is not None:
            genspec = [nomen.strip() for nomen in binomen.split(' ')]
            self.genus = genspec[0].lower().capitalize()
            self.species = genspec[1].lower()
        else:
            self.genus = None
            self.species = None

    def get_binomen(self):
        """Returns a binomen string."""
        return self.genus + ' ' + self.species

    def set_variety(self, variety):
        """Sets variety in the proper format for use with the database."""
        if variety is not None:
            self.variety = variety.lower().strip()
        else:
            variety = None

    def set_category(self, category):
        """Sets category in db-friendly format."""
        if category is not None:
            self.category = category.lower().strip()
        else:
            self.category = None

    def get_images_directory(self):
        """Returns the path to this seed's image files."""
        return os.path.join(
            app.config['IMAGES_FOLDER'],
            self.variety.lower(),
            self.name.lower()
        )


    def create_images_directory(self):
        """Creates this seed's images directory if not present."""
        try:
            os.makedirs(self.get_images_directory())
        except OSError as error:
            if (error.errorno == os.errorno.EEXIST and
                    os.path.isdir(self.get_images_directory())):
                pass
            else:
                raise

    def save_image(self, image):
        """Saves an image to this seed's images directory."""
        fullpath = os.path.join(self.get_images_directory(), image.filename)
        self.create_images_directory()
        image.save(fullpath)

    def save_thumbnail(self, image):
        """Saves and sets a thumbnail image."""
        self.thumbnail = image.filename
        self.save_image(image)

    def get_image_location(self, filename):
        """Returns the full path of the image specified."""
        return os.path.join(self.get_images_directory(), filename)

    def image_exists(self, filename):
        """Returns true if the specified image file exists."""
        if os.path.isfile(self.get_image_location(filename)):
            return True
        else:
            return False

    def thumbnail_exists(self):
        """Returns true if thumbnail image file exists."""
        if self.thumbnail is not None:
            return self.image_exists(self.thumbnail)
        else:
            return False

    def get_image_url(self, filename):
        """Returns the URL for an image as assocated with this seed."""
        relpath = ('images/' + 
                   self.variety.lower() + '/' + 
                   self.name.lower() + '/' +
                   filename)
        return url_for('static', filename=relpath)

    def get_thumbnail_url(self):
        """Returns the URL of this seed's thumbnail."""
        return self.get_image_url(self.thumbnail)
        
    def verify(self):
        """Verifies that seed is ready to be stored in the database."""
        valid = True
        if Seed.query.filter_by(name=self.name).first() is not None:
            self.errors.append('%s is already in the database! Please edit it instead of re-adding.' % self.name)
            valid = False
        return valid
            

class Synonym(db.Model):
    """A synonym for a seed.

    Data Attributes:
        id -- Unique ID for database
        name -- The synonym itself.
        seed_id -- The ID of the parent seed.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    seed_id = db.Column(db.Integer, db.ForeignKey('seed.id'))

    def __init__(self, name):
        self.name = name



def string_to_list(stringlist):
    """Splits a string by its commas and returns a list."""
    return [item.strip() for item in stringlist.split(',')]

def list_to_string(listobj):
    """Returns a list as a string w/ commas."""
    return ', '.join(listobj)


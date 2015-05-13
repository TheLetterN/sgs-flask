"""
Our main unit tests file.

Unit tests are a very good way to ensure that our project's behavior
remains consistent between changes, and that we will more easily be
able to narrow down causes of unexpected behaviors that may occur in
the future.

It is important to write tests for each method we write that does
anything that could have unexpected results. We don't need to test
Things that have well-known behavior, such as a simple assignment.

It is even more important that we run the tests before committing
any changes we make! They can be run via the command:
    manage.py test
"""

import os
import shutil
import unittest
from cStringIO import StringIO
from werkzeug import secure_filename
from app import app, db
from config import basedir
from app.forms import get_images_directory
from app.models import Seed


class TestCaseExample(unittest.TestCase):
    """This is just a set of examples of unit tests.
    
    Notes:
        All methods for testing must begin with "test_"

    Methods:
        setUp -- Perform actions needed to create testing environment.
        tearDown -- Remove/close anything only needed during testing.
        test_passing -- A test that always passes.
        test_failing -- A test that always fails.
    """

    def setUp(self):
        """Create test environment."""
        #Example:
        #set_database_location(testing_location)
        #create_database(testing_database)
        pass    #Do nothing

    def tearDown(self):
        """Destroy test environment."""
        #Example:
        #destroy_database(testing_database)
        pass

    def test_passing(self):
        """This test always passes."""
        self.assertTrue(True)

    #The unittest.expectedFailure decorator tells unittest that a test should
    #fail, and therefore not count as a failure.
    @unittest.expectedFailure
    def test_failing(self):
        """This test always fails."""
        self.assertTrue(False)

class TestViews(unittest.TestCase):
    """Test views (views.py and templates) independent of other modules.
    
    Methods:
        setUp -- Create test environment.
        tearDown -- Destroy test environment.
        test_default_title -- Make sure page title is SITE_NAME when no
                              title is passed to template.
    """

    def setUp(self):
        #Set config to show we're in testing mode.
        app.config['TESTING'] = True
        #Create test version of our app.
        self.app = app.test_client()

    def tearDown(self):
        pass    #Nothing needs to be done during teardown.

    def test_default_title(self):
        """Page title should default to config.SITE_NAME."""
        retval = self.app.get('/')
        #retval.data contains the HTML generated by running index()
        site_title = '<title>' + app.config['SITE_NAME'] + '</title>'
        self.assertTrue(site_title in retval.data)


class TestAddSeedForm(unittest.TestCase):
    """Testing AddSeedForm from forms.py."""

    def setUp(self):
        #Enable testing mode
        app.config['TESTING'] = True

        #Turn CSRF off when testing forms
        app.config['WTF_CSRF_ENABLED'] = False

        #Set images folder to tmp
        app.config['IMAGES_FOLDER'] = os.path.join(basedir, 'tmp')

        #Create a test app
        self.app = app.test_client()

    def tearDown(self):
        #Delete all files in the tmp folder
        clear_tmp()

    def simulate_post(self, data):
        """Posts data to our test client and returns the result."""
        return self.app.post('/manage/addseed', data=data, 
                             follow_redirects=True)

    def test_valid_seed_data(self):
        """A valid set of data should flash a success message."""
        seed = create_seed_data()
        #success = the message we flash if the seed is submitted successfully.
        success = '%s has been added!' % seed['name']
        retval = self.simulate_post(seed)
        self.assertTrue(success in retval.data)

    def test_no_seed_data(self):
        """Submitting the form with no data should cause errors."""
        seed = None
        #These fields should have InputRequired validators:
        #name, binomen, description, variety, category, price
        #Total expected InputRequired errors: 6
        retval = self.simulate_post(seed)
        self.assertEqual(retval.data.count('This field is required.'), 6)

    def test_bad_file_type(self):
        """Thumbnail files should be in jpg, png, or gif format."""
        seed = create_seed_data()
        errormsg = 'Thumbnail format: jpg, png, gif' 
        seed['thumbnail'] = (StringIO('Not really HTML'), 'soulmate.html')
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)
        seed['thumbnail'] = (StringIO('Not really PHP'), 'soulmate.php')
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)
        seed['thumbnail'] = (StringIO('Not really an EXE'), 'soulmate.exe')
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)
        seed['thumbnail'] = (StringIO('Not really a python file'), 'soulmate.py')
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)

    def test_too_long_synonym(self):
        """Synonyms longer than 64 characters should cause an error."""
        seed = create_seed_data()
        errormsg = 'Each synonym must be 64 characters or less.'
        seed['synonyms'] = seed['synonyms'] + ', This synonym is unreasonably\
                           long and it really shouldn\'t be likely to happen.'
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)

    def test_too_long_genus_or_species_in_binomen(self):
        """Each word in binomen must be <= 64 characters."""
        seed = create_seed_data()
        errormsg = ('Each word in binomen (genus and species) ' +
                    'must be 64 characters or less.')
        seed['binomen'] = ('Foo superlongspeciesnamewhichisutterlyimprobable' +
                           'butstilltechnicallypossiblesoweshouldtestforit')
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)

    def test_binomen_word_count(self):
        """Binomen should be exactly 2 words."""
        seed = create_seed_data()
        errormsg = 'Binomen must be 2 words separated by a space.'
        seed['binomen'] = 'Too many words'
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)
        #Create a new seed because thumbnail causes a ValueError exception if
        #we try to re-use the same seed data object more than once due to the
        #StringIO object being closed after posting to our test client.
        seed = create_seed_data()
        seed['binomen'] = 'Toofew'
        retval = self.simulate_post(seed)
        self.assertTrue(errormsg in retval.data)

    #TODO: The functionality this tests for should be moved to models
    def test_thumbnail_upload(self):
        """A valid thumbnail should be saved and moved to its seed's images."""
        seed = create_seed_data()
        seed['thumbnail'] = (StringIO('Still not a real file.'), 'thumb.jpg')
        retval = self.simulate_post(seed)
        self.assertTrue(os.path.isfile(os.path.join(
            get_images_directory(variety=seed['variety'], name=seed['name']),
            secure_filename('thumb.jpg'))))

    def test_no_thumbnail(self):
        """Nothing should go wrong if there's no thumbnail file."""
        seed = create_seed_data()
        seed['thumbnail'] = None
        success = '%s has been added!' % seed['name']
        retval = self.simulate_post(seed)
        self.assertTrue(success in retval.data)


class TestSeedModel(unittest.TestCase):
    """Tests for our Seed object."""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = (
            'sqlite:///' + os.path.join(basedir, 'tmp', 'test.db')
        )
        app.config['IMAGES_FOLDER'] = os.path.join(basedir, 'tmp')
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        clear_tmp()

    def test_add_synonym(self):
        """Add synonym should add a string to synonyms."""
        seed = create_seed_object()
        synonym = 'white indian hemp'
        seed.add_synonym(synonym)
        self.assertTrue(synonym in seed.get_synonyms_list())

    def test_add_synonyms_from_list(self):
        """add_synonyms_from_list should add from a list object."""
        #We don't want the default synonyms present, so we clear them
        seed = create_seed_object()
        clear_synonyms(seed)
        synlist = ['swamp milkweed',
                   'rose milkweed',
                   'swamp silkweed',
                   'white indian hemp']
        seed.add_synonyms_from_list(synlist)
        self.assertEqual(
            sorted(seed.get_synonyms_list()),
            sorted(synlist)
        )

    def test_synonyms_string(self):
        """Synonyms in format "syn1, syn2, syn3" should be addable/gettable."""
        seed = create_seed_object()
        clear_synonyms(seed)
        synonyms = 'swamp milkweed, rose milkweed, swamp silkweed, white indian hemp'
        seed.add_synonyms_from_string(synonyms)
        self.assertEqual(seed.get_synonyms_string(), synonyms)

    def test_set_binomen(self):
        """set_binomen should set genus and species."""
        seed = create_seed_object()
        seed.binomen = None
        genus = 'Fake'
        species = 'binomen'
        seed.set_binomen(genus + ' ' + species)
        self.assertEqual(seed.genus, genus)
        self.assertEqual(seed.species, species)


def create_seed_data():
    return dict(
        name='Soulmate',
        binomen='Asclepias incarnata',
        description=('Produces absolutely beautiful deep rose pink flowers ' +
                     'in large umbels in only 3 months from sowing. They ' +
                     'are superb cut flowers, and of course the butterflies ' +
                     'find them irresistible. Long blooming. Grows to 3.5 ' +
                     'feet tall and is a stunning background plant. Easy to ' + 
                     'germinate seeds. Winter hardy to zone 3.'),
        variety='Butterfly Weed',
        category='Perennial Flower',
        price='2.99',
        is_active=True,
        in_stock=True,
        synonyms='swamp milkweed, rose milkweed',
        thumbnail=(StringIO('This is a fake file.'), 'soulmate.jpg')
        )

def create_seed_object():
    """Creates a default valid Seed object."""
    return Seed(
        name='Soulmate',
        binomen='Asclepias incarnata',
        description=('Produces absolutely beautiful deep rose pink flowers ' +
                     'in large umbels in only 3 months from sowing. They ' +
                     'are superb cut flowers, and of course the butterflies ' +
                     'find them irresistible. Long blooming. Grows to 3.5 ' +
                     'feet tall and is a stunning background plant. Easy to ' + 
                     'germinate seeds. Winter hardy to zone 3.'),
        variety='Butterfly Weed',
        category='Perennial Flower',
        price='2.99',
        is_active=True,
        in_stock=True,
        synonyms='swamp milkweed, rose milkweed'
        )

def clear_synonyms(seed):
    """Clears the synonyms for a given seed object.
    NOTE: This does not clear them from the database!
    """
    for synonym in seed.synonyms.all():
        seed.synonyms.remove(synonym)
    #There is no return here because seed is a mutable object; Python passes
    #mutable objects by reference, so if we made seed2 = seed1, for example,
    #It does not create a new copy of seed1, it instead makes seed2 point to
    #seed1. If you alter seed1, it will alter seed2, too, and vice-versa!

def clear_tmp():
    """Deletes all files in the tmp directory."""
    temppath = os.path.join(basedir, 'tmp')
    for tempfile in os.listdir(temppath):
        fullfile = os.path.join(temppath, tempfile)
        if os.path.isdir(fullfile):
            shutil.rmtree(fullfile)
        else:
            os.remove(fullfile)


#If tests.py is run directly, it should automatically run all tests.
if __name__ == '__main__':
    unittest.main()

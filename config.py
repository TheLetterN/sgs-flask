#This file contains settings for our Flask application.
import os

#Get the full path for our sgs_flask directory.
basedir = os.path.abspath(os.path.dirname(__file__))

#Debug mode should be enabled during development.
DEBUG=True

#This is a random string used for securely generating things like cookies.
#I used os.urandom(24) to generate it.
SECRET_KEY = '\xecU\xf2\xb6\xb6\x86\x81\xba\x1a\x0ci\xfc\xe2OfB\xaf\xaa\xc3\xc7O\xfe>\xf5'

#Database information
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'

#Upload folder location
UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')

#Images folder location
IMAGES_FOLDER = os.path.join(basedir, 'app', 'static', 'images')

#Website information
SITE_NAME = 'Swallowtail Garden Seeds'

#This file lets python know our "app" directory is a python module. This allows
#Us to easily use it and the files it contains.It also contains anything we
# need to automatically run when we start the website application.

#Import needed Python modules.
import json
import os

#Import the built-in modules we need for our website:
from flask import Flask

#Now we create an "app" object which we will use throughout our program; this
#is essntially the core object of our website, which everything else either
#derives from or communicates with.
app = Flask(__name__)

#Now we need to import our views.py file so that our application can actually 
#find our pages! We need to do this after the previous step because 'app'
#didn't exist until we created it.
from app import views

#Next we load our config.py file, which contains settings for our application:
app.config.from_object('config')

#Add the SITE_NAME constant from config.py to Jinja globals so we can use it
#in our templates without having to pass it to view functions.
app.jinja_env.globals.update(SITE_NAME=app.config['SITE_NAME'])

#Allow loading JSON files from jinja templates.
def load_json_file(filename, directory=None):
    """Loads specified json file and returns a Python object."""
    if directory == None:
        directory = app.config['JSON_FOLDER']
    fullname = os.path.join(directory, filename)
    if os.path.isfile(fullname):
        with open(fullname, 'r') as infile:
            return json.loads(infile.read())
    else:
        return None

app.jinja_env.globals.update(load_json_file=load_json_file)


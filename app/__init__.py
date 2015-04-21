#This file lets python know our "app" directory is a python module. This allows
#Us to easily use it and the files it contains.It also contains anything we
# need to automatically run when we start the website application.

#First we import the built-in modules we need for our website:
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

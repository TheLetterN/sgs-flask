#!venv/bin/python
"""Manage running, testing, and interacting with sgs_flask.
Use manage.py --help to list available commands."""
import nose
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import app
from app.models import db
import tests

#Create a Manager object to assign commands to
manager = Manager(app)

#Create a migrate object
migrate = Migrate(app, db)

#Example of creating a command using the manager.command decorator
@manager.command
def hello():
    """Say hello to your little friend."""
    print "Why are you talking to a computer program?"

#@manager.command
#def test():
#    """Run all unit tests from tests.py."""
#    suite = unittest.TestLoader().discover('tests')
#    unittest.TextTestRunner(verbosity=2).run(suite)
@manager.command
def test():
    nose.main(argv=['', '--verbosity=3'])

#Manage our database and migrations
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()

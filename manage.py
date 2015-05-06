#!venv/bin/python
"""Manage running, testing, and interacting with sgs_flask.
Use manage.py --help to list available commands."""
from flask.ext.script import Manager, Command
from app import app

#Create a Manager object to assign commands to
manager = Manager(app)

#Example of creating a command using the manager.command decorator
@manager.command
def hello():
    """Say hello to your little friend."""
    print "Why are you talking to a computer program?"

if __name__ == '__main__':
    manager.run()

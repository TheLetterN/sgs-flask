#!venv/bin/python
"""Manage running, testing, and interacting with sgs_flask.
Use manage.py --help to list available commands."""
import unittest
from flask.ext.script import Manager, Command
from app import app
import tests

#Create a Manager object to assign commands to
manager = Manager(app)

#Example of creating a command using the manager.command decorator
@manager.command
def hello():
    """Say hello to your little friend."""
    print "Why are you talking to a computer program?"

@manager.command
def test():
    """Run all unit tests from tests.py."""
    suite = unittest.TestLoader().loadTestsFromModule(tests)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    manager.run()

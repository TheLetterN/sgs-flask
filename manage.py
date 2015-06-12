#!/usr/bin/env python
import os
import pytest
from flask.ext.script import Manager, Shell
from app import create_app

app = create_app(os.getenv('SGS_CONFIG') or 'default')
manager = Manager(app)


def make_shell_context():
    return dict(app=app)


@manager.command
def hello():
    """Say hello to your Flask site."""
    print('Why are you talking to a python script?')


@manager.command
def test():
    """Run tests."""
    pytest.main('tests')


manager.add_command("shell", Shell(make_context=make_shell_context))

if __name__ == '__main__':
    manager.run()

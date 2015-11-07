import pytest
from app import create_app
from app import db as _db

@pytest.yield_fixture(scope='session')
def app(request):
    print('\nSetting up app.')
    _app = create_app('testing')
    context = _app.app_context()
    context.push()
    yield _app
    print('\nTearing down app.')
    context.pop()


@pytest.fixture(scope='function')
def db(app, request):
    print('\nSetting up db.')
    _db.app = app
    _db.create_all()
    def teardown():
        print('\nTearing down db.')
        _db.session.rollback()
        _db.session.remove()
        if _db.engine.dialect.name == 'postgresql':
            _db.engine.execute('drop schema if exists public cascade')
            _db.engine.execute('create schema public')
        _db.drop_all()
    request.addfinalizer(teardown)
    return _db

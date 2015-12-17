import json
from io import StringIO
from datetime import datetime, timedelta
from unittest import mock
import pytest
from app.redirects import Redirect, RedirectsFile
from tests.conftest import app


class TestRedirect:
    """Test methods of Redirect from the redirect module."""
    def test_repr(self):
        """Return string describing contents of redirect."""
        rd = Redirect('/old/path', '/new/path', 302)
        assert rd.__repr__() == '<Redirect from /old/path to /new/path, '\
                                'status code: 302>'

    def test_eq(self):
        """Return true if all data in two Redirects is the same."""
        dt = datetime.utcnow()
        rd1 = Redirect('/old/path', '/new/path', 302, dt)
        rd2 = Redirect('/old/path', '/new/path', 302, dt)
        assert rd1 is not rd2
        assert rd1 == rd2
        rd2.new_path = '/newer/path'
        assert rd1 != rd2
        rd2.new_path = '/new/path'
        assert rd1 == rd2
        rd2.old_path = '/oldest/path'
        assert rd1 != rd2
        rd2.old_path = '/old/path'
        assert rd1 == rd2
        rd2.status_code = 301
        assert rd1 != rd2
        rd2.status_code = 302
        assert rd1 == rd2
        rd2.date_created = datetime.utcnow()
        assert rd1 != rd2
        rd2.date_created = dt
        assert rd1 == rd2

    def test_old_path_getter(self):
        """Return self._old_path"""
        rd = Redirect('/old/path', '/new/path', 302)
        rd._old_path = '/older/path'
        assert rd.old_path == '/older/path'

    def test_old_path_setter(self):
        """Set self._old_path to data if it's valid, else raise ValueError."""
        rd = Redirect('/old/path', '/new/path', 302)
        rd.old_path = '/older/path'
        assert rd._old_path == '/older/path'
        with pytest.raises(ValueError):
            rd.old_path = 'not/root/relative/path'

    def test_new_path_getter(self):
        """Return self._new_path"""
        rd = Redirect('/old/path', '/new/path', 302)
        rd._new_path = '/newer/path'
        assert rd.new_path == '/newer/path'

    def test_new_path_setter(self):
        """Set self._new_path to data if valid, else raise ValueError."""
        rd = Redirect('/old/path', '/new/path', 302)
        rd.new_path = '/newer/path'
        assert rd._new_path == '/newer/path'
        with pytest.raises(ValueError):
            rd.new_path = 'not/root/relative/path'

    def test_status_code_getter(self):
        """Return self._status_code"""
        rd = Redirect('/old/path', '/new/path', 302)
        rd._status_code = 301
        assert rd.status_code == 301

    def test_status_code_setter(self):
        """Set data to self._status code if an integer between 300-309.

        Raise a TypeError if not int, or a ValueError if not between 300-309.
        """
        rd = Redirect('/old/path', '/new/path', 302)
        rd.status_code = 301
        assert rd._status_code == 301
        with pytest.raises(TypeError):
            rd.status_code = '301'
        with pytest.raises(ValueError):
            rd.status_code = 200
        with pytest.raises(ValueError):
            rd.status_code = 404
        with pytest.raises(ValueError):
            rd.status_code = 299
        with pytest.raises(ValueError):
            rd.status_code = 310

    def test_date_created_getter(self):
        """Return self._date_created"""
        rd = Redirect('/old/path', '/new/path', 302)
        dt = datetime.utcnow()
        rd._date_created = dt
        assert rd.date_created == dt

    @mock.patch('app.redirects.utcnow', return_value=datetime(2000, 1, 1))
    def test_date_created_setter(self, mock_dt):
        """Set with given datetime, or with current utc datetime if none given.

        Raise a TypeError if given non-datetime data.
        """
        rd = Redirect('/old/path', '/new/path', 302)
        dt = datetime(2012, 12, 21)
        assert rd._date_created == datetime(2000, 1, 1)
        rd.date_created = dt
        assert rd._date_created == dt
        with pytest.raises(TypeError):
            rd.date_created = '12/12/12'

    def test_message(self):
        """Return a string describing the redirect."""
        rd = Redirect('/old/path', '/new/path', 302)
        assert rd.message() == 'Redirect from /old/path to /new/path with '\
                               'status code 302'

    @mock.patch('app.redirects.redirect')
    def test_redirect_path(self, mock_redirect):
        """Creates a redirect to self.new_path with self.status_code."""
        rd = Redirect('/old/path', '/new/path', 302)
        rd.redirect_path()
        mock_redirect.assert_called_with('/new/path', 302)

    def test_add_to_app(self, app):
        """Add a url_rule for redirect to given app."""
        rd = Redirect('/old/path', '/new/path', 302)
        with app.test_client() as tc:
            assert '/old/path' not in [rule.rule for
                                       rule in
                                       app.url_map.iter_rules()]
            rd.add_to_app(app)
            assert '/old/path' in [rule.rule for
                                   rule in
                                   app.url_map.iter_rules()]

    def test_to_json_and_back(self):
        """A Redirect converted to JSON should convert back to a redirect."""
        rd1 = Redirect('/old/path', '/new/path', 302)
        jsondump = rd1.to_JSON()
        rd2 = Redirect.from_JSON(jsondump)
        assert rd1 == rd2


class TestRedirectsFile:
    """Test methods of RedirectsFile from the redirects module."""
    def test_repr(self):
       """Return a string representing the redirects file."""
       rdf = RedirectsFile('/tmp/redirects.json')
       assert rdf.__repr__() == '<RedirectsFile \'/tmp/redirects.json\'>'

    def test_add_redirect_new_path_redirected_from(self):
        """Raise ValueError if a redirect already exists from a new path.

        This should also prevent circular redirects.
        """
        rd1 = Redirect('/path/one', '/path/two', 302)
        rd2 = Redirect('/path/three', '/path/one', 302)
        rd3 = Redirect('/path/two', '/path/one', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        with pytest.raises(ValueError):
            rdf.add_redirect(rd2)
        with pytest.raises(ValueError):
            rdf.add_redirect(rd3)

    def test_add_redirect_old_path_in_use(self):
        """Raise ValueError if a redirect already exists from an old path."""
        rd1 = Redirect('/old/path', '/new/one', 302)
        rd2 = Redirect('/old/path', '/new/two', 302)
        rdf = RedirectsFile('/tmp/redirects.json')
        rdf.add_redirect(rd1)
        with pytest.raises(ValueError):
            rdf.add_redirect(rd2)

    def test_add_redirect_prevents_chains(self):
        """If adding a redirect would create a chain, edit old redirect."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/two', '/three', 302)
        rdf = RedirectsFile('/tmp/redirects.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        for rd in rdf.redirects:
            assert rd.new_path == '/three'

    def test_add_redirect_wrong_type(self):
        """Raise TypeError if given data that is not a Redirect object."""
        rdf = RedirectsFile('/tmp/foo.json')
        with pytest.raises(TypeError):
            rdf.add_redirect('/old/path')

    def test_remove_redirect(self):
        """Remove a redirect from self.redirects."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rd3 = Redirect('/five', '/six', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        rdf.add_redirect(rd3)
        assert len(rdf.redirects) == 3
        assert rd2 in rdf.redirects
        rdf.remove_redirect(rd2)
        assert len(rdf.redirects) == 2
        assert rd2 not in rdf.redirects

    @mock.patch('app.redirects.os.path.exists')
    def test_exists(self, mock_exists):
        """Return True if file specified by self.file_name exists."""
        rdf = RedirectsFile('/tmp/foo.json')
        mock_exists.return_value = True
        assert rdf.exists()
        mock_exists.return_value = False
        assert not rdf.exists()
        mock_exists.assert_called_with('/tmp/foo.json')

    def test_get_redirect_with_old_path(self):
        """Return redirect with given old_path if it exists, None if not."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        retrd = rdf.get_redirect_with_old_path('/three')
        assert retrd == rd2
        retrd = rdf.get_redirect_with_old_path('/two')
        assert retrd is None
        retrd = rdf.get_redirect_with_old_path('/four')
        assert retrd is None

    def test_load(self):
        """Load redirects from specified file or self.file_name."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rd3 = Redirect('/five', '/six', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        rdf.add_redirect(rd3)
        json_file = StringIO()
        json_file.write(json.dumps([rd.to_JSON() for rd in rdf.redirects]))
        json_file.seek(0)
        rdf2 = RedirectsFile('/tmp/foo.json')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            m.return_value = json_file
            rdf2.load('/tmp/bar.json')
            m.assert_called_with('/tmp/bar.json', 'r', encoding='utf-8')
        json_file = StringIO()
        json_file.write(json.dumps([rd.to_JSON() for rd in rdf.redirects]))
        json_file.seek(0)
        rdf2 = RedirectsFile('/tmp/foo.json')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            m.return_value = json_file
            rdf2.load()
            m.assert_called_with('/tmp/foo.json', 'r', encoding='utf-8')

    def test_load_file(self):
        """Populate self.redirects with JSON data from a file-like object."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rd3 = Redirect('/five', '/six', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        rdf.add_redirect(rd3)
        json_file = StringIO()
        json_file.write(json.dumps([rd.to_JSON() for rd in rdf.redirects]))
        json_file.seek(0)
        rdf2 = RedirectsFile('/tmp/foo.json')
        rdf2.load_file(json_file)
        assert rdf.redirects == rdf2.redirects
        json_file = StringIO()
        json_file.write(json.dumps([rd.to_JSON() for rd in rdf.redirects]))
        json_file.seek(0)

    def test_save(self):
        """Save redirects to specified file or self.file_name."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rd3 = Redirect('/five', '/six', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        rdf.add_redirect(rd3)
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            m.return_value = StringIO()
            rdf.save('/tmp/bar.txt')
            m.assert_called_with('/tmp/bar.txt', 'w', encoding='utf-8')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            m.return_value = StringIO()
            rdf.save()
            m.assert_called_with('/tmp/foo.json', 'w', encoding='utf-8')

    def test_save_no_redirects(self):
        """Raise a ValidationError if save is run with no data to save."""
        rdf = RedirectsFile('/tmp/foo.txt')
        with pytest.raises(ValueError):
            rdf.save('/tmp/bar.txt')
        with pytest.raises(ValueError):
            rdf.save()

    def test_save_file(self):
        """Save redirects to a JSON string in a file or file-like object."""
        rd1 = Redirect('/one', '/two', 302)
        rd2 = Redirect('/three', '/four', 302)
        rd3 = Redirect('/five', '/six', 302)
        rdf = RedirectsFile('/tmp/foo.json')
        rdf.add_redirect(rd1)
        rdf.add_redirect(rd2)
        rdf.add_redirect(rd3)
        json_file = StringIO()
        json_file.write(json.dumps([rd.to_JSON() for rd in rdf.redirects]))
        json_file.seek(0)
        json_ofile = StringIO()
        rdf.save_file(json_ofile)
        json_ofile.seek(0)
        assert json_file.read() == json_ofile.read()


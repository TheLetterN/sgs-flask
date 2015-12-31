from flask import url_for
from unittest import mock
from app.seeds.views import list_to_or_string, redirect_warning


class TestModuleFunctions:
    """Test helper functions used within the module."""
    def test_list_to_or_string(self):
        """Return a string list delineated by commas with or between last 2."""
        assert list_to_or_string(['one']) == 'one'
        assert list_to_or_string(['one', 'two']) == 'one or two'
        assert list_to_or_string(['one', 'two', 'three']) ==\
            'one, two, or three'
        assert list_to_or_string(['one', 'two', 'three', 'four']) ==\
            'one, two, three, or four'

    def test_redirect_warning(self):
        """Return a string warning that a redirect should probably be made."""
        assert redirect_warning('/old/path', '<link to new path>') ==\
            'Warning: the path \'/old/path\' is no longer valid. You may '\
            'wish to redirect it to <link to new path>.'


class TestAddIndex:
    """Test add_index route."""
    def test_add_index_renders_page(self, app):
        """Render the Add Index page given no form data."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_index'), follow_redirects=True)
        assert 'Add Index' in str(rv.data)


class TestAddPacket:
    """Test add_packet route."""
    def test_add_packet_no_cv_id(self, app):
        """Redirect to select_cultivar given no cv_id."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_packet'))
        assert rv.location == url_for('seeds.select_cultivar',
                                      dest='seeds.add_packet',
                                      _external=True)


class TestAddRedirect:
    """Test add_redirect_route."""
    def test_add_redirect_renders_with_args(self, app):
        """Fill form with arg data if it exists."""
        with app.test_client() as tc:
            rv = tc.get(url_for('seeds.add_redirect',
                                old_path='/old/path',
                                new_path='/new/path',
                                status_code=302))
        assert '/old/path' in str(rv.data)
        assert '/new/path' in str(rv.data)
        assert '302' in str(rv.data)

    @mock.patch('app.seeds.views.Pending')
    @mock.patch('app.seeds.views.RedirectsFile')
    def test_add_redirect_with_submission(self, mr, mp, app):
        """Add a redirect to RedirectsFile."""
        mr.exists.return_value = True
        mp.exists.return_value = True
        with app.test_client() as tc:
            rv = tc.post(url_for('seeds.add_redirect'),
                         data=dict(old_path='/old/path',
                                   new_path='/new/path',
                                   status_code='302'),
                         follow_redirects=True)
        assert 'added. It will take effect on next restart' in str(rv.data)
        mrc = str(mr.mock_calls)
        assert 'call(\'{0}\')'.format(app.config.get('REDIRECTS_FILE')) in mrc
        assert 'call().exists()' in mrc
        assert 'call().load()' in mrc
        assert 'from /old/path to /new/path' in mrc
        assert 'call().save()' in mrc
        mpc = str(mp.mock_calls)
        assert 'call(\'{0}\')'.format(app.config.get('PENDING_FILE')) in mpc
        assert 'call().exists()' in mpc
        assert 'call().load()' in mpc
        assert 'call().add_message' in mpc
        assert 'call().save()' in mpc

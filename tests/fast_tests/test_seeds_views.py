from flask import url_for
from unittest import mock
from app.seeds.views import redirect_warning


class TestModuleFunctions:
    """Test helper functions used within the module."""
    def test_redirect_warning(self):
        """Return a string warning that a redirect should probably be made."""
        assert redirect_warning('/old/path', '<link to new path>') ==\
            'Warning: the path \'/old/path\' is no longer valid. You may '\
            'wish to redirect it to <link to new path>.'


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

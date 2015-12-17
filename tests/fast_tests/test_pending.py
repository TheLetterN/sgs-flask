from unittest import mock
import pytest
from app.pending import Pending

class TestPending:
    """Contains tests for the pending module."""

    def test_add_message(self):
        """Adding a message should concatenate message to changes.
        
        It should also add a newline before new data if previous data exists.
        """
        pd = Pending('/tmp/foo.txt')
        assert pd.changes == ''
        pd.add_message('This is not a message.')
        assert pd.changes == 'This is not a message.'
        pd.add_message('This is not a message either.')
        assert pd.changes == 'This is not a message.\n'\
                             'This is not a message either.'
        pd.add_message('Nor is this a message.')
        assert pd.changes == 'This is not a message.\n'\
                             'This is not a message either.\n'\
                             'Nor is this a message.'

    def test_clear(self):
        """Using clear should set messages to empty string."""
        pd = Pending('/tmp/foo.txt')
        pd.add_message('This is not a message.')
        assert pd.changes != ''
        pd.clear()
        assert pd.changes == ''
        pd.add_message('One')
        pd.add_message('Two')
        pd.add_message('Three')
        assert pd.changes != ''
        pd.clear()
        assert pd.changes == ''

    def test_load(self):
        """Load loads pending changes from a file, or self.file_name."""
        pd = Pending('/tmp/foo.txt')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            pd.load('/tmp/bar.txt')
        m.assert_called_with('/tmp/bar.txt', 'r', encoding='utf-8')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            pd.load()
        m.assert_called_with('/tmp/foo.txt', 'r', encoding='utf-8')

    def test_save(self):
        """Save saves pending changes to file, or self.file_name."""
        pd = Pending('/tmp/foo.txt')
        pd.add_message('This is not a message.')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            pd.save('/tmp/bar.txt')
        m.assert_called_with('/tmp/bar.txt', 'w', encoding='utf-8')
        m = mock.mock_open()
        with mock.patch('builtins.open', m, create=True):
            pd.save()
        m.assert_called_with('/tmp/foo.txt', 'w', encoding='utf-8')

    @mock.patch('os.path.exists')
    def test_exists(self, mock_exists):
        """Check if file specified by self.file_name exists."""
        pd = Pending('/tmp/foo.txt')
        mock_exists.return_value = True
        assert pd.exists()
        mock_exists.return_value = False
        assert not pd.exists()
        mock_exists.assert_called_with('/tmp/foo.txt')

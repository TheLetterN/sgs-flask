"""
Our main unit tests file.

Unit tests are a very good way to ensure that our project's behavior
remains consistent between changes, and that we will more easily be
able to narrow down causes of unexpected behaviors that may occur in
the future.

It is important to write tests for each method we write that does
anything that could have unexpected results. We don't need to test
Things that have well-known behavior, such as a simple assignment.

It is even more important that we run the tests before committing
any changes we make! They can be run via the command:
    manage.py test
"""

import unittest
from app import app


class TestCaseExample(unittest.TestCase):
    """This is just a set of examples of unit tests.
    
    Notes:
        All methods for testing must begin with "test_"

    Methods:
        setUp -- Perform actions needed to create testing environment.
        tearDown -- Remove/close anything only needed during testing.
        test_passing -- A test that always passes.
        test_failing -- A test that always fails.
    """

    def setUp(self):
        """Create test environment."""
        #Example:
        #set_database_location(testing_location)
        #create_database(testing_database)
        pass    #Do nothing

    def tearDown(self):
        """Destroy test environment."""
        #Example:
        #destroy_database(testing_database)
        pass

    def test_passing(self):
        """This test always passes."""
        assert True

    #The unittest.expectedFailure decorator tells unittest that a test should
    #fail, and therefore not count as a failure.
    @unittest.expectedFailure
    def test_failing(self):
        """This test always fails."""
        assert False

#If tests.py is run directly, it should automatically run all tests.
if __name__ == '__main__':
    unittest.main()

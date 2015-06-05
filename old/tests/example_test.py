"""This script is an example of how a unit test is structured."""

import unittest

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
        self.assertTrue(True)

    #The unittest.expectedFailure decorator tells unittest that a test should
    #fail, and therefore not count as a failure.
    @unittest.expectedFailure
    def test_failing(self):
        """This test always fails."""
        self.assertTrue(False)


#If tests.py is run directly, it should automatically run all tests.
if __name__ == '__main__':
    unittest.main()

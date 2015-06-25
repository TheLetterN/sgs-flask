import unittest
from app import create_app, db
from app.auth.models import User


class TestAuthRoutesWithDB(unittest.TestCase):
    """Tests routes in auth model which use the db."""
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.tc = self.app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_redirects_on_success(self):
        """Logging in successfully should cause a 302 redirect."""
        data = dict(
            username='AzureDiamond',
            password='hunter2',
            remember_me='true')
        user = User()
        user.name = data['username']
        user.password = data['password']
        user.email = 'gullible@bash.org'
        db.session.add(user)
        db.session.commit()
        retval = self.tc.post('/auth/login', data=data, follow_redirects=False)
        self.assertEqual(retval.status_code, 302)

if __name__ == '__main__':
    unittest.main()

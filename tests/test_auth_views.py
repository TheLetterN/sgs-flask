import unittest
from app import create_app, db
from app.auth.models import User


class TestAuthRoutes(unittest.TestCase):
    """Tests routes in the auth module."""
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
        """Successfully logging in should cause a 302 redirect."""
        data = dict(
            username='AzureDiamond',
            password='hunter2',
            remember_me=True)
        user = User()
        user.name = data['username']
        user.password = data['password']
        user.email = 'idiot@bash.org'
        db.session.add(user)
        db.session.commit()
        retval = self.tc.post('/auth/login', data=data, follow_redirects=False)
        self.assertEqual(retval.status_code, 302)

    def test_login_returns_valid_page(self):
        retval = self.tc.get('/auth/login')
        self.assertEqual(retval.status_code, 200)


if __name__ == '__main__':
    unittest.main()

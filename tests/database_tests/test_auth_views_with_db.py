import unittest
from datetime import datetime, timedelta
from flask import url_for
from app import create_app, db
from app.auth.models import Permission, User


class TestConfirmAccountWithDB(unittest.TestCase):
    """Test the confirm_account route in the auth module."""
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

    def test_confirm_account_confirms_account_with_valid_token(self):
        """User.confirmed is true if confirm_account given a valid token."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        self.assertFalse(user.confirmed)
        token = user.generate_account_confirmation_token()
        self.tc.get(url_for('auth.confirm_account', token=token))
        self.assertTrue(user.confirmed)

    def test_confirm_account_automatically_promotes_administrator(self):
        """Permission to manage users is granted if user email in admin list.

        The list is in <app>.config['ADMINISTRATORS']
        """
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        self.assertFalse(user.can(Permission.MANAGE_USERS))
        token = user.generate_account_confirmation_token()
        self.app.config['ADMINISTRATORS'].append(user.email)
        self.tc.get(url_for('auth.confirm_account', token=token))
        self.assertTrue(user.can(Permission.MANAGE_USERS))


class TestConfirmNewEmailWithDB(unittest.TestCase):
    """Test the confirm_new_email route in the auth module."""
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

    def test_confirm_new_email_with_bad_token(self):
        """confirm_new_email given a bad token redirects w/ error message."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            retval = tc.get('/auth/confirm_new_email/badtoken',
                            follow_redirects=True)
        self.assertTrue('Error: could not change email' in str(retval.data))

    def test_confirm_new_email_with_valid_token(self):
        """confirm_new_email sets new email address w/ valid token."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        new_email = 'azurediamond@bash.org'
        token = user.generate_new_email_token(new_email)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            tc.get(url_for('auth.confirm_new_email', token=token))
        user2 = User.query.get(user.id)
        self.assertEqual(new_email, user2.email)


class TestEditUserWithDB(unittest.TestCase):
    """Test edit_user route in the auth module."""
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

    def test_edit_user_changed_email(self):
        """edit_user should flash a success message if email is changed."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1='fool@bar.com',
                email2='fool@bar.com',
                current_password='hunter2')
            rv = tc.post('/auth/edit_user', data=data, follow_redirects=True)
        self.assertTrue('sent to fool@bar.com' in str(rv.data))

    def test_edit_user_changed_password(self):
        """edit_user should flash a success message if password is changed."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1=user.email,
                email2=user.email,
                new_password1='password1',
                new_password2='password1',
                current_password='hunter2')
            rv = tc.post('/auth/edit_user', data=data, follow_redirects=True)
        self.assertTrue('changed your password' in str(rv.data))

    def test_edit_user_no_changes(self):
        """edit_user should flash a message if no changes are made."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1=user.email,
                email2=user.email,
                current_password='hunter2')
            rv = tc.post('/auth/edit_user', data=data, follow_redirects=True)
        self.assertTrue('No changes have been made' in str(rv.data))


class TestLoginWithDB(unittest.TestCase):
    """Test login route in the auth module."""
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

    def test_login_bad_data(self):
        """login should flash an error message if login is incorrect."""
        rv = login('not', 'themama', tc=self.tc)
        self.assertTrue('Error: Login information' in str(rv.data))
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        rv2 = login(user.name, 'badpassword', tc=self.tc)
        self.assertTrue('Error: Login information' in str(rv2.data))
        rv3 = login('badusername', 'hunter2', tc=self.tc)
        self.assertTrue('Error: Login information' in str(rv3.data))

    def test_login_not_confirmed(self):
        """login should flash an error message if account isn't confirmed."""
        user = make_dummy_user()
        user.confirmed = False
        db.session.add(user)
        db.session.commit()
        rv = login(user.name, 'hunter2', tc=self.tc)
        self.assertTrue('Error: Account not confirmed!' in str(rv.data))

    def test_login_success(self):
        """login should flash a success message on success."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        rv = login(user.name, 'hunter2', tc=self.tc)
        self.assertTrue('You are now logged in' in str(rv.data))


class TestLogoutWithDB(unittest.TestCase):
    """Test logout route in the auth module."""
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

    def test_logout(self):
        """logout flashes a message telling the user they logged out."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/logout', follow_redirects=True)
        self.assertTrue('You have been logged out.' in str(rv.data))


class TestManageUserWithDB(unittest.TestCase):
    """Test manage_user route in the auth module."""
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

    @staticmethod
    def make_form_data(user,
                       email=None,
                       manage_users=None,
                       manage_seeds=None,
                       password=None,
                       username=None):
        """Create a dict containing data to submit to /auth/manage_user/<id>

        Note:
            All arguments except user should be set to the passed user's
            relevant data if no new values are supplied.

        Args:
            user (User): The user whose data is being edited in the test.
            email (str): A new email address, if any.
            manage_users (bool): Whether or not the user can manage users.
            manage_seeds (bool): Whether or not the user can manage the seeds
                                 database.
            password (str): A new password, if any.
            username (str): A new username, if any.

        Returns:
            dict: Data for a simulated POST to /auth/manage_user/<id>
        """
        data = dict()
        if email is not None:
            data['email1'] = email
            data['email2'] = email
        else:
            data['email1'] = user.email
            data['email2'] = user.email
        if manage_users is not None:
            if manage_users is True:
                data['manage_users'] = True
            elif manage_users is False:
                data['manage_users'] = None    # Unchecked box submits no data.
            else:
                raise ValueError('manage_users must be True, False, or None!')
        else:
            if user.can(Permission.MANAGE_USERS):
                data['manage_users'] = True
            else:
                data['manage_users'] = None
        if manage_seeds is not None:
            if manage_seeds is True:
                data['manage_seeds'] = True
            elif manage_seeds is False:
                data['manage_seeds'] = None
            else:
                raise ValueError('manage_seeds must be True, False, or None!')
        else:
            if user.can(Permission.MANAGE_SEEDS):
                data['manage_seeds'] = True
            else:
                data['manage_seeds'] = None
        if password is not None:
            data['password1'] = password
            data['password2'] = password
        else:
            data['password1'] = None
            data['password1'] = None
        if username is not None:
            data['username1'] = username
            data['username2'] = username
        else:
            data['username1'] = user.name
            data['username2'] = user.name
        return data

    def test_manage_user_change_email_address(self):
        """manage_user changes email address if new one not in use already."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        new_email = 'schmotgoy@bash.org'
        data = self.make_form_data(user, email=new_email)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            tc.post('/auth/manage_user/{0}'.format(user.id),
                    data=data,
                    follow_redirects=True)
            self.assertEqual(user.email, new_email)

    def test_manage_user_change_password(self):
        """Changing the user's password should flash a success message.

        It should flash a success message even if the password is the same as
        the old one, as we don't want to allow admins to try to guess passwords
        entered by the user.
        """
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data1 = self.make_form_data(user, password='hunter2')
            rv1 = tc.post('/auth/manage_user/{0}'.format(user.id),
                          data=data1,
                          follow_redirects=True)
            self.assertTrue('password has been changed' in str(rv1.data))
            data2 = self.make_form_data(user, password='hunter3')
            rv2 = tc.post('/auth/manage_user/{0}'.format(user.id),
                          data=data2,
                          follow_redirects=True)
            self.assertTrue('password has been changed' in str(rv2.data))

    def test_manage_user_change_username(self):
        """manage_user changes username if not in use already."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(user, username='BlueZirconia')
            tc.post('/auth/manage_user/{0}'.format(user.id),
                    data=data,
                    follow_redirects=True)
            self.assertEqual(user.name, 'BlueZirconia')

    def test_manage_user_current_user_lacks_permission(self):
        """manage_user aborts with a 403 error if user w/o permission visits.

        Note:
            This is actually a test for app.decorators.permission_required. it
            is just easier to test it this way than to try and make a mock
            setup for it!
        """
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/manage_user', follow_redirects=False)
            self.assertEqual(rv.status_code, 403)

    def test_manage_user_prevents_lockout(self):
        """Flash error if user tries to revoke their own MANAGE_USERS perm."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(user, manage_users=False)
            rv = tc.post('/auth/manage_user/{0}'.format(user.id),
                         data=data,
                         follow_redirects=True)
        self.assertTrue('Error: Please do not try to remove' in str(rv.data))

    def test_manage_user_prevents_change_to_email_of_other_user(self):
        """Flash an error if new email is in use by another user."""
        user = make_smart_user()
        db.session.add(user)
        cavy = make_guinea_pig()
        db.session.add(cavy)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, email=user.email)
            rv = tc.post('/auth/manage_user/{0}'.format(cavy.id),
                         data=data,
                         follow_redirects=True)
            self.assertTrue('Error: Email address already in' in str(rv.data))

    def test_manage_user_prevents_change_to_username_of_other_user(self):
        """Flash an error if new username is already used by another user."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        db.session.add(user)
        db.session.add(cavy)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, username=user.name)
            rv = tc.post('/auth/manage_user/{0}'.format(cavy.id),
                         data=data,
                         follow_redirects=True)
            self.assertTrue('Error: Username is already' in str(rv.data))

    def test_manage_user_no_changes(self):
        """manage_user flashes a message if no changes are made."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        data = self.make_form_data(user)
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post('/auth/manage_user/{0}'.format(user.id),
                         data=data,
                         follow_redirects=True)
        self.assertTrue('No changes made' in str(rv.data))

    def test_manage_user_no_user_id(self):
        """manage_user redirects to /auth/select_user if given no user_id."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/manage_user', follow_redirects=False)
            print(rv.data)
        self.assertTrue('/auth/select_user' in str(rv.location))

    def test_manage_user_no_user_with_user_id(self):
        """manage_user flashes an error if no matching user.id found in db."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/manage_user/999', follow_redirects=True)
        self.assertTrue('Error: No user exists with' in str(rv.data))

    def test_manage_user_update_permissions(self):
        """manage_user updates permissions if changes are submitted."""
        user = make_smart_user()
        db.session.add(user)
        cavy = make_guinea_pig()
        db.session.add(cavy)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            self.assertFalse(cavy.can(Permission.MANAGE_SEEDS))
            data1 = self.make_form_data(cavy, manage_seeds=True)
            tc.post('/auth/manage_user/{0}'.format(cavy.id),
                    data=data1,
                    follow_redirects=True)
            self.assertTrue(cavy.can(Permission.MANAGE_SEEDS))
            self.assertFalse(cavy.can(Permission.MANAGE_USERS))
            data2 = self.make_form_data(cavy,
                                        manage_users=True,
                                        manage_seeds=False)
            tc.post('/auth/manage_user/{0}'.format(cavy.id),
                    data=data2,
                    follow_redirects=True)
            self.assertTrue(cavy.can(Permission.MANAGE_USERS))
            self.assertFalse(cavy.can(Permission.MANAGE_SEEDS))

    def test_manage_user_user_id_not_integer(self):
        """manage_user flashes an error if user_id is not an integer."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/manage_user/3d', follow_redirects=True)
        self.assertTrue('Error: User id must be an integer!' in str(rv.data))


class TestRegisterWithDB(unittest.TestCase):
    """Test register route in the auth module."""
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

    def test_register_adds_user_to_database(self):
        """register adds user to db if form validates."""
        data = dict(
            email='gullible@bash.org',
            email2='gullible@bash.org',
            password='hunter2',
            password2='hunter2',
            username='AzureDiamond')
        self.tc.post('/auth/register', data=data, follow_redirects=True)
        user = User.query.filter_by(name='AzureDiamond').first()
        self.assertEqual(user.email, 'gullible@bash.org')

    def test_register_success_message(self):
        """register flashes a success message on successful submission."""
        data = dict(
            email='gullible@bash.org',
            email2='gullible@bash.org',
            password='hunter2',
            password2='hunter2',
            username='AzureDiamond')
        rv = self.tc.post('/auth/register', data=data, follow_redirects=True)
        self.assertTrue('A confirmation email has been sent' in str(rv.data))


class TestResendConfirmationWithDB(unittest.TestCase):
    """Test resend_confirmation route in the auth module."""
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

    def test_resend_confirmation_email_request_too_many(self):
        """Flash an error if too many requests have been made."""
        self.app.config['ERFP_MAX_REQUESTS'] = 10
        self.app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        time = datetime.utcnow() - timedelta(minutes=6)
        for i in range(0, 11):
            user.log_email_request('confirm account', time=time)
        db.session.add(user)
        db.session.commit()
        rv = self.tc.post('/auth/resend_confirmation',
                          data=dict(email=user.email),
                          follow_redirects=True)
        self.assertTrue('Error: Too many requests have been made' in
                        str(rv.data))

    def test_resend_confirmation_email_request_too_soon(self):
        """Flash an errror if request made too soon after previous one."""
        self.app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        user.log_email_request('confirm account')
        data = dict(email=user.email)
        rv = self.tc.post('/auth/resend_confirmation',
                          data=data,
                          follow_redirects=True)
        self.assertTrue('Error: A confirmation email has already been sent' in
                        str(rv.data))

    def test_resend_confirmation_logged_in_user(self):
        """resend_confirmation flashes an error if user is logged in.

        Since users can't log in without being confirmed, there's no point in
        letting them resend confirmation emails if they're logged in!
        """
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get('/auth/resend_confirmation',
                        follow_redirects=True)
            self.assertTrue('Error: Your account is already' in str(rv.data))

    def test_resend_confirmation_success_message(self):
        """resend_confirmation flashes a success message on successful sub."""
        user = make_dummy_user()
        user.confirmed = False
        db.session.add(user)
        db.session.commit()
        rv = self.tc.post('/auth/resend_confirmation',
                          data=dict(email=user.email),
                          follow_redirects=True)
        self.assertTrue('Confirmation email sent to' in str(rv.data))


class TestResetPasswordWithDB(unittest.TestCase):
    """Test reset_password route in the auth module."""
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

    def test_reset_password_email_not_in_db(self):
        """reset_password flashes an error message if email is not in db."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        token = user.generate_password_reset_token()
        data1 = dict(
            email='bad@address.com',
            password1='hunter3',
            password2='hunter3')
        rv1 = self.tc.post(url_for('auth.reset_password', token=token),
                           data=data1,
                           follow_redirects=True)
        self.assertTrue('Error: wrong email address!' in str(rv1.data))

    def test_reset_password_email_request_too_many(self):
        """Flash an error if too many requests have been made."""
        self.app.config['ERFP_MAX_REQUESTS'] = 10
        self.app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        time = datetime.utcnow() - timedelta(minutes=6)
        for i in range(0, 11):
            user.log_email_request('reset password', time=time)
        db.session.add(user)
        db.session.commit()
        rv = self.tc.post('/auth/reset_password',
                          data=dict(email=user.email),
                          follow_redirects=True)
        self.assertTrue('Error: Too many requests have been made to reset' in
                        str(rv.data))

    def test_reset_password_email_request_too_soon(self):
        """Flash an error if request made too soon after previous one."""
        self.app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        user.log_email_request('reset password')
        db.session.add(user)
        db.session.commit()
        rv = self.tc.post('/auth/reset_password',
                          data=dict(email=user.email),
                          follow_redirects=True)
        self.assertTrue('Error: A request to reset your password has' in
                        str(rv.data))

    def test_reset_password_resets_password(self):
        """reset_password resets the user's password with valid submission."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        data = dict(
            email=user.email,
            password1='hunter3',
            password2='hunter3')
        token = user.generate_password_reset_token()
        self.tc.post(url_for('auth.reset_password', token=token),
                     data=data,
                     follow_redirects=True)
        self.assertTrue(user.verify_password('hunter3'))

    def test_reset_password_success_message(self):
        """reset_password flashes success message on valid submission."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        data = dict(
            email=user.email,
            password1='hunter3',
            password2='hunter3')
        token = user.generate_password_reset_token()
        rv = self.tc.post(url_for('auth.reset_password', token=token),
                          data=data,
                          follow_redirects=True)
        self.assertTrue('New password set' in str(rv.data))

    def test_reset_password_wrong_email(self):
        """reset_password flashes and error if wrong user's email provided."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        token = user.generate_password_reset_token()
        user2 = User()
        user2.name = 'Ford Prefect'
        user2.set_password('knowwhereyourtowelis')
        user2.email = 'froody@h2g2.com'
        user2.confirmed = True
        db.session.add(user2)
        db.session.commit()
        data = dict(
            email=user2.email,
            password1='heartofgold',
            password2='heartofgold')
        rv = self.tc.post(url_for('auth.reset_password', token=token),
                          data=data,
                          follow_redirects=True)
        self.assertTrue('Error: Given token is invalid' in str(rv.data))

    def test_reset_password_request_success_message(self):
        """reset_password_request flashes a success message on success."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        data = dict(email=user.email)
        rv = self.tc.post('/auth/reset_password',
                          data=data,
                          follow_redirects=True)
        self.assertTrue('An email with instructions' in str(rv.data))


class TestSelectUserWithDB(unittest.TestCase):
    """Test select_user route in the auth module."""
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

    def test_select_user_success_redirect(self):
        """select_user should redirect to target_route if successful."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with self.app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = self.tc.post(
                '/auth/select_user?target_route=auth.manage_user',
                data=dict(select_user=1),
                follow_redirects=False)
            self.assertEqual(rv.location, url_for('auth.manage_user',
                                                  user_id=1,
                                                  _external=True))


def login(username, password, tc):
    """Log a user in to the given test client.

    Args:
        username (str): username of account to log in.
        password (str): password for account to log in.
        tc (flask.testing.FlaskClient): Test client to log in to.
    returns:
        flask.wrappers.Response: Response object (generated web page and
                                 related data) from the login POST.
    """
    return tc.post('/auth/login', data=dict(
        login=username,
        password=password
        ), follow_redirects=True)


def make_dummy_user():
    """Create a basic dummy user for testing.

    Returns:
        User: A basic user with no confirmed account or privileges.
    """
    user = User()
    user.name = 'AzureDiamond'
    user.set_password('hunter2')
    user.email = 'gullible@bash.org'
    return user


def make_guinea_pig():
    """Create an additional dummy user when more than one user is needed.

    Returns:
        User: A basic user with a confirmed account but no privileges.
    """
    cavy = User()   # Cavy is another name for guinea pig.
    cavy.email = 'squeals@rodents.com'
    cavy.name = 'Mister Squeals'
    cavy.set_password('food')
    cavy.confirmed = True
    return cavy


def make_smart_user():
    """Create a confirmed user with permission to manage users.

    Returns:
        User: An admin/mod user w/ confirmed account and MANAGE_USERS perm.
    """
    user = make_dummy_user()
    user.confirmed = True
    user.permissions = 0
    user.grant_permission(Permission.MANAGE_USERS)
    return user


if __name__ == '__main__':
    unittest.main()

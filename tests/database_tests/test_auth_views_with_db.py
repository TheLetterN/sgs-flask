# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from flask import url_for
from app.auth.models import Permission, User
from tests.conftest import app, db  # noqa


class TestConfirmAccountWithDB:
    """Test the confirm_account route in the auth module."""
    def test_confirm_account_confirms_account_with_valid_token(self, app, db):
        """User.confirmed is true if confirm_account given a valid token."""
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        assert not user.confirmed
        token = user.generate_account_confirmation_token()
        with app.test_client() as tc:
            tc.get(url_for('auth.confirm_account', token=token))
        assert user.confirmed

    def test_confirm_account_automatically_promotes_administrator(self,
                                                                  app,
                                                                  db):
        """Permission to manage users is granted if user email in admin list.

        The list is in <app>.config['ADMINISTRATORS']
        """
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        assert not user.can(Permission.MANAGE_USERS)
        token = user.generate_account_confirmation_token()
        app.config['ADMINISTRATORS'].append(user.email)
        with app.test_client() as tc:
            tc.get(url_for('auth.confirm_account', token=token))
        assert user.can(Permission.MANAGE_USERS)


class TestDeleteUserWithDB:
    """Test the confirm_account route in the auth module."""
    def test_delete_user_delete_self(self, app, db):
        """Flash an error when user tries to delete their own account."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.delete_user', uid=user.id),
                        follow_redirects=True)
        assert 'Error: You cannot delete yourself!' in str(rv.data)

    def test_delete_user_malformed_uid(self, app, db):
        """Flash an error when uid is not an integer."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.delete_user', uid='frogs'),
                        follow_redirects=True)
        assert 'Error: Invalid or malformed user ID!' in str(rv.data)

    def test_delete_user_nonexistent(self, app, db):
        """Flash an error if user does not exist."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.delete_user', uid=42),
                        follow_redirects=True)
        assert 'Error: No user exists with that ID number!' in str(rv.data)

    def test_delete_user_renders_page(self, app, db):
        """The page for deleting a user is presented if uid is valid."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        db.session.add(cavy)
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.delete_user', uid=cavy.id),
                        follow_redirects=True)
        assert 'THIS CANNOT BE UNDONE' in str(rv.data)

    def test_delete_user_success(self, app, db):
        """Delete a user and flash a message if given valid form data."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        db.session.add(user)
        db.session.add(cavy)
        db.session.commit()
        assert User.query.count() == 2
        assert User.query.filter_by(name='Mister Squeals').first() is not None
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('auth.delete_user', uid=cavy.id),
                         data=dict(confirmation='THIS CANNOT BE UNDONE',
                                   password='hunter2'),
                         follow_redirects=True)
        assert 'Mister Squeals has been deleted!' in str(rv.data)
        assert User.query.count() == 1
        assert User.query.filter_by(name='Mister Squeals').first() is None


class TestConfirmNewEmailWithDB:
    """Test the confirm_new_email route in the auth module."""
    def test_confirm_new_email_with_bad_token(self, app, db):
        """confirm_new_email given a bad token redirects w/ error message."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.confirm_new_email',
                                token='badtoken'),
                        follow_redirects=True)
        assert 'Error: could not change email' in str(rv.data)

    def test_confirm_new_email_with_valid_token(self, app, db):
        """confirm_new_email sets new email address w/ valid token."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        new_email = 'azurediamond@bash.org'
        token = user.generate_new_email_token(new_email)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            tc.get(url_for('auth.confirm_new_email', token=token))
        user2 = User.query.get(user.id)
        assert new_email == user2.email


class TestEditUserWithDB:
    """Test edit_user route in the auth module."""
    def test_edit_user_changed_email(self, app, db):
        """edit_user should flash a success message if email is changed."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1='fool@bar.com',
                email2='fool@bar.com',
                current_password='hunter2')
            rv = tc.post(url_for('auth.edit_user'),
                         data=data,
                         follow_redirects=True)
        assert 'sent to fool@bar.com' in str(rv.data)

    def test_edit_user_changed_password(self, app, db):
        """edit_user should flash a success message if password is changed."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1=user.email,
                email2=user.email,
                new_password1='password1',
                new_password2='password1',
                current_password='hunter2')
            rv = tc.post(url_for('auth.edit_user'),
                         data=data,
                         follow_redirects=True)
        assert 'changed your password' in str(rv.data)

    def test_edit_user_no_changes(self, app, db):
        """edit_user should flash a message if no changes are made."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = dict(
                email1=user.email,
                email2=user.email,
                current_password='hunter2')
            rv = tc.post(url_for('auth.edit_user'),
                         data=data,
                         follow_redirects=True)
        assert 'No changes have been made' in str(rv.data)


class TestLoginWithDB:
    """Test login route in the auth module."""
    def test_login_bad_data(self, app, db):
        """login should flash an error message if login is incorrect."""
        with app.test_client() as tc:
            rv = login('not', 'themama', tc=tc)
        assert 'Error: Login information' in str(rv.data)
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv2 = login(user.name, 'badpassword', tc=tc)
        assert 'Error: Login information' in str(rv2.data)
        with app.test_client() as tc:
            rv3 = login('badusername', 'hunter2', tc=tc)
        assert 'Error: Login information' in str(rv3.data)

    def test_login_not_confirmed(self, app, db):
        """login should flash an error message if account isn't confirmed."""
        user = make_dummy_user()
        user.confirmed = False
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = login(user.name, 'hunter2', tc=tc)
        assert 'Error: Account not confirmed!' in str(rv.data)

    def test_login_success(self, app, db):
        """login should flash a success message on success."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = login(user.name, 'hunter2', tc=tc)
        assert 'You are now logged in' in str(rv.data)


class TestLogoutWithDB:
    """Test logout route in the auth module."""
    def test_logout(self, app, db):
        """logout flashes a message telling the user they logged out."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.logout'), follow_redirects=True)
        assert 'You have been logged out.' in str(rv.data)


class TestManageUserWithDB:
    """Test manage_user route in the auth module."""
    @staticmethod
    def make_form_data(user,
                       confirmed=None,
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
            confirmed (bool): Whether or not the account should be confirmed.
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
        if confirmed is not None:
            if confirmed:
                data['confirmed'] = True
            elif not confirmed:
                data['confirmed'] = None    # Unchecked box submits no data.
            else:
                raise ValueError('confirmed bust be True, False, or None!')
        else:
            if user.confirmed:
                data['confirmed'] = True
            else:
                data['confirmed'] = None
        data['email1'] = email
        data['email2'] = email
        if manage_users is not None:
            if manage_users:
                data['manage_users'] = True
            elif not manage_users:
                data['manage_users'] = None
            else:
                raise ValueError('manage_users must be True, False, or None!')
        else:
            if user.can(Permission.MANAGE_USERS):
                data['manage_users'] = True
            else:
                data['manage_users'] = None
        if manage_seeds is not None:
            if manage_seeds:
                data['manage_seeds'] = True
            elif not manage_seeds:
                data['manage_seeds'] = None
            else:
                raise ValueError('manage_seeds must be True, False, or None!')
        else:
            if user.can(Permission.MANAGE_SEEDS):
                data['manage_seeds'] = True
            else:
                data['manage_seeds'] = None
        data['password1'] = password
        data['password2'] = password
        data['username1'] = username
        data['username2'] = username
        return data

    def test_manage_user_change_email_address(self, app, db):
        """manage_user changes email address if new one not in use already."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        new_email = 'schmotgoy@bash.org'
        data = self.make_form_data(user, email=new_email)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            tc.post(url_for('auth.manage_user', user_id=user.id),
                    data=data,
                    follow_redirects=True)
        assert user.email == new_email

    def test_manage_user_change_password(self, app, db):
        """Changing the user's password should flash a success message.

        It should flash a success message even if the password is the same as
        the old one, as we don't want to allow admins to try to guess passwords
        entered by the user.
        """
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data1 = self.make_form_data(user, password='hunter2')
            rv1 = tc.post(url_for('auth.manage_user', user_id=user.id),
                          data=data1,
                          follow_redirects=True)
            assert 'password has been changed' in str(rv1.data)
            data2 = self.make_form_data(user, password='hunter3')
            rv2 = tc.post(url_for('auth.manage_user', user_id=user.id),
                          data=data2,
                          follow_redirects=True)
            assert 'password has been changed' in str(rv2.data)

    def test_manage_user_change_username(self, app, db):
        """manage_user changes username if not in use already."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(user, username='BlueZirconia')
            tc.post(url_for('auth.manage_user', user_id=user.id),
                    data=data,
                    follow_redirects=True)
        assert user.name == 'BlueZirconia'

    def test_manage_user_confirmed_false_to_true(self, app, db):
        """Set User.confirmed to True if it was false and box is checked."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        cavy.confirmed = False
        db.session.add(user)
        db.session.add(cavy)
        db.session.commit()
        assert not cavy.confirmed
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, confirmed=True)
            tc.post(url_for('auth.manage_user', user_id=cavy.id),
                    data=data,
                    follow_redirects=True)
        assert cavy.confirmed

    def test_manage_user_confirmed_true_to_false(self, app, db):
        """Set User.confirmed to False if it was true and box is unchecked."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        cavy.confirmed = True
        db.session.add(user)
        db.session.add(cavy)
        db.session.commit()
        assert cavy.confirmed
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, confirmed=False)
            tc.post(url_for('auth.manage_user', user_id=cavy.id),
                    data=data,
                    follow_redirects=True)
        assert not cavy.confirmed

    def test_manage_user_current_user_lacks_permission(self, app, db):
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
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.manage_user'), follow_redirects=False)
        assert rv.status_code == 403

    def test_manage_user_prevents_confirmed_lockout(self, app, db):
        """Flash error if user tries to revoke own account confirmation."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(user, confirmed=False)
            rv = tc.post(url_for('auth.manage_user', user_id=user.id),
                         data=data,
                         follow_redirects=True)
        assert user.confirmed
        assert 'Error: You cannot revoke your own' in str(rv.data)

    def test_manage_user_prevents_manage_users_lockout(self, app, db):
        """Flash error if user tries to revoke their own MANAGE_USERS perm."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(user, manage_users=False)
            rv = tc.post(url_for('auth.manage_user', user_id=user.id),
                         data=data,
                         follow_redirects=True)
        assert user.can(Permission.MANAGE_USERS)
        assert 'Error: Please do not try to remove' in str(rv.data)

    def test_manage_user_prevents_change_to_email_of_other_user(self, app, db):
        """Flash an error if new email is in use by another user."""
        user = make_smart_user()
        db.session.add(user)
        cavy = make_guinea_pig()
        db.session.add(cavy)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, email=user.email)
            rv = tc.post(url_for('auth.manage_user', user_id=cavy.id),
                         data=data,
                         follow_redirects=True)
        assert 'Error: Email address already in' in str(rv.data)

    def test_manage_user_prevents_change_to_username_of_other_user(self,
                                                                   app,
                                                                   db):
        """Flash an error if new username is already used by another user."""
        user = make_smart_user()
        cavy = make_guinea_pig()
        db.session.add(user)
        db.session.add(cavy)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            data = self.make_form_data(cavy, username=user.name)
            rv = tc.post(url_for('auth.manage_user', user_id=cavy.id),
                         data=data,
                         follow_redirects=True)
        assert 'Error: Username is already' in str(rv.data)

    def test_manage_user_no_changes(self, app, db):
        """manage_user flashes a message if no changes are made."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        data = self.make_form_data(user)
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('auth.manage_user', user_id=user.id),
                         data=data,
                         follow_redirects=True)
        assert 'No changes made' in str(rv.data)

    def test_manage_user_no_user_id(self, app, db):
        """manage_user redirects to /auth/select_user if given no user_id."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.manage_user'), follow_redirects=False)
            print(rv.data)
        assert '/auth/select_user' in str(rv.location)

    def test_manage_user_no_user_with_user_id(self, app, db):
        """manage_user flashes an error if no matching user.id found in db."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.manage_user', user_id=999),
                        follow_redirects=True)
        assert 'Error: No user exists with' in str(rv.data)

    def test_manage_user_update_permissions(self, app, db):
        """manage_user updates permissions if changes are submitted."""
        user = make_smart_user()
        db.session.add(user)
        cavy = make_guinea_pig()
        db.session.add(cavy)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            assert not cavy.can(Permission.MANAGE_SEEDS)
            data1 = self.make_form_data(cavy, manage_seeds=True)
            tc.post(url_for('auth.manage_user', user_id=cavy.id),
                    data=data1,
                    follow_redirects=True)
            assert cavy.can(Permission.MANAGE_SEEDS)
            assert not cavy.can(Permission.MANAGE_USERS)
            data2 = self.make_form_data(cavy,
                                        manage_users=True,
                                        manage_seeds=False)
            tc.post(url_for('auth.manage_user', user_id=cavy.id),
                    data=data2,
                    follow_redirects=True)
        assert cavy.can(Permission.MANAGE_USERS)
        assert not cavy.can(Permission.MANAGE_SEEDS)

    def test_manage_user_user_id_not_integer(self, app, db):
        """manage_user flashes an error if user_id is not an integer."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.manage_user', user_id='3d'),
                        follow_redirects=True)
        assert 'Error: User id must be an integer!' in str(rv.data)


class TestRegisterWithDB:
    """Test register route in the auth module."""
    def test_register_adds_user_to_database(self, app, db):
        """register adds user to db if form validates."""
        data = dict(
            email='gullible@bash.org',
            email2='gullible@bash.org',
            password='hunter2',
            password2='hunter2',
            username='AzureDiamond')
        with app.test_client() as tc:
            tc.post(url_for('auth.register'),
                    data=data,
                    follow_redirects=True)
        user = User.query.filter_by(name='AzureDiamond').first()
        assert user.email == 'gullible@bash.org'

    def test_register_success_message(self, app, db):
        """register flashes a success message on successful submission."""
        data = dict(
            email='gullible@bash.org',
            email2='gullible@bash.org',
            password='hunter2',
            password2='hunter2',
            username='AzureDiamond')
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.register'),
                         data=data,
                         follow_redirects=True)
        assert 'A confirmation email has been sent' in str(rv.data)


class TestResendConfirmationWithDB:
    """Test resend_confirmation route in the auth module."""
    def test_resend_confirmation_email_request_too_many(self, app, db):
        """Flash an error if too many requests have been made."""
        app.config['ERFP_MAX_REQUESTS'] = 10
        app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        time = datetime.utcnow() - timedelta(minutes=6)
        for i in range(0, 11):
            user.log_email_request('confirm account', time=time)
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.resend_confirmation'),
                         data=dict(email=user.email),
                         follow_redirects=True)
        assert 'Error: Too many requests have been made' in str(rv.data)

    def test_resend_confirmation_email_request_too_soon(self, app, db):
        """Flash an errror if request made too soon after previous one."""
        app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        db.session.add(user)
        db.session.commit()
        user.log_email_request('confirm account')
        data = dict(email=user.email)
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.resend_confirmation'),
                         data=data,
                         follow_redirects=True)
        assert 'Error: A confirmation email has already been sent' in\
            str(rv.data)

    def test_resend_confirmation_logged_in_user(self, app, db):
        """resend_confirmation flashes an error if user is logged in.

        Since users can't log in without being confirmed, there's no point in
        letting them resend confirmation emails if they're logged in!
        """
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.get(url_for('auth.resend_confirmation'),
                        follow_redirects=True)
        assert 'Error: Your account is already' in str(rv.data)

    def test_resend_confirmation_success_message(self, app, db):
        """resend_confirmation flashes a success message on successful sub."""
        user = make_dummy_user()
        user.confirmed = False
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.resend_confirmation'),
                         data=dict(email=user.email),
                         follow_redirects=True)
        assert 'Confirmation email sent to' in str(rv.data)


class TestResetPasswordWithDB:
    """Test reset_password route in the auth module."""
    def test_reset_password_email_not_in_db(self, app, db):
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
        with app.test_client() as tc:
            rv1 = tc.post(url_for('auth.reset_password', token=token),
                          data=data1,
                          follow_redirects=True)
        assert 'Error: wrong email address!' in str(rv1.data)

    def test_reset_password_resets_password(self, app, db):
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
        with app.test_client() as tc:
            tc.post(url_for('auth.reset_password', token=token),
                    data=data,
                    follow_redirects=True)
        assert user.verify_password('hunter3')

    def test_reset_password_success_message(self, app, db):
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
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.reset_password', token=token),
                         data=data,
                         follow_redirects=True)
        assert 'New password set' in str(rv.data)

    def test_reset_password_wrong_email(self, app, db):
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
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.reset_password', token=token),
                         data=data,
                         follow_redirects=True)
        assert 'Error: Given token is invalid' in str(rv.data)


class TestResetPasswordRequestWithDB:
    """Test reset_password_request route in the auth module."""
    def test_reset_password_request_email_request_too_many(self, app, db):
        """Flash an error if too many requests have been made."""
        app.config['ERFP_MAX_REQUESTS'] = 10
        app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        time = datetime.utcnow() - timedelta(minutes=6)
        for i in range(0, 11):
            user.log_email_request('reset password', time=time)
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.reset_password_request'),
                         data=dict(email=user.email),
                         follow_redirects=True)
        assert 'Error: Too many requests have been made to reset' in\
            str(rv.data)

    def test_reset_password_request_email_request_too_soon(self, app, db):
        """Flash an error if request made too soon after previous one."""
        app.config['ERFP_MINUTES_BETWEEN_REQUESTS'] = 5
        user = make_dummy_user()
        user.log_email_request('reset password')
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.reset_password_request'),
                         data=dict(email=user.email),
                         follow_redirects=True)
        assert 'Error: A request to reset your password has' in str(rv.data)

    def test_reset_password_request_success_message(self, app, db):
        """reset_password_request flashes a success message on success."""
        user = make_dummy_user()
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        data = dict(email=user.email)
        with app.test_client() as tc:
            rv = tc.post(url_for('auth.reset_password_request'),
                         data=data,
                         follow_redirects=True)
        assert 'An email with instructions' in str(rv.data)


class TestSelectUserWithDB:
    """Test select_user route in the auth module."""
    def test_select_user_success_redirect(self, app, db):
        """select_user should redirect to target_route if successful."""
        user = make_smart_user()
        db.session.add(user)
        db.session.commit()
        with app.test_client() as tc:
            login(user.name, 'hunter2', tc=tc)
            rv = tc.post(url_for('auth.select_user',
                                 target_route='auth.manage_user'),
                         data=dict(select_user=1),
                         follow_redirects=False)
            assert rv.location == url_for('auth.manage_user',
                                          user_id=1,
                                          _external=True)


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
    return tc.post(url_for('auth.login'), data=dict(login=username,
                                                    password=password),
                   follow_redirects=True)


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

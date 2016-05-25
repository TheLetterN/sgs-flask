# This file is part of SGS-Flask.

# SGS-Flask is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SGS-Flask is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Copyright Swallowtail Garden Seeds, Inc


from flask import (
    current_app,
    flash, Markup,
    redirect,
    render_template,
    request,
    url_for
)
from flask.ext.login import (
    current_user,
    login_required,
    login_user,
    logout_user
)
from app import db, Permission
from app.decorators import permission_required
from . import auth
from .forms import (
    DeleteUserForm,
    EditUserForm,
    ManageUserForm,
    LoginForm,
    RegistrationForm,
    ResendConfirmationForm,
    ResetPasswordForm,
    ResetPasswordRequestForm,
    SelectUserForm
)
from .models import get_user_from_confirmation_token, User


@auth.route('/confirm_account/<token>')
@auth.route('/confirm_account')
def confirm_account(token=None):
    """Get an account confirmation token and confirm account if it's valid.

    Args:
        token (str): An encrypted token used for account verification.

    Returns:
        function: redirect to auth.resend_confirmation if confirmation fails.
        function: redirect to auth.login if confirmation succeeds.
    """
    error_instructions = ('Please try again, or use the form below to'
                          ' receive a new confirmation token:')
    if token is None:
        return redirect(url_for('auth.resend_confirmation'))
    else:
        try:
            user = get_user_from_confirmation_token(token)
            if user.confirm_account(token):
                user.confirmed = True
                if user.email in current_app.config['ADMINISTRATORS']:
                    user.grant_permission(Permission.MANAGE_USERS)
                db.session.add(user)
                db.session.commit()
                flash('Account confirmed, '
                      '{0} you may now log in.'.format(user.name))
                return redirect(url_for('auth.login'))
            else:  # pragma: no cover
                # This is here just in case, but I'm pretty sure it will never
                # be run, as any condition that causes User.confirm_account
                # to return false also causes get_user_from_confirmation_token
                # to raise an exception. -N
                flash('Error: Account could not be confirmed.'
                      ' {0}'.format(error_instructions))
                return redirect(url_for('auth.resend_confirmation'))
        except BaseException as e:
            flash('Error: {0} {1}'.format(str(e), error_instructions))
            return redirect(url_for('auth.resend_confirmation'))


@auth.route('/confirm_new_email/<token>')
@login_required
def confirm_new_email(token):
    """Get a new email confirmation token and set new email if it's valid.

    Args:
        token (str): Encrypted token containing new email address and user.id.

    Returns:
        function: Redirect to main.index on successful confirmation.
        function: Redirect to auth.edit_user if confirmation fails.
    """
    if current_user.confirm_new_email(token):
        db.session.add(current_user)
        db.session.commit()
        flash('Your email address has been changed to: ' +
              '{0}'.format(current_user.email))
        return redirect(url_for('main.index'))
    else:
        flash('Error: could not change email address due to bad ' +
              'confirmation token. Please try again using the form below:')
        return redirect(url_for('auth.edit_user'))


@auth.route('/delete_user/<uid>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def delete_user(uid=None):
    """Allow a user with MANAGE_USERS permission to delete another user.

    Args:
        uid (int): The id number of a user in the database.

    Returns:
        function: Redirect to auth.manage_user with error message if active
                  user tries to delete their own account.
        function: Redirect to auth.manage_user with error message if uid is
                  not an integer.
        function: Redirect to auth.manage_user with error message if no user
                  exists with the id number given.
        function: Redirect to auth.manage_user with success message if user is
                  deleted successfully.
        function: Render auth/delete_user.html template if uid is valid and no
                  form data has been submitted.
    """
    try:
        if int(uid) == current_user.id:
            flash('Error: You cannot delete yourself! If you really wish to ' +
                  'have your account deleted, please ask another ' +
                  'administrator.')
            return redirect(url_for('auth.manage_user'))
    except:
        flash('Error: Invalid or malformed user ID!')
        return redirect(url_for('auth.manage_user'))
    user = User.query.get(uid)
    if user is None:
        flash('Error: No user exists with that ID number!')
        return redirect(url_for('auth.manage_user'))
    form = DeleteUserForm()
    if form.validate_on_submit():
        # flash message first so we can use user data in it.
        flash('User {0}: {1} has been deleted!'.format(user.id, user.name))
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('auth.manage_user'))
    return render_template('auth/delete_user.html',
                           form=form,
                           user=user)


@auth.route('/edit_user', methods=['GET', 'POST'])
@login_required
def edit_user():
    """Allow user to edit their account information.

    Returns:
        function: Redirect to main.index if user is edited successfully.
        function: Redirect to auth.edit_user if form is submitted with no
                  changes to user data.
        function: Render the template auth/edit_user.html if no form data is
                  received.
    """
    form = EditUserForm()
    if form.validate_on_submit():
        user_edited = False
        try:
            if form.email1.data is not None and len(form.email1.data) > 0 and \
                    form.email1.data != current_user.email:
                if not current_app.config['TESTING']:  # pragma: no cover
                    current_user.send_new_email_confirmation(form.email1.data)
                flash('A confirmation email has been sent to ' +
                      '{0}.'.format(form.email1.data) + ' Please check your ' +
                      'email for further instructions.')
                user_edited = True
            if form.new_password1.data is not None and \
                    len(form.new_password1.data) > 0:
                current_user.set_password(form.new_password1.data)
                db.session.add(current_user)
                db.session.commit()
                flash('You have successfully changed your password!')
                user_edited = True
        except TypeError:  # pragma: no cover
            # form.email1.data and form.new_password.data must be strings
            # if we are to use them, so we can safely do nothing if len()
            # raises a TypeError.
            pass
        if user_edited:
            return redirect(url_for('main.index'))
        else:
            flash('No changes have been made to your account.')
            return redirect(url_for('auth.edit_user'))
    return render_template('auth/edit_user.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Allow registered, confirmed users to log in.

    Request Args:
        next (str): The location of the page to return to after logging in.

    Returns:
        function: On successful login, redirect to page specified by next, or
                  main.index if no page is specified by next.
        function: Redirect to auth.resend_confirmation if user not confirmed.
        function: Redirect to auth.login if username or password is incorrect.
        function: Render template auth/login.html if no form data is received.
    """
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter((User.name == form.login.data) |
                                 (User.email == form.login.data)).first()
        if user is not None and user.verify_password(form.password.data):
            if user.confirmed:
                remember = False
                if form.remember_me.data:  # pragma: no cover
                    remember = True
                if(login_user(user, remember=remember)):
                    flash('You are now logged in, {0}.'.format(user.name))
                    return redirect(request.args.get('next') or
                                    url_for('main.index'))
            else:
                flash('Error: Account not confirmed! Please check your email, '
                      'or use the form below to get a new confirmation email.')
                return redirect(url_for('auth.resend_confirmation'))
        else:
            reset_url = Markup(
                '<a href="{0}'.format(url_for('auth.reset_password_request')) +
                '">Click here if you forgot your password</a>')
            flash('Error: Login information is incorrect! ' + reset_url + '.')
            return redirect(url_for('auth.login', next=request.args.get('next')))
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    """Log out the user if they visit this view while logged in.

    Returns:
        function: After logout, redirect to page specified by next, or
                  main.index if no page specified by next.
    """
    logout_user()
    flash('You have been logged out.')
    return redirect(request.values.get('next') or url_for('main.index'))


@auth.route('/manage_user', methods=['GET', 'POST'])
@auth.route('/manage_user/<user_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def manage_user(user_id=None):
    """Allow user w/ the MANAGE_USERS permission to edit other users' data.

    Args:
        user_id (int): id of user to manage data of.

    Returns:
        function: Redirect to auth.select_user with auth.manage_user as
                  target_route if user_id is missing.
        function: Redirect to auth.select_user with auth.manage_user as
                  target_route if user_id is not an integer.
        function: Redirect to auth.select_user with auth.manage_user as
                  target_route if user_id does not correspond to an existing
                  user.
        function: Redirect to auth.select_user with auth.manage_user as
                  target_route if current user attempts to revoke their own
                  MANAGE_USERS permission.
        function: Redirect to auth.manage_user if no changes were made to
                  the user.
        function: Render template /auth/manage_user.html if no form data is
                  received.
    """
    if user_id is None:
        return redirect(url_for('auth.select_user',
                                target_route='auth.manage_user'))
    if not user_id.isdigit():
        flash('Error: User id must be an integer! Please select a user:')
        return redirect(url_for('auth.select_user',
                                target_route='auth.manage_user'))
    user = User.query.get(user_id)
    if user is None:
        flash('Error: No user exists with that id number!')
        return redirect(url_for('auth.select_user',
                                target_route='auth.manage_user'))
    form = ManageUserForm()
    if form.validate_on_submit():
        user_info_changed = False
        if not user.confirmed and form.confirmed.data:
            flash('{0}\'s account is now confirmed.'.format(user.name))
            user.confirmed = True
            user_info_changed = True
        if user.confirmed and not form.confirmed.data:
            if current_user.id == user.id:
                flash('Error: You cannot revoke your own account\'s' +
                      ' confirmed status! If you really wish to do this, ' +
                      ' please ask another administrator to do it for you.')
            else:
                flash('{0}\'s account is no'.format(user.name) +
                      ' longer confirmed.')
                user.confirmed = False
                user_info_changed = True
        if form.email1.data is not None and len(form.email1.data) > 0 and \
                form.email1.data != user.email:
            if User.query.filter_by(email=form.email1.data).first() is None:
                user.email = form.email1.data
                flash('{0}\'s email address'.format(user.name) +
                      ' changed to: {0}'.format(form.email1.data))
                user_info_changed = True
            else:
                flash('Error: Email address already in use by another user!')
        if form.password1.data is not None and len(form.password1.data) > 0:
            if not user.verify_password(form.password1.data):
                # Just in case an admin tries to guess a password created by
                # the user for nefarious purposes, even though they'd have to
                # get it right on the first try to know they got it right.
                user.set_password(form.password1.data)
            flash('{0}\'s password has been changed.'.format(user.name))
            user_info_changed = True
        if form.username1.data is not None and \
                len(form.username1.data) > 0 and \
                form.username1.data != user.name:
            if User.query.filter_by(name=form.username1.data).first() is \
                    None:
                flash('{0}\'s username'.format(user.name) +
                      ' changed to: {0}.'.format(form.username1.data))
                user.name = form.username1.data
                user_info_changed = True
            else:
                flash('Error: Username is already in use by someone else!')
        if not form.manage_users.data and user.id == current_user.id:
            flash('Error: Please do not try to remove permission to manage'
                  ' users from yourself! If you really need the permission'
                  ' revoked, ask another administrator to do it.')
            return redirect(url_for('auth.select_user',
                                    target_route='auth.manage_user'))
        if (update_permission(user,
                              Permission.MANAGE_USERS,
                              form.manage_users.data,
                              'manage users')):
            user_info_changed = True
        if (update_permission(user,
                              Permission.MANAGE_SEEDS,
                              form.manage_seeds.data,
                              'manage seeds')):
            user_info_changed = True
        if user_info_changed:
            db.session.add(user)
            db.session.commit()
        else:
            flash('No changes made to {0}\'s account.'.format(user.name))
        return redirect(url_for('auth.manage_user', user_id=user_id))
    # Populate form with existing data:
    if user.confirmed:
        form.confirmed.data = True
    if user.can(Permission.MANAGE_USERS):
        form.manage_users.data = True
    if user.can(Permission.MANAGE_SEEDS):
        form.manage_seeds.data = True
    return render_template('auth/manage_user.html',
                           form=form,
                           user=user)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Allow a new user to create an account.

    Returns:
        function: Redirect to auth.login on successful registration.
        function: Render template auth/register.html if no form data received.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.email = form.email.data
        user.name = form.username.data
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        if not current_app.config['TESTING']:  # pragma: no cover
            user.send_account_confirmation_email()
        flash('A confirmation email has been sent to ' + form.email.data +
              ', please check your email for further instructions.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/resend_confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    """Send a new account confirmation email.

    Returns:
        function: Redirect to main.index with an error message if user is
                  already logged in, as that means their account does not need
                  to be confirmed.
        function: Redirect to main.index with an error message if form
                  validates despite the user already being confirmed. (This
                  should not happen, so it is unlikely this return will ever
                  occur.)
        function: Redirect to main.index after sending confirmation email.
        function: Render template auth.resend_confirmation.html if no form
                  data received.
    """
    if not current_user.is_anonymous:
        flash('Error: Your account is already confirmed!')
        return redirect(url_for('main.index'))
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.confirmed:  # pragma: no cover
            # This is here just in case; it should never be needed, as the form
            # will not validate if the user is already confirmed.
            flash('Error: Account already confirmed!')
            return redirect(url_for('main.index'))
        if user.email_request_too_soon('confirm account'):
            mbr = current_app.config['ERFP_MINUTES_BETWEEN_REQUESTS']
            flash('Error: A confirmation email has already been sent' +
                  ' within the last {0} minutes.'.format(mbr) +
                  ' If you did not recieve it, it may have been marked as' +
                  ' spam, so please check your spam folder/filter, and try' +
                  ' again in {0} minutes if needed.'.format(mbr) +
                  ' If the problem persists or you would like help, please ' +
                  support_mailto_address('contact support',
                                         'Trouble Confirming Account') + '.')
            return redirect(url_for('main.index'))
        if user.email_request_too_many('confirm account'):
            flash('Error: Too many requests have been made to resend a' +
                  ' confirmation email to this address. For your protection,' +
                  ' we have temporarily blocked all requests to send a' +
                  ' confirmation email to this account. We apologize for' +
                  ' the inconvenience, please ' +
                  support_mailto_address('contact support',
                                         'Trouble Confirming Account') +
                  ' for help confirming your account.')
            return redirect(url_for('main.index'))
        if not current_app.config['TESTING']:  # pragma: no cover
            user.send_account_confirmation_email()
        user.log_email_request('confirm account')
        flash('Confirmation email sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/resend_confirmation.html', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Allow the user to reset their password if token is valid.

    Args:
        token (str): A token for validating that the user resetting the
                     password has access to the email address associated with
                     the account.

    Returns:
        function: Redirect to auth.reset_password if wrong email address is
                  entered in the form.
        function: Redirect to auth.login if password is successfully reset.
        function: Redirect to auth.reset_password_request if token is invalid.
        function: Render template auth/reset_password.html if no form data is
                  received.
    """
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('Error: wrong email address!')
            return redirect(url_for('auth.reset_password', token=token))
        if user.reset_password(token, form.password1.data):
            flash('New password set, you may now use it to log in!')
            return redirect(url_for('auth.login'))
        else:
            flash('Error: Given token is invalid for this user! If you still '
                  'need to reset your password, please try again using the '
                  'form below: ')
            return redirect(url_for('auth.reset_password_request'))
    return render_template('auth/reset_password.html', form=form, token=token)


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    """Allow the user to request a token to let them reset their password.

    Returns:
        function: Redirect to main.index after sending email.
        function: Render template auth/reset_password_request.html id no form
                  data is received.
    """
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user.email_request_too_soon('reset password'):
            mbr = current_app.config['ERFP_MINUTES_BETWEEN_REQUESTS']
            flash('Error: A request to reset your password has already been' +
                  ' made within the last {0} minutes.'.format(mbr) +
                  ' If you did not recieve a confirmation email, it may' +
                  ' have been marked as spam, so please check your spam' +
                  ' folder/filter, and try again in {0}'.format(mbr) +
                  ' minutes if needed. If you would like help resetting' +
                  ' your password, please ' +
                  support_mailto_address('contact support',
                                         'Trouble Resetting Password') + '.')
            return redirect(url_for('main.index'))
        if user.email_request_too_many('reset password'):
            flash('Error: Too many requests have been made to reset the' +
                  ' password for your account. For your protection,' +
                  ' we have temporarily blocked all requests to reset your' +
                  ' password. We apologize for the inconvenience, please ' +
                  support_mailto_address('contact support',
                                         'Trouble Resetting Password') +
                  ' for help resetting your password.')
            return redirect(url_for('main.index'))
        if not current_app.config['TESTING']:  # pragma: no cover
            user.send_reset_password_email()
        user.log_email_request('reset password')
        flash('An email with instructions for resetting your password has ' +
              'been sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/reset_password_request.html', form=form)


@auth.route('/select_user', methods=['GET', 'POST'])
def select_user():
    """Select a user to use with a different page.

    Request Args:
        target_route (str): The route to redirect to after user is selected.

    Returns:
        function: Redirect to main.index if no target_route provided.
        function: Redirect to target_route on submission of form.
        function: Render template auth/select_user if no form data received.
    """
    target_route = request.args.get('target_route')
    # select_user should only load if it has a target_route.
    if target_route is None:
        flash('Error: Select user cannot be used without a target route!')
        return redirect(url_for('main.index'))
    form = SelectUserForm()
    form.load_users()
    if form.validate_on_submit():
        return redirect(url_for(target_route, user_id=form.select_user.data))
    return render_template('auth/select_user.html', form=form,
                           target_route=target_route)


def support_mailto_address(link_text, subject=None):
    """Return a mailto link to the support email address, usable in flashes.

    Args:
        link_text (str): The text to display as the mailto link.
        subject (str): Optional subject to include in mailto link.

    Returns:
        Markup: A mailto link for use in flashed messages.
    """
    if subject is None:
        uri = 'mailto:{0}'.format(current_app.config['SUPPORT_EMAIL'])
    else:
        uri = 'mailto:{0}?subject={1}'.format(
            current_app.config['SUPPORT_EMAIL'],
            subject)
    return Markup('<a href="{0}">{1}</a>'.format(uri, link_text))


def update_permission(user, permission, permission_from_form, permission_name):
    """Update a permission if it has been changed in the submitted form.

    Args:
        user (User): The user we want to update.
        permission (int): The Permission being updated.
        permission_from_form (bool): Whether or not the permission is checked
                                     in the submitted form.
        permission_name (str): Name of the permission being updated, so we can
                               include it in the flashed message if it is
                               updated.

    Returns:
        bool: True if the permission has changed, False if it is unchanged.
    """
    if user.can(permission):
        if not permission_from_form:
            user.revoke_permission(permission)
            flash('{0} may no longer {1}.'.format(user.name, permission_name))
            return True
        else:
            return False
    else:
        if permission_from_form:
            user.grant_permission(permission)
            flash('{0} may now {1}.'.format(user.name, permission_name))
            return True
        else:
            return False

from flask import flash, redirect, render_template, request, url_for
from flask.ext.login import current_user, login_required, login_user, \
    logout_user
from app import db
from app.decorators import permission_required
from . import auth
from .forms import EditUserForm, ManageUserForm, LoginForm, RegistrationForm, \
    ResendConfirmationForm, ResetPasswordForm, ResetPasswordRequestForm, \
    SelectUserForm
from .models import get_user_from_confirmation_token, Permission, User


@auth.route('/confirm_account/<token>')
def confirm_account(token):
    """Get an account confirmation token and confirm account if it's valid."""
    error_instructions = ('Please try again, or use the form below to'
                          ' revieve a new confirmation token:')
    if token is None:
        return redirect(url_for('auth.resend'))
    else:
        try:
            user = get_user_from_confirmation_token(token)
            if user.confirm_account(token):
                user.confirmed = True
                db.session.add(user)
                db.session.commit()
                flash('Account confirmed, '
                      '{0} you may now log in.'.format(user.name))
                return redirect(url_for('auth.login'))
            else:
                flash('Error: Account could not be confirmed.'
                      ' {0}'.format(error_instructions))
                return redirect(url_for('auth.resend_confirmation'))
        except BaseException as e:
            flash('Error: {0} {1}'.format(str(e), error_instructions))
            return redirect(url_for('auth.resend_confirmation'))


@auth.route('confirm_new_email/<token>')
def confirm_new_email(token):
    """Get a new email confirmation token and set new email if it's valid."""
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


@auth.route('/edit_user', methods=['GET', 'POST'])
@login_required
def edit_user():
    """Allow user to edit their account information."""
    form = EditUserForm()
    if form.validate_on_submit():
        user_edited = False
        try:
            if form.email1.data is not None and len(form.email1.data) > 0 and \
                    form.email1.data != current_user.email:
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
        except TypeError:
            # form.email1.data and form.new_password.data must be strings
            # if we are to use them, so we can safely do nothing if len()
            # raises a TypeError.
            pass
        if user_edited is True:
            return redirect(url_for('main.index'))
        else:
            flash('No changes have been made to your account.')
            return redirect(url_for('auth.edit_user'))
    form.email1.data = current_user.email
    form.email2.data = current_user.email
    return render_template('auth/edit_user.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Allow registered, confirmed users to log in."""
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            if user.confirmed:
                if(login_user(user, form.remember_me.data)):
                    flash('You are now logged in, {0}.'.format(user.name))
                    return redirect(request.args.get('next') or
                                    url_for('main.index'))
            else:
                flash('Error: Account not confirmed! Please check your email, '
                      'or use the form below to get a new confirmation email.')
                return redirect(url_for('auth.resend_confirmation'))
        else:
            flash('Error: Username or password is invalid!')
            return redirect(url_for('auth.login'))
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    """Log out the user if they visit this view while logged in."""
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/manage_user', methods=['GET', 'POST'])
@auth.route('/manage_user/<user_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_USERS)
def manage_user(user_id=None):
    """Allow user w/ the MANAGE_USERS permission to edit other users' data.

    Args:
        user_id (int): id of user to manage data of.
    """
    if user_id is None:
        return redirect(url_for('auth.select_user',
                                target_route='auth.manage_user'))

    user = User.query.get(user_id)
    if user is None:
        flash('Error: No user exists with that id number!')
        return redirect(url_for('auth.select_user',
                                target_route='auth.manage_user'))
    form = ManageUserForm()
    if form.validate_on_submit():
        # TODO: Continue adding more form fields to this!
        user_info_changed = False
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
    if user.can(Permission.MANAGE_USERS):
        form.manage_users.data = True
    if user.can(Permission.MANAGE_SEEDS):
        form.manage_seeds.data = True
    return render_template('auth/manage_user.html',
                           form=form,
                           username=user.name)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Allow a new user to create an account."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.email = form.email.data
        user.name = form.username.data
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        user.send_account_confirmation_email()
        flash('A confirmation email has been sent to ' + form.email.data +
              ', please check your email for further instructions.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/resend_confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    """Send a new account confirmation email."""
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_account_confirmation_email()
        flash('Confirmation email sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/resend.html', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Allow the user to reset their password if token is valid."""
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
            flash('Error: Reset token is too old or invalid! If you still '
                  'need to reset your password, please try again using the '
                  'form below: ')
            return redirect(url_for('auth.reset_password_request'))
    return render_template('auth/reset_password.html', form=form, token=token)


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    """Allow the user to request a token to let them reset their password."""
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_reset_password_email()
        flash('An email with instructions for resetting your password has ' +
              'been sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/reset_password_request.html', form=form)


@auth.route('/select_user', methods=['GET', 'POST'])
def select_user():
    """Select a user to use with a different page.

    Note:
        Requires a query parameter, target_route.
    """
    target_route = request.args.get('target_route')
    # select_user should only load if it has a target_route.
    print('Target route: {0}'.format(target_route))
    if target_route is None:
        return redirect(url_for('main.index'))

    form = SelectUserForm()
    form.load_users()
    if form.validate_on_submit():
        return redirect(url_for(target_route, user_id=form.select_user.data))
    return render_template('auth/select_user.html', form=form,
                           target_route=target_route)


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
        if permission_from_form is False:
            user.revoke_permission(permission)
            flash('{0} may no longer {1}.'.format(user.name, permission_name))
            return True
        else:
            return False
    else:
        if permission_from_form is True:
            user.grant_permission(permission)
            flash('{0} may now {1}.'.format(user.name, permission_name))
            return True
        else:
            return False

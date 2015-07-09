from flask import flash, redirect, render_template, request, url_for
from flask.ext.login import current_user, login_required, login_user, \
    logout_user
from app import db
from . import auth
from .forms import EditUserForm, LoginForm, RegistrationForm, \
    ResendConfirmationForm, ResetPasswordForm, ResetPasswordRequestForm
from .models import get_user_from_confirmation_token, User


@auth.route('/confirm_account/<token>')
def confirm_account(token):
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
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
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
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_account_confirmation_email()
        flash('Confirmation email sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/resend.html', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
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
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_reset_password_email()
        flash('An email with instructions for resetting your password has ' +
              'been sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/reset_password_request.html', form=form)

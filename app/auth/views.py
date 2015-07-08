from flask import flash, redirect, render_template, request, url_for
from flask.ext.login import current_user, login_required, login_user, \
    logout_user
from app import db
from . import auth
from .forms import LoginForm, RegistrationForm, ResendConfirmationForm, \
    ResetPasswordForm, ResetPasswordRequestForm
from .models import get_user_from_confirmation_token, User


@auth.route('/confirm/<token>')
def confirm(token):
    error_instructions = ('Please try again, or use the form below to'
                          ' revieve a new confirmation token:')
    if token is None:
        return redirect(url_for('auth.resend'))
    else:
        try:
            user = get_user_from_confirmation_token(token)
            if user.confirm_token(token):
                user.confirmed = True
                db.session.add(user)
                db.session.commit()
                flash('Account confirmed, '
                      '{0} you may now log in.'.format(user.name))
                return redirect(url_for('auth.login'))
            else:
                flash('Error: Account could not be confirmed.'
                      ' {0}'.format(error_instructions))
                return redirect(url_for('auth.resend'))
        except BaseException as e:
            flash('Error: {0} {1}'.format(str(e), error_instructions))
            return redirect(url_for('auth.resend'))


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
                return redirect(url_for('auth.resend'))
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
        user.send_confirmation_email()
        flash('A confirmation email has been sent to ' + form.email.data +
              ', please check your email for further instructions.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/resend', methods=['GET', 'POST'])
def resend():
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_confirmation_email()
        flash('Confirmation email sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/resend.html', form=form)


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password_request():
    if not current_user.is_anonymous():
        flash('Error: You are already logged in!')
        return redirect(url_for('main.index'))  # TODO: redirect to profile
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        user.send_reset_password_email()
        flash('An email with instructions for resetting your password has ' +
              'been sent to {0}.'.format(form.email.data))
        return redirect(url_for('main.index'))
    return render_template('auth/reset_password_request.html', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if not current_user.is_anonymous():
        return redirect(url_for('main.index'))  # TODO: redirect to profile
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            flash('Error: wrong email address!')
            return redirect(url_for('main.index'))  # TODO: redirect better
        if user.reset_password(token, form.password1.data):
            flash('New password set, you may now use it to log in!')
            return redirect(url_for('auth.login'))
        else:
            flash('Error: Reset token is too old or invalid! If you still '
                  'need to reset your password, please try again using the '
                  'form below: ')
            return redirect(url_for('auth.reset_password_request'))
    return render_template('auth/reset_password.html', form=form, token=token)

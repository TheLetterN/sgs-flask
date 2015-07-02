from flask import flash, redirect, render_template, url_for
from flask.ext.login import login_required, login_user, logout_user
from app import db
from . import auth
from .forms import LoginForm, RegistrationForm
from .models import User


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            if user.confirmed:
                login_user(user, form.remember_me.data)
                flash('You are now logged in, {0}.'.format(user.name))
                return redirect(url_for('main.index'))
            else:
                flash('You must confirm your account in order to log in.')
                # TODO: Give user an easy way to re-send confirmation email.
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
        flash('A confirmation email has been sent to ' + form.email.data +
              ', please check your email for further instructions.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

from flask import flash, redirect, render_template, url_for
from flask.ext.login import login_user
from . import auth
from .forms import LoginForm
from .models import User


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            flash('You are now logged in, {0}.'.format(user.name))
            return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)

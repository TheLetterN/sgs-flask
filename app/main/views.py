from flask import redirect, render_template, url_for
from . import main


@main.route('/')
def index():
    return render_template('main/index.html')


@main.route('/index')
@main.route('/index.html')
def index_redirect():
    """For convenience, we want common index pages to be redirected to /"""
    return redirect(url_for('main.index'), code=301)

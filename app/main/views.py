from flask import redirect, render_template, url_for
from . import main


@main.route('/')
def index():
    """Generate the index page of the website."""
    return render_template('main/index.html')


@main.route('/index')
@main.route('/index.html')
@main.route('/index.htm')
def index_redirect():
    """Redirect common index page names to main.index"""
    return redirect(url_for('main.index'), code=301)

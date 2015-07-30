from flask import redirect, render_template, url_for
from . import main
from app.auth.models import Permission


@main.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


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

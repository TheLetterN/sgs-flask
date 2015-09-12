from flask import current_app, redirect, render_template, url_for
from . import main
from app.auth.models import Permission
from app.seeds.models import Category


@main.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@main.context_processor
def make_categories_available():
    """Make categories available to Jinja templates.

    Returns:
        dict: A list of all Category objects loaded from the database.
    """
    if not current_app.config.get('TESTING'):
        categories = Category.query.all()
    else:
        categories = None
    return dict(categories=categories)


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

from flask import render_template
from . import seeds
from app.auth.models import Permission


@seeds.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@seeds.route('/')
def index():
    """Index page for seeds section.
    """
    return render_template('seeds/index.html')

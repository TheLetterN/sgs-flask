from flask import current_app, flash, redirect, render_template, request, \
    url_for
from flask.ext.login import login_required
from . import seeds
from .models import Category
from .forms import AddCategoryForm, EditCategoryForm, RemoveCategoryForm, \
    SelectCategoryForm
from app import db
from app.decorators import permission_required
from app.auth.models import Permission


@seeds.context_processor
def make_permissions_available():
    """Make the Permission object available to Jinja templates.

    Returns:
        dict: The Permission object to use in templates.
    """
    return dict(Permission=Permission)


@seeds.context_processor
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


@seeds.route('/add_category', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def add_category():
    """Add a category to the database."""
    form = AddCategoryForm()
    if form.validate_on_submit():
        category = Category()
        db.session.add(category)
        category.category = form.category.data.title()
        if len(form.description.data) > 0:
            category.description = form.description.data
        db.session.commit()
        flash('{0} has been added to Categories.'.
              format(category.category))
        return redirect(url_for('seeds.manage'))
    return render_template('seeds/add_category.html', form=form)


@seeds.route('/<category_slug>')
def category(category_slug):
    """Display a category."""
    category = Category.query.filter_by(slug=category_slug).first()
    if category is not None:
        return render_template('seeds/category.html', category=category)


@seeds.route('/edit_category', methods=['GET', 'POST'])
@seeds.route('/edit_category/<category_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def edit_category(category_id=None):
    if category_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
    if not category_id.isdigit():
        flash('Error: Category id must be an integer!'
              ' Please select a category:')
        return redirect(url_for('seeds.select_category',
                                dest='seeds.edit_category'))
    form = EditCategoryForm()
    category = Category.query.get(category_id)
    if form.validate_on_submit():
        edited = False
        if form.category.data.title() != category.category:
            flash('Category changed from \'{0}\' to \'{1}\'.'
                  .format(category.category, form.category.data.title()))
            category.category = form.category.data.title()
            edited = True
        if len(form.description.data) < 1:
            form.description.data = None
        if form.description.data != category.description:
            flash('{0} description changed to \'{1}\'.'
                  .format(form.category.data.title(), form.description.data))
            category.description = form.description.data
            edited = True
        if edited:
            db.session.commit()
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made to category: {0}'.format(category.category))
            return redirect(url_for('seeds.manage'))
    form.populate(category)
    return render_template('seeds/edit_category.html', form=form)


@seeds.route('/')
def index():
    """Index page for seeds section."""
    categories = Category.query.all()
    print(categories)
    return render_template('seeds/index.html', categories=categories)


@seeds.route('/manage')
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def manage():
    return render_template('seeds/manage.html')


@seeds.route('/select_category', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def select_category():
    """Select a category to load on another page.

    Request Args:
        dest (str): The route to redirect to once category is selected.
    """
    dest = request.args.get('dest')
    if dest is None:
        flash('Error: No destination page was specified!')
        return redirect(url_for('seeds.manage'))
    form = SelectCategoryForm()
    form.load_categories()
    if form.validate_on_submit():
        return redirect(url_for(dest, category_id=form.categories.data))
    return render_template('seeds/select_category.html', form=form)


@seeds.route('/remove_category', methods=['GET', 'POST'])
@seeds.route('/remove_category/<category_id>', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.MANAGE_SEEDS)
def remove_category(category_id=None):
    """Remove a category from the database."""
    if category_id is None:
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    if not category_id.isdigit():
        flash('Error: Category id must be an integer!')
        return redirect(url_for('seeds.select_category',
                                dest='seeds.remove_category'))
    form = RemoveCategoryForm()
    category = Category.query.get(category_id)
    if form.validate_on_submit():
        if form.verify_removal.data:
            flash('Category {0}: \'{1}\' has been removed from the database.'
                  .format(category.id, category.category))
            db.session.delete(category)
            return redirect(url_for('seeds.manage'))
        else:
            flash('No changes made. Check the box labeled \'Yes\''
                  ' if you want to remove this category.')
            return redirect(url_for('seeds.remove_category',
                                    category_id=category_id))
    return render_template('seeds/remove_category.html',
                           form=form,
                           category=category)

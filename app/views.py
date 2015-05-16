import os
from flask import (
        flash,
        redirect,
        render_template,
        request,
        url_for
)
from werkzeug import secure_filename

from app import app
from app.forms import AddSeedForm
from app.models import db, Seed

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/manage')
@app.route('/manage/<action>', methods=['GET', 'POST'])
def manage(action=None):
    if action == 'addseed':
        form = AddSeedForm()
        if form.validate_on_submit():
            flash('%s has been added!' % form.name.data)
            seed = Seed(
                name=form.name.data,
                binomen=form.binomen.data,
                description=form.description.data,
                #Lower and strip variety and category to make it easier to
                #search for them in the database.
                variety=form.variety.data.lower().strip(),      
                category=form.category.data.lower().strip(),
                price=form.price.data,
                is_active=form.is_active.data,
                in_stock=form.in_stock.data,
                synonyms=form.synonyms.data,
                series=form.series.data
            )
            if form.thumbnail.data:
                thumbfile = request.files[form.thumbnail.name]
                seed.thumbnail = thumbfile.filename
                seed.save_image(thumbfile)
            if seed.verify():
                db.session.add(seed)
                db.session.commit()

            return redirect(url_for('manage'))
        else:
            title = app.config['SITE_NAME'] + ' - Add Seed'
            return render_template('addseed.html', form=form, title=title)
    else:
        title = app.config['SITE_NAME'] + ' - Manage Site'
        return render_template('manage.html', title=title)

@app.route('/seeds')
@app.route('/seeds/<variety>')
def seeds(variety=None):
    if variety:
        variety = variety.lower().strip()
        title = app.config['SITE_NAME'] + ' - ' + variety + ' seeds'
        seeds = Seed.query.filter_by(variety=variety).all()
        return render_template('variety.html', title=title, variety=variety, seeds=seeds)


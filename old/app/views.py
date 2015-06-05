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
            seed = Seed()
            seed.populate_from_form(form)
            if seed.verify():
                seed.save()
                flash('%s has been added!' % form.name.data)


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


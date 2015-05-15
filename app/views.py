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
                variety=form.variety.data,
                category=form.category.data,
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

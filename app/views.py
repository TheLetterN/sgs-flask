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
from forms import AddSeedForm

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
            #Now that we know everything's valid, we can save the thumbnail
            thumbfile = request.files[form.thumbnail.name]
            thumbfile.save(os.path.join(app.config['UPLOAD_FOLDER'],
                                        secure_filename(thumbfile.filename)))

            return redirect(url_for('manage'))
        else:
            title = app.config['SITE_NAME'] + ' - Add Seed'
            return render_template('addseed.html', form=form, title=title)
    else:
        title = app.config['SITE_NAME'] + ' - Manage Site'
        return render_template('manage.html', title=title)

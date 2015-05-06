from flask import render_template

from app import app
from config import SITE_NAME

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

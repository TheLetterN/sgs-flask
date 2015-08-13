from flask import Blueprint


seeds = Blueprint('seeds', __name__)

from . import views

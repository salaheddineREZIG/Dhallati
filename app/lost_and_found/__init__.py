from flask import Blueprint

lost_and_found = Blueprint('lost_and_found', __name__)

from . import routes
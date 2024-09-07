from flask import Blueprint

lost_and_found = Blueprint('lost_and_found', __name__, template_folder='../templates/lost_and_found')

from . import routes
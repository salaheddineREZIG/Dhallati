from flask import Blueprint

lost_and_found = Blueprint('lost_and_found', __name__, template_folder='../templates/lost_and_found')

from app.lost_and_found.routes import home, reports,claim 
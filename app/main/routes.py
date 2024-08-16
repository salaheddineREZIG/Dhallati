from flask import render_template,Blueprint
from app.functions import login_required

main = Blueprint('main', __name__)
@main.route('/')
def index():
    return render_template('index.html')


@main.route('/home')
@login_required
def home(user):
    return render_template('home.html', user=user)

from flask import render_template
from app.decorators import login_required
from . import main

@main.route('/')
def index():
    return render_template('index.html')


@main.route('/home')
@login_required
def home(user):
    return render_template('home.html', user=user)

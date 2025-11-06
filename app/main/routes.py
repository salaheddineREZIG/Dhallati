from flask import render_template, flash, redirect, url_for
from app.decorators import login_required
from . import main
from app.lost_and_found.models import Report, Item

@main.route('/')
def index():
    return render_template('index.html')


@main.route('/home')
@login_required
def home(user):
    return render_template('home.html', user=user)

@main.route('/profile')
@login_required
def profile(user):
    try:
        reports = Report.query.filter_by(reporter_id=user["id"]).all()
        items_claimed = Item.query.filter_by(claimed_by_id=user["id"]).count()
        active_items = Item.query.filter_by(reporter_id=user["id"], claimed_by_id=None).count()
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.home'))
    treated = []
    for report in reports:
        r = report.to_dict()
        r["name"] = Item.query.get(report.item_id).name
        treated.append(r)
    stats = {
        'reports': treated,
        'items_claimed': items_claimed,
        'active_items': active_items
    }
    print(r, items_claimed, active_items)
    return render_template('profile.html', user=user,stats = stats)

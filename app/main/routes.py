from flask import render_template, flash, redirect, url_for, current_app
from app.decorators import login_required
from . import main
from app.lost_and_found.models import Report, Item, Category
from app.lost_and_found.forms import ReportItemForm
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
        active_items = Item.query.filter_by(
            reporter_id=user["id"], 
            claimed_by_id=None
        ).count()
    except Exception as e:
        # ✅ Log full traceback
        current_app.logger.exception("Failed to load profile data")
        flash("An error occurred while loading your profile", "danger")
        return redirect(url_for('main.home'))

    # Process reports safely
    treated = []
    try:
        for report in reports:
            r = report.to_dict()
            item = Item.query.get(report.item_id)
            if item:
                r["name"] = item.name
            else:
                r["name"] = "Unknown item"
            treated.append(r)
    except Exception:
        # ✅ Log processing errors too
        current_app.logger.exception("Failed while processing report list")
        flash("An error occurred while preparing your profile data", "danger")
        return redirect(url_for('main.home'))

    stats = {
        'reports': treated,
        'items_claimed': items_claimed,
        'active_items': active_items
    }
    form = ReportItemForm()
    form.category_id.choices = [(category.id, category.name) for category in Category.query.all()]
    return render_template('profile.html', user=user, stats=stats, form=form)

from flask import jsonify, request, current_app, make_response
from . import main
from app.decorators import login_required
from app.lost_and_found.models import Report, Item
# ... other imports already in file ...

@main.route('/profile/reports', methods=['GET'])
@login_required
def profile_reports(user):
    """
    GET /profile/reports?page=1&page_size=8
    Returns JSON:
    {
      "items": [{ report fields + item_name }...],
      "page": 1,
      "page_size": 8,
      "total": 42,
      "has_more": true
    }
    """
    try:
        # parse pagination params
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 8))
        except ValueError:
            return make_response(jsonify({"error": "Invalid pagination parameters"}), 400)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 8

        # base query: reports for this user, newest first
        base_q = Report.query.filter_by(reporter_id=user['id']).order_by(Report.created_at.desc())

        total = base_q.count()
        reports_page = base_q.limit(page_size).offset((page - 1) * page_size).all()

        # collect item ids, query them once to avoid N+1
        item_ids = [r.item_id for r in reports_page if r.item_id is not None]
        items = Item.query.filter(Item.id.in_(item_ids)).all() if item_ids else []
        items_map = {it.id: it.name for it in items}

        result = []
        for r in reports_page:
            rd = r.to_dict()
            rd['item_name'] = items_map.get(r.item_id, "Unknown item")
            result.append(rd)

        loaded = (page - 1) * page_size + len(result)
        has_more = loaded < total

        payload = {
            "items": result,
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_more": has_more
        }
        return make_response(jsonify(payload), 200)

    except Exception:
        current_app.logger.exception("Failed to fetch paged profile reports for user_id=%s", user.get('id'))
        return make_response(jsonify({"error": "Internal server error"}), 500)


@main.route('/profile/get_edit_form/<int:report_id>')
@login_required
def get_edit_form(user,report_id):
    """Return pre-populated edit form for a specific report"""
    try:
        # Get the report with related item data
        
        report = Report.query.filter_by(id=report_id).first()
        
        if not report:
            return "Report not found", 404
        if(report.reporter_id != user['id']):
            return "Unauthorized", 403
        
        form = ReportItemForm(
            report_type=report.report_type.value if report.report_type else 'found',
            name=report.item.name,
            description=report.item.description,
            category=report.item.category_id,
            location_reported=report.location_reported,
            event_datetime=report.item.created_at,  # Using item creation time as event time
            is_anonymous=report.is_anonymous,
            additional_details=report.additional_details,
            contact_info=report.contact_info
        )
        
        # Populate category choices
        categories = Category.query.all()
        form.category.choices = [(c.id, c.name) for c in categories]
        
        return render_template('main/_edit_form_fields.html', 
                             form=form, 
                             report=report)
                             
    except Exception as e:
        print(f"Error loading edit form: {e}")
        return "Error loading form", 500


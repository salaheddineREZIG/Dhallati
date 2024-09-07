from flask import jsonify, request, render_template, flash, redirect, url_for
from . import lost_and_found
from config import Config
from app.decorators import login_required
from app.lost_and_found.forms import ReportItemForm
from app.lost_and_found.models import Item, Report, Category, ItemImage, db
from flask_wtf.csrf import validate_csrf, generate_csrf
from datetime import datetime, timedelta
from app.constants import (
    DESCRIPTION_AND_ADDITIONAL_CHARACTERS as NAME_LIMIT, 
    NAME_AND_CONTACT_AND_LOCATION_CHARACTERS as DESCRIPTION_LIMIT, 
    REPORT_TYPE
)
from app.functions import allowed_file
import os
from werkzeug.utils import secure_filename
import uuid

@lost_and_found.route('/lost_and_found')
@login_required
def lost_and_found_page(user):
    try:
        form = ReportItemForm()
        form.category.choices = [(category.id, category.name) for category in Category.query.all()]
        csrf_token = generate_csrf()
        return render_template('lost_and_found.html', form=form, csrf_token=csrf_token)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@lost_and_found.route('/lost_and_found/api/lost', methods=['POST', 'GET'])
@login_required
def report_lost_item(user):
    if request.method == 'POST':
        form = ReportItemForm(request.form)  

        # Set choices for category field
        form.category.choices = [(category.id, category.name) for category in Category.query.all()]

        # Debugging: Print request.files and form.images.data
        print("Request Files:", request.files)
        print("Form Images Data:", form.images.data)

        if form.validate():
            try:
                # Length checks for form fields
                if (
                    len(form.name.data) > NAME_LIMIT or 
                    len(form.location_reported.data) > NAME_LIMIT or 
                    len(form.contact_info.data) > NAME_LIMIT
                ):
                    flash("Name, location, and contact info should be less than 50 characters", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))

                if (
                    len(form.description.data) > DESCRIPTION_LIMIT or 
                    len(form.additional_details.data) > DESCRIPTION_LIMIT
                ):
                    flash("Description and additional details should be less than 150 characters", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))

                # Check if report type is valid
                if form.report_type.data not in REPORT_TYPE:
                    flash("Report type should be 'lost' or 'found'", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))

                # Category validation
                categories = Category.query.all()
                ids = [category.id for category in categories]
                if form.category.data not in ids:
                    flash("Invalid category", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))

                # Date validation (within the last 7 days and not in the future)
                if (
                    form.event_datetime.data is None or 
                    form.event_datetime.data > datetime.now() or 
                    form.event_datetime.data < datetime.now() - timedelta(days=7)
                ):
                    flash("Invalid date", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))

                # Create new Item
                new_item = Item(
                    name=form.name.data,
                    description=form.description.data,
                    category_id=form.category.data,
                    location_reported=form.location_reported.data,
                    reporter_id=user['google_id'],
                    claimed_at=form.event_datetime.data,
                    status=form.report_type.data
                )
                db.session.add(new_item)
                db.session.commit()
                print(new_item)
                print(form.images.data)

                for image_file in request.files.getlist('images'):
                    if image_file:
                        if not allowed_file(image_file.filename):
                            flash("Invalid file type", "danger")
                            continue

                        original_filename = secure_filename(image_file.filename)
                        file_extension = os.path.splitext(original_filename)[1]
                        unique_filename = str(uuid.uuid4()) + file_extension
                        image_path = os.path.join(Config.UPLOAD_FOLDER , unique_filename)
                        image_file.save(image_path)
                        print(image_path, unique_filename, file_extension, original_filename)

                        # Create a new ItemImage entry for each uploaded image
                        new_image = ItemImage(
                            item_id=new_item.id,
                            image_url=image_path  # Store the file path or URL
                        )
                        print(new_image)
                        db.session.add(new_image)

                # Create new Report
                new_report = Report(
                    item_id=new_item.id,
                    reporter_id=None if form.is_anonymous.data else user['google_id'],
                    report_type=form.report_type.data,
                    additional_details=form.additional_details.data,
                    location_reported=form.location_reported.data,
                    is_anonymous=form.is_anonymous.data,
                    contact_info=form.contact_info.data
                )
                db.session.add(new_report)
                db.session.commit()

                return jsonify({"message": "Report successfully submitted", "item_id": new_item.id}), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": form.errors}), 400

    elif request.method == 'GET':
        try:
            items = Item.query.filter_by(status='lost').all()
            return jsonify({"items": [item.to_dict() for item in items]}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

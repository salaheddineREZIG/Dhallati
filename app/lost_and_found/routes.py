from flask import jsonify, request, render_template, flash, redirect, url_for,make_response
from . import lost_and_found
from config import Config
from app.decorators import login_required
from app.lost_and_found.forms import ReportItemForm
from app.lost_and_found.models import Item, Report, Category, ItemImage, db
from datetime import datetime, timedelta
from app.constants import (
    DESCRIPTION_AND_ADDITIONAL_CHARACTERS as NAME_LIMIT, 
    NAME_AND_CONTACT_AND_LOCATION_CHARACTERS as DESCRIPTION_LIMIT, 
    ReportType as REPORT_TYPE
)
from app.functions import allowed_file, log_action
import os
from werkzeug.utils import secure_filename
import uuid

@lost_and_found.route('/lost_and_found')
@login_required
def lost_and_found_page(user):
    try:
        form = ReportItemForm()
        form.category.choices = [(category.id, category.name) for category in Category.query.all()]
        return render_template('lost_and_found.html', form=form)
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.home'))
@lost_and_found.route('/lost_and_found/api', methods=['POST', 'GET','PUT', 'DELETE'])
def report_item():
    if request.method == 'POST':
        form = ReportItemForm(request.form)  

        # Set choices for category field
        form.category.choices = [(category.id, category.name) for category in Category.query.all()]

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
                if len(request.files.getlist('images')) > 5:
                    flash("You can upload a maximum of 5 images", "danger")
                    return redirect(url_for('lost_and_found.lost_and_found_page'))
                
                # Create new Item
                new_item = Item(
                    name=form.name.data,
                    description=form.description.data,
                    category_id=form.category.data,
                    reporter_id=1,
                    claimed_at=form.event_datetime.data,
                    status=form.report_type.data
                )
                db.session.add(new_item)
                db.session.commit()
                log_action(1, 'items', new_item.id, 'create', changes=f"Item {new_item.name} created.")
                

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

                        # Create a new ItemImage entry for each uploaded image
                        new_image = ItemImage(
                            item_id=new_item.id,
                            image_url=image_path  # Store the file path or URL
                        )
                        db.session.add(new_image)
                        db.session.commit()
                        log_action(1, 'item_images', new_image.id, 'create', changes=f"Image for item {new_item.name} added.") 
                # Create new Report
                new_report = Report(
                    item_id=new_item.id,
                    reporter_id=1,
                    report_type=form.report_type.data,
                    additional_details=form.additional_details.data,
                    location_reported=form.location_reported.data,
                    is_anonymous=form.is_anonymous.data,
                    contact_info=form.contact_info.data
                )
                db.session.add(new_report)
                print(form.report_type.data)
                db.session.commit()
                log_action(1, 'reports', new_report.id, 'create', changes=f"Report for item {new_item.name} created.")
                flash("Report successfully submitted", "success")
                return redirect(url_for('lost_and_found.lost_and_found_page', show=form.report_type.data.lower()))

            except Exception as e:
                db.session.rollback()
                print(e)
                flash(f"An error occurred, please try again", "danger")
                return redirect(url_for('lost_and_found.lost_and_found_page'))
        else:
            flash("Form validation failed. Please check your inputs.", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))

    elif request.method == 'GET':              
        type = request.args.get('type')  
        if  type == 'lost':
            try:
                items = Item.query.filter_by(status='LOST').all()
                ret = []
                for item in items:
                    ret.append(item.to_dict())
                return make_response(jsonify(ret), 200)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        elif type == 'found':
            try:
                items= Item.query.filter_by(status='FOUND').all()
                ret = []
                for item in items:
                    ret.append(item.to_dict())
                return make_response(jsonify(ret), 200)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

@lost_and_found.route("/lost_and_found/item", methods=['GET'])
@login_required
def item(user):
    try:
        
        item_id = request.args.get('id')
        if not item_id:
            flash("Item ID is required", "danger")
            return redirect(url_for('main.home'))
        item = Item.query.filter_by(id=item_id).first()
        if not item:
            flash("Item not found", "danger")
            return redirect(url_for('main.home'))
        report = Report.query.filter_by(item_id=item_id).first()
        if not report:
            flash("Report not found for this item", "danger")
            return redirect(url_for('main.home'))
        item = item.to_dict()        
        report = report.to_dict()
        

        return render_template('item_detail.html', item=item, report=report)
    
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.home'))
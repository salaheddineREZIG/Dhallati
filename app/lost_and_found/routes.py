from flask import jsonify, request, render_template, flash, redirect, url_for, make_response, current_app
from . import lost_and_found
from config import Config
from app.decorators import login_required
from app.lost_and_found.forms import ReportItemForm
from app.lost_and_found.models import Item, Report, Category, ItemImage, Match, Location , VerificationQuestion ,db
from datetime import datetime, timedelta
from app.constants import (
    NAME_LIMIT,
    DESCRIPTION_LIMIT,
    REPORT_TYPES,
    ITEM_STATUSES,
    
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
        form.category_id.choices = [(category.id, category.name) for category in Category.query.all()]
        form.location_id.choices = [(l.id, l.name) for l in Location.query.all()]
        return render_template('lost_and_found.html', form=form)
    except Exception as e:
        current_app.logger.exception("Failed to render lost_and_found page")
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.home'))

@lost_and_found.route('/report/new', methods=['GET'])
@login_required
def new_report(user):
    """Render the multi-step report form"""
    form = ReportItemForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.location_id.choices = [(l.id, l.name) for l in Location.query.all()]    
    return render_template('report_form.html', form=form,
                         user=user)

@lost_and_found.route('/lost_and_found/api', methods=['POST', 'GET', 'PUT', 'DELETE'])
@login_required
def report_item(user):
    if request.method == 'POST':
        # Use request.form AND request.files for form data
        form = ReportItemForm()
        
        # Set choices for category field
        try:
            form.category_id.choices = [(category.id, category.name) for category in Category.query.all()]
            form.location_id.choices = [(l.id, l.name) for l in Location.query.all()]
        except Exception:
            current_app.logger.exception("Failed to load categories or locations for ReportItemForm")
            flash("An error occurred while preparing the form. Please try again.", "danger")
            return redirect(url_for('lost_and_found.new_report'))

        if form.validate_on_submit():
            try:
                current_app.logger.info("Contact info received: %s", form.contact_info.data)
                # Length checks for form fields
                if len(form.name.data) > NAME_LIMIT:
                    flash("Name should be less than 50 characters", "danger")
                    return redirect(url_for('lost_and_found.new_report'))

                if (len(form.description.data) > DESCRIPTION_LIMIT or
                    len(form.additional_details.data) > DESCRIPTION_LIMIT or
                    len(form.specific_spot.data) > 255):
                    flash("Description and additional details should be less than 150 characters, and specific spot should be less than 255 characters", "danger")
                    return redirect(url_for('lost_and_found.new_report'))

                # Check if report type is valid (using string comparison)
                if form.report_type.data not in REPORT_TYPES:
                    flash(f"Report type should be one of {', '.join(REPORT_TYPES)}", "danger")
                    return redirect(url_for('lost_and_found.new_report'))

                # Category validation
                categories = Category.query.all()
                category_ids = [category.id for category in categories]
                if form.category_id.data not in category_ids:
                    flash("Invalid category", "danger")
                    return redirect(url_for('lost_and_found.new_report'))
                
                # Location validation
                locations = Location.query.all()
                location_ids = [location.id for location in locations]
                if form.location_id.data and form.location_id.data not in location_ids:
                    flash("Invalid location", "danger")
                    return redirect(url_for('lost_and_found.new_report'))

                # Date validation (within the last 7 days and not in the future)
                if form.event_datetime.data:
                    if (form.event_datetime.data > datetime.now() or
                        form.event_datetime.data < datetime.now() - timedelta(days=7)):
                        flash("Invalid date", "danger")
                        return redirect(url_for('lost_and_found.new_report'))

                if len(request.files.getlist('images')) > 5:
                    flash("You can upload a maximum of 5 images", "danger")
                    return redirect(url_for('lost_and_found.new_report'))

                # Convert report type string to enum for database

                # Create new Item
                new_item = Item(
                    name=form.name.data,
                    description=form.description.data,
                    category_id=form.category_id.data,  # Use category_id.data
                    reporter_id=user['id'],  # Use actual user ID
                    claimed_at=form.event_datetime.data or datetime.now(),
                    status=form.report_type.data
                )
                db.session.add(new_item)
                db.session.commit()
                log_action(user['id'], 'items', new_item.id, 'create', changes=f"Item {new_item.name} created.")

                # Handle image uploads
                for image_file in request.files.getlist('images'):
                    if image_file and image_file.filename:
                        if not allowed_file(image_file.filename):
                            flash("Invalid file type", "danger")
                            continue

                        original_filename = secure_filename(image_file.filename)
                        file_extension = os.path.splitext(original_filename)[1]
                        unique_filename = str(uuid.uuid4()) + file_extension
                        image_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
                        image_file.save(image_path)

                        # Create a new ItemImage entry for each uploaded image
                        new_image = ItemImage(
                            item_id=new_item.id,
                            image_url=image_path
                        )
                        db.session.add(new_image)
                        db.session.commit()
                        log_action(user['id'], 'item_images', new_image.id, 'create', changes=f"Image for item {new_item.name} added.")

                # Create new Report
                new_report = Report(
                    item_id=new_item.id,
                    reporter_id=user['id'],
                    report_type=form.report_type.data,
                    additional_details=form.additional_details.data,
                    location_id=form.location_id.data,
                    specific_spot=form.specific_spot.data,
                    event_datetime=form.event_datetime.data or datetime.now(),
                    is_anonymous=form.is_anonymous.data,
                    contact_info=form.contact_info.data
                )
                db.session.add(new_report)
                db.session.commit()
                log_action(user['id'], 'reports', new_report.id, 'create', changes=f"Report for item {new_item.name} created.")
                
                # Create verification question for found items
                if form.report_type.data == 'found' and form.verification_question.data:
                    verification_question = VerificationQuestion(
                        report_id=new_report.id,
                        question=form.verification_question.data
                    )
                    db.session.add(verification_question)
                    db.session.commit()
                    log_action(user['id'], 'verification_questions', verification_question.id, 'create', changes=f"Verification question for item {new_item.name} created.")

                flash("Report successfully submitted", "success")
                return redirect(url_for('lost_and_found.lost_and_found_page', show=form.report_type.data.lower()))

            except Exception as e:
                current_app.logger.exception("Failed while processing report_item POST")
                db.session.rollback()
                flash("An error occurred, please try again", "danger")
                return redirect(url_for('lost_and_found.lost_and_found_page'))
        else:
            current_app.logger.warning("ReportItemForm validation failed: %s", form.errors)
            flash("Form validation failed. Please check your inputs.", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))

    elif request.method == 'DELETE':
        report_id = request.args.get('report_id')
        if not report_id:
            return make_response(jsonify({"error": "Missing report_id"}), 400)
        
        try:
            rid = int(report_id)
        except (ValueError, TypeError):
            return make_response(jsonify({"error": "Invalid report_id"}), 400)

        report = Report.query.get(rid)
        if not report:
            return make_response(jsonify({"error": "Report not found"}), 404)

        # Authorization check
        if not user or str(report.reporter_id) != str(user["id"]):
            return make_response(jsonify({"error": "Unauthorized"}), 403)
        
        try:
            # Get all related data BEFORE any deletion
            item = report.item
            item_name = item.name if item else "Unknown item"
            
            image_urls = []
            matches_to_delete = []
            
            if item:
                # Get images and extract URLs before any deletion
                images_to_delete = ItemImage.query.filter_by(item_id=item.id).all()
                image_urls = [img.image_url for img in images_to_delete]  # Extract URLs while objects are valid
                
                # Get matches for this item
                matches_to_delete = Match.query.filter(
                    (Match.lost_item_id == item.id) | (Match.found_item_id == item.id)
                ).all()
            else:
                images_to_delete = []            

            
            db.session.delete(report)  
            db.session.delete(item) if item else None
            for match in matches_to_delete:
                db.session.delete(match) if match else None
            for image in images_to_delete:
                db.session.delete(image) if image else None
                
            log_action(user["id"], 'reports', report.id, 'delete', 
                    changes=f"Report {report.id} for item '{item_name}' deleted.")
            current_app.logger.info(f"Deleted report {report.id} for item '{item_name}'.")

            # Commit all deletions
            db.session.commit()

            # 5. Delete image files from filesystem AFTER successful DB commit
            # ✅ NOW image_urls is populated with strings, not ORM objects
            for image_url in image_urls:
                try:
                    if os.path.exists(image_url):
                        os.remove(image_url)
                    else:
                        current_app.logger.warning(f"Image file not found: {image_url}")
                except OSError as e:
                    current_app.logger.error(f"Failed to delete image file {image_url}: {e}")

            return make_response(jsonify({
                "message": "Report and all associated data deleted successfully",
                "report_id": report.id,
                "deleted_items": 1 if item else 0,
                "deleted_images": len(images_to_delete),
                "deleted_matches": len(matches_to_delete)
            }), 200)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Deletion failed: {e}")
            return make_response(jsonify({"error": "Deletion failed"}), 500)
    else:
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
            
            
@lost_and_found.route('/lost_and_found/update_report', methods=['POST'])
            
@login_required
def update_report(user):
    """Handle report updates (using _method=PUT)"""
    report = None
    removed_image_urls = []  # Track removed images for cleanup
    
    try:
        report_id = request.form.get('report_id') 
        if not report_id:
            flash('Report ID is required', 'error')
            return redirect(url_for('main.profile'))
        
        report = Report.query.filter_by(id=report_id).first()
        if not report:
            flash('Report not found', 'error')
            return redirect(url_for('main.profile'))
        
        if report.reporter_id != user['id']:
            flash('Unauthorized to edit this report', 'error')
            return redirect(url_for('main.profile'))        
            
        form = ReportItemForm()
        
        # Populate category choices for validation
        categories = Category.query.all()
        form.category.choices = [(c.id, c.name) for c in categories]
        
        if not form.validate_on_submit():
            # Return form with validation errors
            categories = Category.query.all()
            form.category.choices = [(c.id, c.name) for c in categories]
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)
        
        # ✅ VALIDATION CHECKS
        if (len(form.name.data) > NAME_LIMIT or
            len(form.location_reported.data) > NAME_LIMIT or
            len(form.contact_info.data) > NAME_LIMIT):
            flash("Name, location, and contact info should be less than 50 characters", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        if (len(form.description.data) > DESCRIPTION_LIMIT or
            len(form.additional_details.data) > DESCRIPTION_LIMIT):
            flash("Description and additional details should be less than 150 characters", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # Check if report type is valid
        if form.report_type.data not in REPORT_TYPES:
            flash("Report type should be 'lost' or 'found'", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # Category validation
        category_ids = [category.id for category in categories]
        if form.category.data not in category_ids:
            flash("Invalid category", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # Date validation (within the last 7 days and not in the future)
        if (form.event_datetime.data and
            (form.event_datetime.data > datetime.now() or
             form.event_datetime.data < datetime.now() - timedelta(days=7))):
            flash("Invalid date", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # ✅ FIXED: Get current image count BEFORE any operations
        current_image_count = len(report.item.images)
        new_images_count = len(request.files.getlist('images'))
        remove_image_ids = request.form.getlist('remove_images')
        
        # Calculate final image count after removal and addition
        final_image_count = current_image_count - len(remove_image_ids) + new_images_count
        
        if final_image_count > 5:
            flash("Total images cannot exceed 5", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # ✅ FIXED: Handle image removal FIRST
        if remove_image_ids:
            images_to_remove = ItemImage.query.filter(
                ItemImage.id.in_(remove_image_ids),
                ItemImage.item_id == report.item_id
            ).all()
            
            for image in images_to_remove:
                removed_image_urls.append(image.image_url)  # Store for cleanup
                db.session.delete(image)
        
        # ✅ FIXED: Handle new image uploads - SAVE FILES TEMPORARILY
        uploaded_files = []
        try:
            for image in form.images.data:
                if image and image.filename:  # Only process actual files
                    filename = secure_filename(image.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    image.save(file_path)
                    uploaded_files.append(file_path)
                    
                    item_image = ItemImage(image_url=file_path, item_id=report.item_id)
                    db.session.add(item_image)
        except Exception as upload_error:
            # Clean up any uploaded files if there's an error
            for file_path in uploaded_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except OSError:
                    pass  # Ignore cleanup errors during rollback
            raise upload_error

        # ✅ UPDATE REPORT AND ITEM DATA
        report.report_type = form.report_type.data
        report.location_reported = form.location_reported.data
        report.additional_details = form.additional_details.data
        report.is_anonymous = form.is_anonymous.data
        report.contact_info = form.contact_info.data
        
        # Update item data
        report.item.name = form.name.data
        report.item.description = form.description.data
        report.item.category_id = form.category.data
        
        # Handle event datetime (stored in item's created_at for now)
        if form.event_datetime.data:
            report.item.created_at = form.event_datetime.data

        # ✅ SINGLE COMMIT FOR ALL DATABASE CHANGES
        db.session.commit()
        
        # ✅ CLEAN UP REMOVED IMAGE FILES AFTER SUCCESSFUL COMMIT
        for image_url in removed_image_urls:
            try:
                if os.path.exists(image_url):
                    os.remove(image_url)
                else:
                    current_app.logger.warning(f"Image file not found during cleanup: {image_url}")
            except OSError as e:
                current_app.logger.error(f"Failed to delete image file {image_url}: {e}")

        flash('Report updated successfully!', 'success')
        return redirect(url_for('main.profile'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating report {report.id if report else 'unknown'}: {str(e)}")
        
        # ✅ CLEAN UP ANY UPLOADED FILES ON ERROR
        if 'uploaded_files' in locals():
            for file_path in uploaded_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except OSError as cleanup_error:
                    current_app.logger.error(f"Failed to cleanup uploaded file {file_path}: {cleanup_error}")
        
        flash('An error occurred while updating the report', 'error')
        return redirect(url_for('main.profile'))
    
    
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
        
        # Convert to dict with public=False since user is logged in
        item_dict = item.to_dict()
        report_dict = report.to_dict()
        
        
        if report.is_anonymous :
            report_dict['reporter_name'] = None
            report_dict['contact_info'] = None
            item_dict['reporter_name'] = None
            item_dict['claimed_by_name'] = None
        

        return render_template('item_detail.html', item=item_dict, report=report_dict)

    except Exception as e:
        current_app.logger.exception("Failed to render item detail for id=%s", request.args.get('id'))
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('main.home'))
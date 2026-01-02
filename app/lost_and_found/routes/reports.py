from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, current_app
from werkzeug.utils import secure_filename
from app.lost_and_found import lost_and_found
from config import Config
from app.decorators import login_required
from app.lost_and_found.models import Category, Location, Item, ItemImage, Report, VerificationQuestion, Claim
from app import db
from datetime import datetime, timedelta
from app.functions import allowed_file, log_action
import os
import uuid
from app.constants import NAME_LIMIT, DESCRIPTION_LIMIT, REPORT_TYPES
from app.lost_and_found.forms import ReportItemForm
from sqlalchemy import or_, func
from PIL import Image

@lost_and_found.route('/report/new', methods=['GET'])
@login_required
def new_report(user):
    """Render the multi-step report form"""
    form = ReportItemForm()
    try:
        form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
        form.location_id.choices = [(l.id, l.name) for l in Location.query.all()]
    except Exception as e:
        current_app.logger.error(f"Failed to load categories/locations: {e}")
        flash("Failed to load form data. Please try again.", "danger")
        return redirect(url_for('lost_and_found.lost_and_found_page'))
    
    return render_template('report_form.html', form=form, user=user)

@lost_and_found.route('/lost_and_found/api', methods=['POST', 'GET', 'PUT', 'DELETE'])
@login_required
def report_item(user):
    if request.method == 'POST':
        # Use request.form AND request.files for form data
        form = ReportItemForm()
        
        # Set choices for category field (must be done before validation)
        try:
            form.category_id.choices = [(category.id, category.name) for category in Category.query.all()]
            form.location_id.choices = [(l.id, l.name) for l in Location.query.all()]
        except Exception:
            current_app.logger.exception("Failed to load categories or locations for ReportItemForm")
            flash("An error occurred while preparing the form. Please try again.", "danger")
            return redirect(url_for('lost_and_found.new_report'))

        if not form.validate_on_submit():
            current_app.logger.warning("ReportItemForm validation failed: %s", form.errors)
            
            # Show specific validation errors for each field
            for field_name, errors in form.errors.items():
                for error in errors:
                    # Clean up field name for display
                    field_display_name = field_name.replace('_', ' ').title()
                    flash(f"{field_display_name}: {error}", "danger")
            
            # Re-render the form with submitted data
            return render_template('report_form.html', form=form, user=user)

        # If form validation passes, continue with your existing successful processing code
        try:
            current_app.logger.info("Contact info received: %s", form.contact_info.data)
            
            # ===== VALIDATIONS =====
            
            # Length checks for form fields
            if len(form.name.data) > NAME_LIMIT:
                flash("Name should be less than 50 characters", "danger")
                return render_template('report_form.html', form=form, user=user)

            if (len(form.description.data) > DESCRIPTION_LIMIT or
                len(form.additional_details.data) > DESCRIPTION_LIMIT or
                len(form.specific_spot.data) > 255):
                flash("Description and additional details should be less than 150 characters, and specific spot should be less than 255 characters", "danger")
                return render_template('report_form.html', form=form, user=user)

            # Check if report type is valid (using string comparison)
            if form.report_type.data not in REPORT_TYPES:
                flash(f"Report type should be one of {', '.join(REPORT_TYPES)}", "danger")
                return render_template('report_form.html', form=form, user=user)

            # Category validation
            categories = Category.query.all()
            category_ids = [category.id for category in categories]
            if form.category_id.data not in category_ids:
                flash("Invalid category", "danger")
                return render_template('report_form.html', form=form, user=user)
            
            # Location validation
            locations = Location.query.all()
            location_ids = [location.id for location in locations]
            if form.location_id.data and form.location_id.data not in location_ids:
                flash("Invalid location", "danger")
                return render_template('report_form.html', form=form, user=user)

            # Date validation (within the last 7 days and not in the future)
            if form.event_datetime.data:
                if (form.event_datetime.data > datetime.now() or
                    form.event_datetime.data < datetime.now() - timedelta(days=7)):
                    flash("Invalid date", "danger")
                    return render_template('report_form.html', form=form, user=user)

            if len(request.files.getlist('images')) > 5:
                flash("You can upload a maximum of 5 images", "danger")
                return render_template('report_form.html', form=form, user=user)

            # ===== CREATE ITEM =====
            
            new_item = Item(
                name=form.name.data,
                description=form.description.data,
                category_id=form.category_id.data,
                reporter_id=user['id'],
                status=form.report_type.data
            )
            
            # For found reports, set the finder info
            if form.report_type.data == 'found':
                new_item.found_by_id = user['id']
                new_item.found_at = form.event_datetime.data or datetime.now()
            
            db.session.add(new_item)
            db.session.commit()
            log_action(user['id'], 'items', new_item.id, 'create', changes=f"Item {new_item.name} created.")

            # ===== HANDLE IMAGES =====
            
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
                        image_url=image_path,
                    )
                    db.session.add(new_image)
                    db.session.commit()
                    log_action(user['id'], 'item_images', new_image.id, 'create', changes=f"Image for item {new_item.name} added.")

            # ===== CREATE REPORT =====
            
            # Check for lost reports - cannot be anonymous
            if form.report_type.data == 'lost' and form.is_anonymous.data:
                flash("Lost reports cannot be anonymous", "danger")
                return render_template('report_form.html', form=form, user=user)
            
            # Check contact info requirements
            if form.report_type.data == 'lost' and not form.contact_info.data:
                flash("Contact info is required for lost reports", "danger")
                return render_template('report_form.html', form=form, user=user)
            
            current_app.logger.info("Creating report with contact info: %s", form.contact_info.data)
            
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
            
            # ===== CREATE VERIFICATION QUESTION =====
            
            # Only for found reports (not lost)
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
            flash(f"An error occurred: {str(e)}", "danger")
            return render_template('report_form.html', form=form, user=user)

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
            
            if item:
                # Get images and extract URLs before any deletion
                images_to_delete = ItemImage.query.filter_by(item_id=item.id).all()
                image_urls = [img.image_url for img in images_to_delete]
                
                # Delete all claims for this item
                claims_to_delete = Claim.query.filter_by(item_id=item.id).all()
                for claim in claims_to_delete:
                    db.session.delete(claim)
                for image in images_to_delete:
                    db.session.delete(image)
            
            # Delete the report and item
            db.session.delete(report)
            if item:
                db.session.delete(item)
            
            # Commit all deletions
            db.session.commit()
            
            # Delete image files from filesystem
            for image_url in image_urls:
                current_app.logger.info(f"Deleting image file: {image_url}")
                try:
                    if os.path.exists(image_url):
                        os.remove(image_url)
                except OSError as e:
                    current_app.logger.error(f"Failed to delete image file {image_url}: {e}")
                    
            log_action(user['id'], 'reports', report.id, 'delete', changes=f"Report and item {item_name} deleted.")

            return make_response(jsonify({
                "message": "Report and all associated data deleted successfully",
                "report_id": report.id
            }), 200)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Deletion failed: {e}")
            return make_response(jsonify({"error": "Deletion failed"}), 500)
            
    elif request.method == 'GET':
        # GET method implementation (pagination/filtering)
        # This part looks mostly correct, but need to update for new fields
        try:
            # Parse query parameters with defaults
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 12, type=int)
            search_text = request.args.get('search', '').strip()
            status_filter = request.args.get('status', '').strip()
            category_filter = request.args.get('category', '').strip()
            date_filter = request.args.get('date', '').strip()
            location_filter = request.args.get('location', '').strip()
            
            # Validate parameters
            if page < 1:
                page = 1
            if per_page < 1:
                per_page = 12
            if per_page > 100:
                per_page = 100
            
            # Start building the query
            query = Item.query
            
            # Join necessary tables for filtering and eager loading
            query = query.join(Report, Item.id == Report.item_id)
            query = query.outerjoin(Location, Report.location_id == Location.id)
            query = query.join(Category, Item.category_id == Category.id)
            query = query.outerjoin(ItemImage, Item.id == ItemImage.item_id)
            
            # Eager load relationships to prevent N+1 queries
            query = query.options(
                db.joinedload(Item.reporter),
                db.joinedload(Item.claimed_by),
                db.joinedload(Item.found_by),
                db.joinedload(Item.category),
                db.joinedload(Item.images),
                db.joinedload(Item.reports).joinedload(Report.location)
            )
            
            # Apply text search if provided
            if search_text:
                search_term = f"%{search_text}%"
                query = query.filter(
                    or_(
                        Item.name.ilike(search_term),
                        Item.description.ilike(search_term),
                        Report.additional_details.ilike(search_term),
                        Location.name.ilike(search_term),
                        Report.specific_spot.ilike(search_term)
                    )
                )
            
            # Apply status filter (now includes more statuses)
            if status_filter in ['lost', 'found']:
                query = query.filter(Item.status == status_filter)
            
            # Apply category filter
            if category_filter and category_filter.isdigit():
                query = query.filter(Item.category_id == int(category_filter))
            
            # Apply date filter
            if date_filter:
                try:
                    filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                    query = query.filter(func.date(Item.created_at) == filter_date.isoformat())
                except ValueError:
                    pass
                        
            # Apply location filter
            if location_filter:
                location_term = f"%{location_filter}%"
                query = query.filter(
                    or_(
                        Location.name.ilike(location_term),
                        Report.specific_spot.ilike(location_term)
                    )
                )
            
            # Order by most recent first
            query = query.order_by(Item.created_at.desc())
            
            # Apply pagination
            items = query.paginate(page=page, per_page=per_page, error_out=False)
            
            # Serialize items
            serialized_items = []
            for item in items.items:
                if item.status not in ['lost', 'found']:
                    continue
                item_dict = item.to_dict()
                
                # Add location_name from the first report
                if item.reports:
                    report = item.reports[0]
                    item_dict['location_name'] = report.location.name if report.location else None
                    item_dict['specific_spot'] = report.specific_spot
                    item_dict['is_anonymous'] = report.is_anonymous
                else:
                    item_dict['location_name'] = None
                    item_dict['specific_spot'] = None
                    item_dict['is_anonymous'] = False
                
                # Ensure images array is always present
                if 'images' not in item_dict:
                    item_dict['images'] = []
                
                # Hide reporter info for anonymous reports
                if item.reports and item.reports[0].is_anonymous:
                    item_dict['reporter_name'] = None
                    item_dict['contact_info'] = None
                
                serialized_items.append(item_dict)
                            
            # Build response
            response = {
                'items': serialized_items,
                'has_more': items.has_next,
                'total': items.total,
                'page': items.page,
                'pages': items.pages,
                'per_page': items.per_page
            }
            
            return jsonify(response), 200
            
        except Exception as e:
            current_app.logger.error(f"Error fetching items: {str(e)}")
            return jsonify({
                'error': 'Failed to fetch items',
                'message': str(e) if current_app.debug else 'Internal server error'
            }), 500


@lost_and_found.route('/lost_and_found/update_report', methods=['POST'])
@login_required
def update_report(user):
    """Handle report updates (using _method=PUT)"""
    report = None
    removed_image_urls = []
    
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
        
        # Populate choices for validation
        categories = Category.query.all()
        form.category_id.choices = [(c.id, c.name) for c in categories]
        
        locations = Location.query.all()
        form.location_id.choices = [(l.id, l.name) for l in locations]
        
        # Get report type from form or use existing
        report_type = request.form.get('report_type', report.report_type)
        
        if not form.validate_on_submit():
            # Return form with validation errors
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)
        
        # ===== VALIDATIONS =====
        
        if len(form.name.data) > NAME_LIMIT:
            flash(f"Item name must be less than {NAME_LIMIT} characters", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        if (len(form.description.data) > DESCRIPTION_LIMIT or
            len(form.additional_details.data) > DESCRIPTION_LIMIT or
            (form.verification_question.data and len(form.verification_question.data) > DESCRIPTION_LIMIT)):
            flash(f"Text fields must be less than {DESCRIPTION_LIMIT} characters", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # Category validation
        category_ids = [category.id for category in categories]
        if form.category_id.data not in category_ids:
            flash("Invalid category", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # Location validation
        if form.location_id.data:
            location_ids = [location.id for location in locations]
            if form.location_id.data not in location_ids:
                flash("Invalid location", "danger")
                return render_template('lost_and_found/_edit_form_fields.html', 
                                     form=form, 
                                     report=report)

        # Date validation
        if form.event_datetime.data:
            if (form.event_datetime.data > datetime.now() or
                form.event_datetime.data < datetime.now() - timedelta(days=30)):
                flash("Date must be within the last 30 days and not in the future", "danger")
                return render_template('lost_and_found/_edit_form_fields.html', 
                                     form=form, 
                                     report=report)

        # Lost reports cannot be anonymous
        if report_type == 'lost' and form.is_anonymous.data:
            flash("Lost reports cannot be anonymous", "danger")
            # Force is_anonymous to False for lost reports
            form.is_anonymous.data = False

        # Calculate image count
        current_image_count = len(report.item.images)
        new_images_count = sum(1 for img in form.images.data if img and img.filename)
        remove_image_ids = request.form.getlist('remove_images')
        
        final_image_count = current_image_count - len(remove_image_ids) + new_images_count
        
        if final_image_count > 5:
            flash("Total images cannot exceed 5", "danger")
            return render_template('lost_and_found/_edit_form_fields.html', 
                                 form=form, 
                                 report=report)

        # ===== HANDLE IMAGE REMOVAL =====
        
        if remove_image_ids:
            images_to_remove = ItemImage.query.filter(
                ItemImage.id.in_(remove_image_ids),
                ItemImage.item_id == report.item_id
            ).all()
            
            for image in images_to_remove:
                # Store relative path for cleanup
                
                removed_image_urls.append(image.image_url)
                db.session.delete(image)
        
        # ===== HANDLE NEW IMAGE UPLOADS =====
        
        uploaded_files = []
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
                        item_id=report.item_id,
                        image_url=image_path,
                    )
                    db.session.add(new_image)
                    db.session.commit()
                    log_action(user['id'], 'item_images', new_image.id, 'create', changes=f"Image for item {report.item.name} added.")
        
        # ===== UPDATE REPORT DATA =====
        
        # Report type cannot be changed - use existing
        report.is_anonymous = form.is_anonymous.data
        
        # ALWAYS save contact info (regardless of anonymity)
        # This is important because even if the finder wants to be anonymous,
        # they still need to provide contact info for the system
        report.contact_info = form.contact_info.data
        
        report.additional_details = form.additional_details.data
        report.location_id = form.location_id.data
        report.specific_spot = form.specific_spot.data
        report.event_datetime = form.event_datetime.data
        
        # ===== UPDATE ITEM DATA =====
        
        report.item.name = form.name.data
        report.item.description = form.description.data
        report.item.category_id = form.category_id.data
        
        # Handle verification question based on report type
        if report_type == 'found':
            if form.verification_question.data:
                vq = VerificationQuestion.query.filter_by(report_id=report.id).first()
                if vq:
                    vq.question = form.verification_question.data
                else:
                    vq = VerificationQuestion(
                        report_id=report.id,
                        question=form.verification_question.data
                    )
                    db.session.add(vq)
            else:
                # Remove verification question if empty for found report
                VerificationQuestion.query.filter_by(report_id=report.id).delete()
        else:
            # For lost reports, remove any existing verification questions
            VerificationQuestion.query.filter_by(report_id=report.id).delete()
        
        # Update timestamps
        report.updated_at = datetime.now()
        report.item.updated_at = datetime.now()
        
        # SINGLE COMMIT FOR ALL DATABASE CHANGES
        db.session.commit()
        
        # CLEAN UP REMOVED IMAGE FILES AFTER SUCCESSFUL COMMIT
        for image_path in removed_image_urls:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except OSError as e:
                current_app.logger.error(f"Failed to delete image file {image_path}: {e}")
                
        log_action(user['id'], 'reports', report.id, 'update', changes=f"Report for item {report.item.name} updated.")
        
        flash('Report updated successfully!', 'success')
        return redirect(url_for('main.profile'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating report {report.id if report else 'unknown'}: {str(e)}")
        
        # CLEAN UP ANY UPLOADED FILES ON ERROR
        if 'uploaded_files' in locals():
            for file_path in uploaded_files:
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except OSError as cleanup_error:
                    current_app.logger.error(f"Failed to cleanup uploaded file {file_path}: {cleanup_error}")
        
        flash('An error occurred while updating the report', 'error')
        return redirect(url_for('main.profile'))


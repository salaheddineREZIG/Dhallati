from datetime import datetime, timedelta
import json
from flask import jsonify, request, current_app, render_template, flash, redirect, url_for, g
from sqlalchemy.orm import joinedload
from .. import lost_and_found
from app.decorators import login_required
from app.lost_and_found.models import Item, Report, User, Notification, Claim
from app import db
from datetime import datetime
from sqlalchemy.orm import joinedload


# ---------- Report Finding Lost Item ---------- #
@lost_and_found.route("/lost_and_found/api/report_found/<int:item_id>", methods=['POST'])
@login_required
def report_found_item(user, item_id):
    """
    Handle when a user reports finding a lost item
    """
    try:
        data = request.get_json()
        action = data.get('action')
        
        item = Item.query.options(
            joinedload(Item.reports),
            joinedload(Item.reporter)
        ).filter_by(id=item_id).first()
        
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        report = Report.query.filter_by(item_id=item_id).first()
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Verify the item is lost
        if item.status != 'lost':
            return jsonify({'error': 'Item is not marked as lost'}), 400
        
        # User cannot find their own lost item
        if report.reporter_id == user['id']:
            return jsonify({'error': 'Cannot find your own lost item'}), 400
        
        if action == 'found_lost_item':
            # Get claimant user info
            claimant_user = User.query.get(user['id'])
            # Get reporter's contact info
            reporter_user = User.query.get(report.reporter_id)
            
            # Create a pending claim for the lost item
            claim = Claim(
                item_id=item_id,
                claimant_id=user['id'],  # The person who found it
                reporter_id=report.reporter_id,  # The person who lost it
                verification_answers=json.dumps({
                    'message': 'Found this lost item',
                    'action': 'found_lost_item',
                }),
                status='pending',
                expires_at=datetime.utcnow() + timedelta(days=7)
            )
            db.session.add(claim)
            
            db.session.flush()
            
            # Create notification for reporter - include claimant's info
            notification_message = f"{claimant_user.name} found your lost item '{item.name}'. "
            
            # Add claimant contact info to notification
            
            notification = Notification(
                user_id=report.reporter_id,
                item_id=item_id,
                claim_id=claim.id,
                notification_type='claim_request',
                message=notification_message
            )
            db.session.add(notification)
            
            db.session.commit()
            
            # Return reporter's contact info for lost items (lost reports are never anonymous)
            reporter_contact = {
                'name': reporter_user.name,
                'email': reporter_user.email,
                'phone': report.contact_info if report.contact_info else "Not provided"
            }
            
            return jsonify({
                'success': True,
                'message': 'Claim request submitted. Here is the owner\'s contact information:',
                'claim_id': claim.id,
                'reporter_contact_info': reporter_contact,
                'is_anonymous': False  # Lost reports are never anonymous
            }), 200
            
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error reporting found item: {str(e)}")
        return jsonify({'error': 'Failed to process request'}), 500


# ---------- Claim Found Item ---------- #
# ---------- Claim Found Item ---------- #
@lost_and_found.route("/lost_and_found/api/claim/<int:item_id>", methods=['POST'])
@login_required
def claim_item(user, item_id):
    """
    Handle when a user claims a found item (reporter found an item, claimant wants it)
    """
    try:
        data = request.get_json()
        verification_answers = data.get('verification_answers', {})
        
        item = Item.query.options(
            joinedload(Item.reports),
            joinedload(Item.reporter),
            joinedload(Item.claims)
        ).filter_by(id=item_id).first()
        
        if not item:
            return jsonify({'error': 'Item not found'}), 404
        
        report = Report.query.filter_by(item_id=item_id).first()
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Verify the item is claimable (found status)
        if item.status != 'found':
            return jsonify({'error': 'Item is not available for claim'}), 400
        
        # User cannot claim their own found item
        if report.reporter_id == user['id']:
            return jsonify({'error': 'Cannot claim your own found item'}), 400
        
        # Check if user already has a pending claim
        existing_claim = Claim.query.filter_by(
            item_id=item_id,
            claimant_id=user['id'],
            status='pending'
        ).first()
        
        if existing_claim:
            return jsonify({'error': 'You already have a pending claim for this item'}), 400
        
        # Get claimant user info
        claimant_user = User.query.get(user['id'])
        # Get reporter's contact info
        reporter_user = User.query.get(report.reporter_id)
        
        # Create the claim
        claim = Claim(
            item_id=item_id,
            claimant_id=user['id'],
            reporter_id=report.reporter_id,
            verification_answers=json.dumps(verification_answers) if verification_answers else None,
            status='pending',
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.session.add(claim)
        
        db.session.flush()
        
        # Create notification for reporter - ALWAYS include claimant's name and contact
        notification_message = f"{claimant_user.name} wants to claim your found item '{item.name}'. "
        
        notification = Notification(
            user_id=report.reporter_id,
            item_id=item_id,
            claim_id=claim.id,
            notification_type='claim_request',
            message=notification_message
        )
        db.session.add(notification)
        
        db.session.commit()
        
        # Return response based on report anonymity
        if not report.is_anonymous:
            # Non-anonymous report: give reporter's contact info to claimant immediately
            reporter_contact = {
                'name': reporter_user.name,
                'email': reporter_user.email,
                'phone': report.contact_info if report.contact_info else "Not provided"
            }
            
            return jsonify({
                'success': True,
                'message': 'Claim submitted successfully. Here is the reporter\'s contact information:',
                'claim_id': claim.id,
                'reporter_contact_info': reporter_contact,
                'note': 'Please contact the reporter to arrange pickup.',
                'is_anonymous': False
            }), 200
        else:
            # Anonymous report: DO NOT give reporter's contact info
            return jsonify({
                'success': True,
                'message': 'Claim request submitted to the reporter. Since this was an anonymous report, you will receive their contact information if they accept your claim.',
                'claim_id': claim.id,
                'is_anonymous': True
            }), 200
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error claiming item: {str(e)}")
        return jsonify({'error': 'Failed to process claim'}), 500


# ---------- Manage Claims (for reporters) ---------- #
@lost_and_found.route("/lost_and_found/api/claims/<int:claim_id>/respond", methods=['POST'])
@login_required
def respond_to_claim(user, claim_id):
    """
    Reporter responds to a claim (accept/reject)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        action = data.get('action')  # 'accept' or 'reject'
        reason = data.get('reason', '')
        
        claim = Claim.query.options(
            joinedload(Claim.item).joinedload(Item.reports),
            joinedload(Claim.item).joinedload(Item.category),
            joinedload(Claim.claimant),
            joinedload(Claim.reporter)
        ).filter_by(id=claim_id).first()
        
        if not claim:
            return jsonify({'error': 'Claim not found'}), 404
        
        # Verify user is the reporter
        if claim.reporter_id != user['id']:
            return jsonify({'error': 'Not authorized'}), 403
        
        # Verify claim is pending
        if claim.status != 'pending':
            return jsonify({'error': 'Claim is not pending'}), 400
        
        item = claim.item
        if not item.reports:
            return jsonify({'error': 'Item report not found'}), 404
            
        report = item.reports[0]  # Get the first report
        
        if action == 'accept':
            # Accept the claim
            claim.status = 'accepted'
            claim.resolved_at = datetime.utcnow()
            claim.reason = reason if reason else "Claim accepted"
            
            # Update item based on report type
            if report.report_type == 'lost':
                # For lost items, mark as "recovered" when claim is accepted
                item.status = 'recovered'
                item.found_by_id = claim.claimant_id
                item.found_at = datetime.utcnow()
                item.claimed_by_id = claim.claimant_id
                item.claimed_at = datetime.utcnow()
            else:
                # For found items, mark as claimed
                item.status = 'claimed'
                item.claimed_by_id = claim.claimant_id
                item.claimed_at = datetime.utcnow()
            
            # Reject all other pending claims for this item
            other_claims = Claim.query.filter_by(
                item_id=item.id,
                status='pending'
            ).filter(Claim.id != claim_id).all()
            
            for other_claim in other_claims:
                other_claim.status = 'rejected'
                other_claim.resolved_at = datetime.utcnow()
                other_claim.reason = "Another claim was accepted"
                
                # Notify other claimants
                notification = Notification(
                    user_id=other_claim.claimant_id,
                    item_id=item.id,
                    claim_id=other_claim.id,
                    notification_type='claim_rejected',
                    message=f"Your claim for item '{item.name}' was rejected because another claim was accepted."
                )
                db.session.add(notification)
            
            # Get reporter's contact info from the report
            reporter_contact_info = report.contact_info if report.contact_info else "Not provided"
            
            # Check if report is anonymous
            if report.is_anonymous:
                # For anonymous reports, share the reporter's contact info with claimant
                notification_message = f"Your claim for item '{item.name}' has been accepted! "
                notification_message += f"The reporter's contact info: {reporter_contact_info}"
                
                # Also share reporter's name and email (since report was anonymous)
                reporter_user = User.query.get(claim.reporter_id)
                if reporter_user:
                    notification_message += f"\nReporter: {reporter_user.name} ({reporter_user.email})"
            else:
                # For non-anonymous reports, claimant already has contact info
                notification_message = f"Your claim for item '{item.name}' has been accepted! "
                notification_message += "Please contact the reporter using the contact information provided in the original report."
            
            # Notify claimant
            claimant_notification = Notification(
                user_id=claim.claimant_id,
                item_id=item.id,
                claim_id=claim.id,
                notification_type='claim_accepted',
                message=notification_message
            )
            db.session.add(claimant_notification)
            
            # Notify reporter of acceptance
            reporter_notification_message = f"You accepted the claim for item '{item.name}' by {claim.claimant.name}."
            
            # Add claimant's contact info for reporter
            claimant_user = User.query.get(claim.claimant_id)
            if claimant_user:
                reporter_notification_message += f"\nClaimant contact: {claimant_user.name} ({claimant_user.email})"
            
            # Check if claimant provided additional contact info in verification answers
            if claim.verification_answers:
                try:
                    import json
                    answers = json.loads(claim.verification_answers)
                    if isinstance(answers, dict):
                        # Look for contact info in answers
                        for key, value in answers.items():
                            if 'contact' in key.lower() or 'phone' in key.lower() or 'email' in key.lower():
                                reporter_notification_message += f"\nAdditional contact info: {key}: {value}"
                except:
                    pass
            
            reporter_notification = Notification(
                user_id=claim.reporter_id,
                item_id=item.id,
                claim_id=claim.id,
                notification_type='item_returned' if report.report_type == 'lost' else 'claim_accepted_confirmation',
                message=reporter_notification_message
            )
            db.session.add(reporter_notification)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Claim accepted successfully'
            }), 200            
        elif action == 'reject':
            # Reject the claim
            claim.status = 'rejected'
            claim.resolved_at = datetime.utcnow()
            claim.reason = reason if reason else "Claim rejected"
            
            # Notify claimant
            notification_message = f"Your claim for item '{item.name}' was rejected."
            if reason:
                notification_message += f" Reason: {reason}"
            
            notification = Notification(
                user_id=claim.claimant_id,
                item_id=item.id,
                claim_id=claim.id,
                notification_type='claim_rejected',
                message=notification_message
            )
            db.session.add(notification)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Claim rejected successfully'
            }), 200
            
        else:
            return jsonify({'error': 'Invalid action. Use "accept" or "reject"'}), 400
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error responding to claim: {str(e)}")
        return jsonify({'error': 'Failed to process response'}), 500


# ---------- Get User's Claims ---------- #
@lost_and_found.route("/lost_and_found/api/my_claims", methods=['GET'])
@login_required
def get_my_claims(user):
    """
    Get all claims made by or for the current user
    """
    try:
        # Claims made by user
        claims_made = Claim.query.options(
            joinedload(Claim.item),
            joinedload(Claim.reporter)
        ).filter_by(claimant_id=user['id']).all()
        
        # Claims received by user (as reporter)
        claims_received = Claim.query.options(
            joinedload(Claim.item),
            joinedload(Claim.claimant)
        ).filter_by(reporter_id=user['id']).all()
        
        # Convert to dictionaries with proper relationship handling
        claims_made_data = []
        for claim in claims_made:
            claim_dict = claim.to_dict()
            if claim.item:
                claim_dict['item'] = {
                    'id': claim.item.id,
                    'name': claim.item.name,
                    'image_url': claim.item.to_dict().get('images')[0]['image_url'] if claim.item.to_dict().get('images') else None,
                    'description': claim.item.description,
                    'category_id': claim.item.to_dict()["category_name"] if "category_name" in claim.item.to_dict() else None
                }
                current_app.logger.debug(f"Claim Item Images: {claim_dict['item']['image_url']}")
            if claim.reporter:
                claim_dict['reporter'] = {
                    'id': claim.reporter.id,
                    'name': claim.reporter.name,
                    'email': claim.reporter.email
                }
            claims_made_data.append(claim_dict)
        
        claims_received_data = []
        for claim in claims_received:
            claim_dict = claim.to_dict()
            if claim.item:
                claim_dict['item'] = {
                    'id': claim.item.id,
                    'name': claim.item.name,
                    'image_url': claim.item.to_dict().get('images')[0]['image_url'] if claim.item.to_dict().get('images') else None,
                    'description': claim.item.description,
                    'category_id': claim.item.to_dict()["category_name"] if "category_name" in claim.item.to_dict() else None
                }
            if claim.claimant:
                claim_dict['claimant'] = {
                    'id': claim.claimant.id,
                    'name': claim.claimant.name,
                    'email': claim.claimant.email
                }
            claims_received_data.append(claim_dict)
        
        return jsonify({
            'claims_made': claims_made_data,
            'claims_received': claims_received_data
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f"Error getting claims: {str(e)}")
        return jsonify({'error': 'Failed to get claims'}), 500


# ---------- Cancel Claim (for claimant) ---------- #
@lost_and_found.route("/lost_and_found/api/claims/<int:claim_id>/cancel", methods=['POST'])
@login_required
def cancel_claim(user, claim_id):
    """
    Claimant cancels their own pending claim
    """
    try:
        claim = Claim.query.options(
            joinedload(Claim.item)
        ).filter_by(id=claim_id).first()
        
        if not claim:
            return jsonify({'error': 'Claim not found'}), 404
        
        # Verify user is the claimant
        if claim.claimant_id != user['id']:
            return jsonify({'error': 'Not authorized'}), 403
        
        # Verify claim is pending
        if claim.status != 'pending':
            return jsonify({'error': 'Only pending claims can be cancelled'}), 400
        
        # Cancel the claim
        claim.status = 'cancelled'
        claim.resolved_at = datetime.utcnow()
        claim.reason = "Cancelled by claimant"
        
        # Notify reporter
        notification = Notification(
            user_id=claim.reporter_id,
            item_id=claim.item_id,
            claim_id=claim.id,
            notification_type='claim_cancelled',
            message=f"Claim for item '{claim.item.name}' was cancelled by the claimant."
        )
        db.session.add(notification)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Claim cancelled successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error cancelling claim: {str(e)}")
        return jsonify({'error': 'Failed to cancel claim'}), 500


# ---------- Claims Management Page ---------- #
@lost_and_found.route("/lost_and_found/claims/manage", methods=['GET'])
@login_required
def claims_management(user):
    """
    Page for managing claims
    """
    try:
        claim_id = request.args.get('claim_id')
        
        if claim_id:
            # Load specific claim
            claim = Claim.query.options(
                joinedload(Claim.item).joinedload(Item.images),  # Added this
                joinedload(Claim.claimant),
                joinedload(Claim.reporter)
            ).filter_by(id=claim_id).first()
            
            if not claim:
                flash("Claim not found", "danger")
                return redirect(url_for('lost_and_found.claims_management'))
            
            # Check if user is authorized to view this claim
            if claim.reporter_id != user['id'] and claim.claimant_id != user['id']:
                flash("Not authorized to view this claim", "danger")
                return redirect(url_for('lost_and_found.claims_management'))
            
            # Get item images if available
            item_images = claim.item.images if claim.item.images else []
            first_image = item_images[0] if item_images else None
            
            # Build claim dictionary with nested objects
            claim_dict = claim.to_dict()
            claim_dict['item'] = {
                'id': claim.item.id,
                'name': claim.item.name,
                'images': [img.to_dict() for img in item_images],  # Store all images
                'first_image_url': first_image.image_url if first_image else None,  # Store first image URL
                'description': claim.item.description,
                'category_id': claim.item.category_id,
                'category_name': claim.item.category.name if claim.item.category else None
            }
            claim_dict['claimant'] = {
                'id': claim.claimant.id,
                'name': claim.claimant.name,
                'email': claim.claimant.email
            }
            
            # Check if reporter is anonymous
            is_anonymous = False
            if claim.item.reports:
                is_anonymous = claim.item.reports[0].is_anonymous
            
            if is_anonymous and not claim.status == 'accepted':
                claim_dict['reporter'] = {
                    'id': None,
                    'name': 'Anonymous',
                    'email': None
                }
            else:
                claim_dict['reporter'] = {
                    'id': claim.reporter.id,
                    'name': claim.reporter.name,
                    'email': claim.reporter.email
                }
            
            return render_template('lost_and_found/claim_detail.html', claim=claim_dict, user={
                'name': user['name'],
                'profile_pic': user['profile_pic'],
                'id': user['id']
            })
        
        # Otherwise show all claims
        return render_template('lost_and_found/claims_management.html', user={
            'name': user['name'],
            'profile_pic': user['profile_pic']
        })
        
    except Exception as e:
        current_app.logger.exception(f"Error loading claims management: {str(e)}")
        flash("An error occurred while loading claims", "danger")
        return redirect(url_for('lost_and_found.lost_and_found_page'))
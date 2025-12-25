from flask import request, jsonify, current_app
from .. import lost_and_found
from app.decorators import login_required
from app.lost_and_found.models import Item, Report, Notification, User
from app import db
from datetime import datetime
import json
@lost_and_found.route('/lost_and_found/api/report_found/<int:item_id>', methods=['POST'])
# ===== NEW CLAIM ENDPOINTS =====

@lost_and_found.route('/lost_and_found/claim/<int:item_id>', methods=['POST'])
@login_required
def create_claim(user, item_id):
    """Create a claim for a found item"""
    try:
        data = request.get_json()
        
        # Get the item
        item = Item.query.get_or_404(item_id)
        
        # Check if item can be claimed
        if not item.is_claimable():
            return jsonify({'error': 'This item cannot be claimed'}), 400
        
        # Check if user is the reporter (can't claim your own reported item)
        if item.reporter_id == user['id']:
            # Original owner can claim their lost item when found by someone else
            if item.status == 'found' and item.found_by_id != user['id']:
                pass  # Allow original owner to claim
            else:
                return jsonify({'error': 'You cannot claim your own reported item'}), 400
        
        # Check if user is the finder (can't claim what you found)
        if item.found_by_id == user['id']:
            return jsonify({'error': 'You cannot claim an item you found'}), 400
        
        # Check for existing pending claim
        existing_claim = Claim.query.filter_by(
            item_id=item_id,
            claimant_id=user['id'],
            status='pending'
        ).first()
        
        if existing_claim:
            return jsonify({'error': 'You already have a pending claim for this item'}), 400
        
        # Get the report
        report = Report.query.filter_by(item_id=item_id).first()
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        # Create claim
        claim = Claim(
            item_id=item_id,
            claimant_id=user['id'],
            reporter_id=report.reporter_id,
            verification_answers=json.dumps(data.get('answers', {})) if data.get('answers') else None,
            status='pending',
            expires_at=datetime.now() + timedelta(days=7)  # 7-day expiration
        )
        
        # Update item status
        item.status = 'claimed_pending'
        
        db.session.add(claim)
        db.session.commit()
        
        # Create notification for reporter
        notification = Notification(
            user_id=report.reporter_id,
            item_id=item_id,
            claim_id=claim.id,
            notification_type='claim_request',
            message=f"{user['name']} has submitted a claim for '{item.name}'"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Claim submitted successfully',
            'claim_id': claim.id
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating claim: {str(e)}")
        return jsonify({'error': str(e)}), 500


@lost_and_found.route('/lost_and_found/claim/<int:claim_id>/<action>', methods=['POST'])
@login_required
def handle_claim(user, claim_id, action):
    """Handle claim actions (accept, reject, cancel)"""
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        if action == 'accept':
            # Only reporter can accept
            if claim.reporter_id != user['id']:
                return jsonify({'error': 'Unauthorized'}), 403
            
            if claim.status != 'pending':
                return jsonify({'error': 'Claim is not pending'}), 400
            
            # Update claim
            claim.status = 'accepted'
            claim.resolved_at = datetime.now()
            
            # Update item
            item = claim.item
            item.status = 'claimed'
            item.claimed_by_id = claim.claimant_id
            item.claimed_at = datetime.now()
            
            # Reject all other pending claims for this item
            other_claims = Claim.query.filter(
                Claim.item_id == claim.item_id,
                Claim.id != claim.id,
                Claim.status == 'pending'
            ).all()
            
            for other_claim in other_claims:
                other_claim.status = 'rejected'
                other_claim.resolved_at = datetime.now()
                
                # Notify other claimants
                notification = Notification(
                    user_id=other_claim.claimant_id,
                    item_id=claim.item_id,
                    claim_id=other_claim.id,
                    notification_type='claim_rejected',
                    message=f"Your claim for '{item.name}' has been rejected as another claim was accepted"
                )
                db.session.add(notification)
            
            # Notify claimant
            notification = Notification(
                user_id=claim.claimant_id,
                item_id=claim.item_id,
                claim_id=claim.id,
                notification_type='claim_accepted',
                message=f"Your claim for '{item.name}' has been accepted!"
            )
            db.session.add(notification)
            
        elif action == 'reject':
            # Only reporter can reject
            if claim.reporter_id != user['id']:
                return jsonify({'error': 'Unauthorized'}), 403
            
            if claim.status != 'pending':
                return jsonify({'error': 'Claim is not pending'}), 400
            
            claim.status = 'rejected'
            claim.resolved_at = datetime.now()
            
            # Update item status back to found
            item = claim.item
            item.status = 'found'
            
            # Notify claimant
            notification = Notification(
                user_id=claim.claimant_id,
                item_id=claim.item_id,
                claim_id=claim.id,
                notification_type='claim_rejected',
                message=f"Your claim for '{item.name}' has been rejected"
            )
            db.session.add(notification)
            
        elif action == 'cancel':
            # Only claimant can cancel
            if claim.claimant_id != user['id']:
                return jsonify({'error': 'Unauthorized'}), 403
            
            if claim.status != 'pending':
                return jsonify({'error': 'Claim is not pending'}), 400
            
            claim.status = 'cancelled'
            claim.resolved_at = datetime.now()
            
            # Update item status back to found
            item = claim.item
            item.status = 'found'
            
            # Notify reporter
            notification = Notification(
                user_id=claim.reporter_id,
                item_id=claim.item_id,
                claim_id=claim.id,
                notification_type='claim_cancelled',
                message=f"{user['name']} has cancelled their claim for '{item.name}'"
            )
            db.session.add(notification)
            
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Claim {action}ed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error handling claim: {str(e)}")
        return jsonify({'error': str(e)}), 500
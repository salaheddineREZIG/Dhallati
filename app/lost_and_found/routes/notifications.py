from sqlalchemy import desc
from flask import jsonify, current_app
from .. import lost_and_found
from app.decorators import login_required
from app.lost_and_found.models import Notification
from app import db
# ---------- Notifications ---------- #
@lost_and_found.route("/lost_and_found/api/notifications", methods=['GET'])
@login_required
def get_notifications(user):
    """
    Get all notifications for the current user
    """
    try:
        # Get notifications for the user, ordered by most recent
        notifications = Notification.query.filter_by(
            user_id=user['id']
        ).order_by(
            desc(Notification.created_at)
        ).limit(50).all()  # Limit to 50 most recent notifications
        
        # Count unread notifications
        unread_count = Notification.query.filter_by(
            user_id=user['id'],
            is_read=False
        ).count()
        
        # Prepare notifications data
        notifications_data = []
        for notification in notifications:
            notification_dict = notification.to_dict()
            
            # Add link based on notification type
            if notification.notification_type == 'claim_request' and notification.claim_id:
                notification_dict['link'] = f"/lost_and_found/claims/manage?claim_id={notification.claim_id}"
            elif notification.notification_type == 'claim_request_anonymous' and notification.claim_id:
                notification_dict['link'] = f"/lost_and_found/claims/manage?claim_id={notification.claim_id}"
            elif notification.item_id:
                notification_dict['link'] = f"/lost_and_found/item?id={notification.item_id}"
            else:
                notification_dict['link'] = ""
            
            notifications_data.append(notification_dict)
        
        return jsonify({
            'notifications': notifications_data,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Failed to get notifications'}), 500


@lost_and_found.route("/lost_and_found/api/notifications/<int:notification_id>/read", methods=['POST'])
@login_required
def mark_notification_as_read(user, notification_id):
    """
    Mark a single notification as read
    """
    try:
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user['id']
        ).first()
        
        if not notification:
            return jsonify({'error': 'Notification not found'}), 404
        
        notification.is_read = True
        db.session.commit()
        
        # Return updated unread count
        unread_count = Notification.query.filter_by(
            user_id=user['id'],
            is_read=False
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500


@lost_and_found.route("/lost_and_found/api/notifications/read_all", methods=['POST'])
@login_required
def mark_all_notifications_as_read(user):
    """
    Mark all notifications as read for the current user
    """
    try:
        # Update all unread notifications for this user
        Notification.query.filter_by(
            user_id=user['id'],
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'unread_count': 0
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error marking all notifications as read: {str(e)}")
        return jsonify({'error': 'Failed to mark notifications as read'}), 500


@lost_and_found.route("/lost_and_found/api/notifications/count", methods=['GET'])
@login_required
def get_notification_count(user):
    """
    Get only the count of unread notifications (for polling)
    """
    try:
        unread_count = Notification.query.filter_by(
            user_id=user['id'],
            is_read=False
        ).count()
        
        return jsonify({
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        current_app.logger.exception(f"Error getting notification count: {str(e)}")
        return jsonify({'error': 'Failed to get notification count'}), 500
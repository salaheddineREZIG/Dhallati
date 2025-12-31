from flask import jsonify, request, render_template, flash, redirect, url_for, make_response, current_app
from .. import lost_and_found
from config import Config
from app.decorators import login_required
from app.lost_and_found.models import Category, Item, Report, Location, User, Notification
from app import db
from sqlalchemy import or_, and_
from datetime import datetime
from sqlalchemy.orm import joinedload

def format_date(date_str):
    """Format date string to readable format"""
    try:
        if isinstance(date_str, str):
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date_obj = date_str
        
        return date_obj.strftime("%B %d, %Y at %I:%M %p")
    except:
        return date_str

@lost_and_found.route('/lost_and_found')
@login_required
def lost_and_found_page(user):
    user ={
        'name': user['name'],
        'profile_pic': user.get('profile_pic', None)
    }
    return render_template('lost_and_found.html', user=user)


@lost_and_found.route('/lost_and_found/categories', methods=['GET'])
@login_required
def get_categories(user):
    """
    Get all categories for filter dropdown.
    """
    try:
        categories = Category.query.order_by(Category.name).all()
        
        # Return minimal data needed for dropdown
        serialized_categories = [
            {
                'id': category.id,
                'name': category.name,
                'description': category.description
            }
            for category in categories
        ]
        
        return jsonify(serialized_categories), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch categories'
        }), 500
        
        
@lost_and_found.route('/items/search', methods=['POST'])
@login_required
def search_items(user):
    """
    Alternative search endpoint with POST for complex queries.
    Expected JSON body:
    {
        "search": "text to search",
        "filters": {
            "status": "lost"|"found",
            "category_ids": [1, 2, 3],
            "date_range": {
                "start": "2024-01-01",
                "end": "2024-01-31"
            },
            "location_ids": [1, 2]
        },
        "sort_by": "recent"|"oldest"|"name",
        "page": 1,
        "per_page": 12
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Parse parameters with defaults
        search_text = data.get('search', '').strip()
        filters = data.get('filters', {})
        sort_by = data.get('sort_by', 'recent')
        page = data.get('page', 1)
        per_page = data.get('per_page', 12)
        
        # Build query
        query = Item.query.join(Report).outerjoin(Location)
        
        # Apply text search
        if search_text:
            search_term = f"%{search_text}%"
            query = query.filter(
                or_(
                    Item.name.ilike(search_term),
                    Item.description.ilike(search_term),
                    Report.additional_details.ilike(search_term)
                )
            )
        
        # Apply status filter
        status = filters.get('status')
        if status in ['lost', 'found']:
            query = query.filter(Item.status == status)
        
        # Apply category filter
        category_ids = filters.get('category_ids', [])
        if category_ids:
            query = query.filter(Item.category_id.in_(category_ids))
        
        # Apply date range filter
        date_range = filters.get('date_range', {})
        start_date = date_range.get('start')
        end_date = date_range.get('end')
        
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(
                    and_(
                        Item.created_at >= start,
                        Item.created_at <= end
                    )
                )
            except ValueError:
                pass
        
        # Apply location filter
        location_ids = filters.get('location_ids', [])
        if location_ids:
            query = query.filter(Report.location_id.in_(location_ids))
        
        # Apply sorting
        if sort_by == 'oldest':
            query = query.order_by(Item.created_at.asc())
        elif sort_by == 'name':
            query = query.order_by(Item.name.asc())
        else:  # default: recent
            query = query.order_by(Item.created_at.desc())
        
        # Paginate
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Serialize results
        items = [item.to_dict() for item in paginated.items]
        
        return jsonify({
            'items': items,
            'has_more': paginated.has_next,
            'total': paginated.total,
            'page': paginated.page
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in search: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500
    
@lost_and_found.route('/lost_and_found/locations', methods=['GET'])
@login_required
def get_locations(user):
    """
    Get all locations for autocomplete/search suggestions.
    """
    try:
        search = request.args.get('search', '').strip()
        
        query = Location.query
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(Location.name.ilike(search_term))
        
        locations = query.order_by(Location.name).limit(20).all()
        
        serialized_locations = [
            {
                'id': loc.id,
                'name': loc.name,
                'description': loc.description
            }
            for loc in locations
        ]
        
        return jsonify(serialized_locations), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching locations: {str(e)}")
        return jsonify({'error': 'Failed to fetch locations'}), 500

@lost_and_found.route("/lost_and_found/item", methods=['GET'])
@login_required
def item(user):
    try:
        item_id = request.args.get('id')
        if not item_id:
            flash("Item ID is required", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))
        
        # Validate item_id is a number
        try:
            item_id = int(item_id)
        except ValueError:
            flash("Invalid item ID", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))
        
        # Get item with eager loading for better performance
        item = Item.query.options(
            joinedload(Item.category),
            joinedload(Item.reporter),
            joinedload(Item.claimed_by),
            joinedload(Item.images)
        ).filter_by(id=item_id).first()
        
        if not item:
            flash("Item not found", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))
        
        # Get report with related data
        report = Report.query.options(
            joinedload(Report.location),
            joinedload(Report.verification_questions)
        ).filter_by(item_id=item_id).first()
        
        if not report:
            flash("Report not found for this item", "danger")
            return redirect(url_for('lost_and_found.lost_and_found_page'))
        
        # Convert to dictionaries
        item_dict = item.to_dict()
        report_dict = report.to_dict()
        
        # Add location details
        if report.location:
            report_dict['location_name'] = report.location.name
            item_dict['location_name'] = report.location.name
        
        # Handle anonymous reports (only for found items)
        if report.is_anonymous and report.report_type == 'found':
            report_dict['reporter_name'] = "Anonymous User"
            report_dict['contact_info'] = "Contact via platform"
            item_dict['reporter_name'] = "Anonymous User"
            item_dict['claimed_by_name'] = None if item_dict['claimed_by_name'] == "Anonymous User" else item_dict['claimed_by_name']
        
        # Get verification questions for found items
        verification_questions = []
        if report.report_type == 'found' and report.verification_questions:
            for vq in report.verification_questions:
                verification_questions.append(vq.question)
        
        # Check if current user can claim this item
        can_claim = False
        claim_message = ""
        
        if item.status == 'found':
            # User cannot claim their own found item
            if report.reporter_id != user['id']:
                can_claim = True
                claim_message = "Request to Claim this Item"
            else:
                claim_message = "You reported this found item"
                
        elif item.status == 'lost':
            # For lost items, users can contact the reporter to say they found it
            if report.reporter_id != user['id']:
                can_claim = True
                claim_message = "I Found This Item"
            else:
                claim_message = "You reported this lost item"
                
        elif item.status == 'claimed':
            claim_message = f"Claimed by {item_dict.get('claimed_by_name', 'someone')}"
        
        # Format dates nicely
        if item_dict.get('created_at'):
            item_dict['formatted_date'] = format_date(item_dict['created_at'])
        if report_dict.get('created_at'):
            report_dict['formatted_date'] = format_date(report_dict['created_at'])
        if item_dict.get('claimed_at'):
            item_dict['formatted_claimed_date'] = format_date(item_dict['claimed_at'])
            
        current_app.logger.info(f"Rendering item detail for id={item_id} by user id={user['id']}" + f" (can_claim={can_claim})")
        
        user ={
        'name': user['name'],
        'profile_pic': user.get('profile_pic', None)
        }

        
        return render_template(
            'item_detail.html', 
            item=item_dict, 
            report=report_dict,
            verification_questions=verification_questions,
            can_claim=can_claim,
            claim_message=claim_message,
            item_id=item_id,
            reporter_id=report.reporter_id,
            user=user
        )
        
    except Exception as e:
        current_app.logger.exception(f"Failed to render item detail for id={request.args.get('id')}")
        flash(f"An error occurred while loading the item details", "danger")
        return redirect(url_for('lost_and_found.lost_and_found_page'))

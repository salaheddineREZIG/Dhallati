from datetime import datetime
from sqlalchemy import Enum, Text, DECIMAL, Index
from app import db
from app.constants import ITEM_STATUS, REPORT_TYPE, NOTIFICATION_TYPE


# Constants for Enums

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # Category name should be unique
    description = db.Column(db.Text, nullable=True)
    
    # Relationships
    items = db.relationship('Item', back_populates='category', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(Enum(*ITEM_STATUS, name='item_status'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)  # Foreign key to Category
    location_reported = db.Column(db.String(100))
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)
    image_url = db.Column(db.Text)  # This will now store multiple images in the related ItemImage table.

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id], back_populates='items_reported')
    claimed_by = db.relationship('User', foreign_keys=[claimed_by_id])
    reports = db.relationship('Report', back_populates='item', lazy='dynamic')
    matches_as_lost = db.relationship('Match', foreign_keys='Match.lost_item_id', back_populates='lost_item', lazy='dynamic')
    matches_as_found = db.relationship('Match', foreign_keys='Match.found_item_id', back_populates='found_item', lazy='dynamic')
    images = db.relationship('ItemImage', back_populates='item', lazy='dynamic')
    category = db.relationship('Category', back_populates='items')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.name,  # Use Enum's name attribute to get string representation
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'location_reported': self.location_reported,
            'reported_at': self.reported_at.isoformat() if self.reported_at else None,
            'reporter_id': self.reporter_id,
            'claimed_by_id': self.claimed_by_id,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'image_url': self.image_url,
            'reporter_name': self.reporter.username if self.reporter else None,
            'claimed_by_name': self.claimed_by.username if self.claimed_by else None,
            'images': [image.to_dict() for image in self.images],  # Include multiple images
        }


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    report_type = db.Column(Enum(*REPORT_TYPE, name='report_type'), nullable=False)
    location_reported = db.Column(db.String(100))
    additional_details = db.Column(db.Text)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    contact_info = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    item = db.relationship('Item', back_populates='reports')
    reporter = db.relationship('User', back_populates='reports')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'reporter_id': self.reporter_id,
            'report_type': self.report_type.name,
            'location_reported': self.location_reported,
            'additional_details': self.additional_details,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=True)
    notification_type = db.Column(Enum(*NOTIFICATION_TYPE, name='notification_type'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='notifications')
    item = db.relationship('Item')

    # Adding index on is_read for faster queries
    __table_args__ = (
        Index('ix_notifications_is_read', 'is_read'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'notification_type': self.notification_type.name,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at
        }


class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    match_score = db.Column(DECIMAL(precision=5, scale=2))  # More precise than Float
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_confirmed = db.Column(db.Boolean, default=False)

    # Relationships
    lost_item = db.relationship('Item', foreign_keys=[lost_item_id], back_populates='matches_as_lost')
    found_item = db.relationship('Item', foreign_keys=[found_item_id], back_populates='matches_as_found')

    def to_dict(self):
        return {
            'id': self.id,
            'lost_item_id': self.lost_item_id,
            'found_item_id': self.found_item_id,
            'match_score': float(self.match_score),  # Convert to float for JSON serialization
            'created_at': self.created_at,
            'is_confirmed': self.is_confirmed
        }


class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class ItemImage(db.Model):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    image_url = db.Column(db.Text, nullable=False)  # Changed to Text for longer URLs
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    item = db.relationship('Item', back_populates='images')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'image_url': self.image_url,
            'uploaded_at': self.uploaded_at
        }

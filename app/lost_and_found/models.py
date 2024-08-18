from datetime import datetime
from sqlalchemy import Enum
from app import db

# Constants for Enums
ITEM_STATUS = ('lost', 'found', 'returned', 'claimed')
REPORT_TYPE = ('lost', 'found')
NOTIFICATION_TYPE = ('match_found', 'status_update', 'new_item_reported')

class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    item_type = db.Column(db.String(50))
    item_category = db.Column(db.String(50))
    status = db.Column(Enum(*ITEM_STATUS, name='item_status'), nullable=False)
    image_url = db.Column(db.String(255))
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    location_reported = db.Column(db.String(100))
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id], back_populates='items_reported')
    claimed_by = db.relationship('User', foreign_keys=[claimed_by_id])
    reports = db.relationship('Report', back_populates='item', lazy='dynamic')
    matches_as_lost = db.relationship('Match', foreign_keys='Match.lost_item_id', back_populates='lost_item', lazy='dynamic')
    matches_as_found = db.relationship('Match', foreign_keys='Match.found_item_id', back_populates='found_item', lazy='dynamic')
    images = db.relationship('ItemImage', back_populates='item', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'item_type': self.item_type,
            'item_category': self.item_category,
            'status': self.status,
            'image_url': self.image_url,
            'reporter_id': self.reporter_id,
            'reported_at': self.reported_at,
            'location_reported': self.location_reported,
            'claimed_by_id': self.claimed_by_id,
            'claimed_at': self.claimed_at
        }

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(Enum(*REPORT_TYPE, name='report_type'), nullable=False)
    location_reported = db.Column(db.String(100))
    additional_details = db.Column(db.Text)
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
            'report_type': self.report_type,
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
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'notification_type': self.notification_type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at
        }

class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    match_score = db.Column(db.Float)  # Optional: a score indicating the likelihood of a match
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
            'match_score': self.match_score,
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
    image_url = db.Column(db.String(255), nullable=False)
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

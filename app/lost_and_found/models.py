# app/lost_and_found/models.py
from datetime import datetime
from app.constants import ReportType
import enum
from decimal import Decimal
from sqlalchemy import func, Index
from app import db
from app.auth.models import User


# ---------- Enums ---------- #
class ItemStatus(enum.Enum):
    LOST = "LOST"
    FOUND = "FOUND"
    CLAIMED = "CLAIMED"
    RETURNED = "RETURNED"



class NotificationType(enum.Enum):
    MATCH = "MATCH"
    CLAIM = "CLAIM"
    INFO = "INFO"


# helper
def enum_to_str(val):
    return getattr(val, 'value', val)


# ---------- Category ---------- #
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)

    items = db.relationship('Item', back_populates='category', lazy='select')

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


# ---------- Item ---------- #
class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(ItemStatus, name='item_status', native_enum=False), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    claimed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id], back_populates='items_reported', lazy='joined')
    claimed_by = db.relationship('User', foreign_keys=[claimed_by_id], lazy='joined')
    reports = db.relationship('Report', back_populates='item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    matches_as_lost = db.relationship('Match', foreign_keys='Match.lost_item_id', back_populates='lost_item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    matches_as_found = db.relationship('Match', foreign_keys='Match.found_item_id', back_populates='found_item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    images = db.relationship('ItemImage', back_populates='item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    category = db.relationship('Category', back_populates='items', lazy='joined')

    __table_args__ = (
        Index('ix_items_reporter_id', 'reporter_id'),
        Index('ix_items_claimed_by_id', 'claimed_by_id'),
    )

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} status={enum_to_str(self.status)}>"

    def to_dict(self, public: bool = True):
        """
        Serializes Item.
    
        """
        images = [img.to_dict() for img in (self.images or [])]

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': enum_to_str(self.status),
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'reporter_id': self.reporter_id if not public and self.reporter.to_dict(public) else None,
            'claimed_by_id': self.claimed_by_id,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'reporter_name': self.reporter.to_dict(public)['name'] if self.reporter and not public else None,
            'claimed_by_name': self.claimed_by.to_dict(public)['name'] if self.claimed_by and not public else None,
            'images': images
        }
        


# ---------- Report ---------- #
class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    report_type = db.Column(db.Enum(ReportType, name='report_type', native_enum=False), nullable=False, index=True)
    location_reported = db.Column(db.String(255), nullable=True)
    additional_details = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    contact_info = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    item = db.relationship('Item', back_populates='reports', lazy='joined')
    reporter = db.relationship('User', back_populates='reports', lazy='joined')

    def __repr__(self):
        return f"<Report id={self.id} item_id={self.item_id} type={enum_to_str(self.report_type)}>"

    def to_dict(self, public: bool = True):
        """
        Serializes Report.
        - If report is anonymous (is_anonymous==True) we DO NOT expose reporter name or contact_info in public mode.
        - public=False returns contact_info and reporter identifier for internal/admin use.
        """

        result = {
            'id': self.id,
            'item_id': self.item_id,
            'reporter_id': None,
            'report_type': enum_to_str(self.report_type),
            'location_reported': self.location_reported,
            'additional_details': self.additional_details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_anonymous': self.is_anonymous,
            'reporter_name': None,
            'contact_info': None
        }

        if not public:
            result.update({
                'reporter_id': self.reporter_id,
                'reporter_name': self.reporter.to_dict(public=True)['name'] if self.reporter else None,
                'contact_info': self.contact_info,
            })
        return result


# ---------- Notification ---------- #
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='SET NULL'), nullable=True, index=True)
    notification_type = db.Column(db.Enum(NotificationType, name='notification_type', native_enum=False), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', back_populates='notifications', lazy='joined')
    item = db.relationship('Item', lazy='joined')

    __table_args__ = (
        Index('ix_notifications_is_read', 'is_read'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'notification_type': enum_to_str(self.notification_type),
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ---------- Match ---------- #
class Match(db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    lost_item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    found_item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    match_score = db.Column(db.Numeric(precision=5, scale=2), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_confirmed = db.Column(db.Boolean, default=False, nullable=False)

    lost_item = db.relationship('Item', foreign_keys=[lost_item_id], back_populates='matches_as_lost', lazy='joined')
    found_item = db.relationship('Item', foreign_keys=[found_item_id], back_populates='matches_as_found', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'lost_item_id': self.lost_item_id,
            'found_item_id': self.found_item_id,
            'match_score': float(self.match_score) if self.match_score is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_confirmed': self.is_confirmed
        }


# ---------- Location ---------- #
class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


# ---------- ItemImage ---------- #
class ItemImage(db.Model):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = db.Column(db.Text, nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    item = db.relationship('Item', back_populates='images', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'image_url': self.image_url,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }

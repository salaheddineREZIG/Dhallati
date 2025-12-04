from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, Index, CheckConstraint, text, UniqueConstraint
from app import db
from app.auth.models import User


# Helper function (keeping for backward compatibility)
def enum_to_str(val):
    return getattr(val, 'value', val) if hasattr(val, 'value') else val


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


# ---------- Location ---------- #
class Location(db.Model):
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    reports = db.relationship('Report', back_populates='location', lazy='select')

    def __repr__(self):
        return f"<Location id={self.id} name={self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }


# ---------- Item ---------- #
class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, index=True)  # Plain string
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    claimed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )

    # Relationships
    reporter = db.relationship('User', foreign_keys=[reporter_id], back_populates='items_reported', lazy='joined')
    claimed_by = db.relationship('User', foreign_keys=[claimed_by_id], lazy='joined')
    reports = db.relationship('Report', back_populates='item', lazy='select')
    matches_as_lost = db.relationship('Match', foreign_keys='Match.lost_item_id', back_populates='lost_item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    matches_as_found = db.relationship('Match', foreign_keys='Match.found_item_id', back_populates='found_item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    images = db.relationship('ItemImage', back_populates='item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    category = db.relationship('Category', back_populates='items', lazy='joined')

    __table_args__ = (
        Index('ix_items_status_created', 'status', 'created_at'),
        Index('ix_items_reporter_created', 'reporter_id', 'created_at'),
        Index('ix_items_category_status', 'category_id', 'status'),
    )

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} status={self.status}>"

    def to_dict(self):
        images = [img.to_dict() for img in (self.images or [])]

        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'reporter_id': self.reporter_id if self.reporter else None,
            'reporter_name': self.reporter.to_dict()['name'] if self.reporter else None,
            'claimed_by_id': self.claimed_by_id if self.claimed_by else None,
            'claimed_by_name': self.claimed_by.to_dict()['name'] if self.claimed_by else None,
            'images': images
        }


# ---------- Report ---------- #
class Report(db.Model):
    __tablename__ = 'reports'
    
    __table_args__ = (
        UniqueConstraint('item_id', name='uq_report_item'),
        Index('ix_reports_type_created', 'report_type', 'created_at'),
        Index('ix_reports_user_created', 'reporter_id', 'created_at'),
        CheckConstraint(
            "contact_info GLOB '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'",
            name='ck_reports_contact_info_digits10'
        ),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    report_type = db.Column(db.String(20), nullable=False, index=True)  # Plain string
    
    additional_details = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    contact_info = db.Column(db.String(10), nullable=False)
    event_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # New location system
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='RESTRICT'), nullable=True, index=True)
    specific_spot = db.Column(db.String(255), nullable=True)

    # Relationships
    item = db.relationship('Item', back_populates='reports', lazy='joined')
    reporter = db.relationship('User', back_populates='reports', lazy='joined')
    location = db.relationship('Location', back_populates='reports', lazy='joined')

    def __repr__(self):
        return f"<Report id={self.id} item_id={self.item_id} type={self.report_type}>"

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'reporter_id': self.reporter_id,
            'report_type': self.report_type,
            'location_id': self.location_id,
            'specific_spot': self.specific_spot,
            'location_name': self.location.name if self.location else None,
            'additional_details': self.additional_details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_anonymous': self.is_anonymous,
            'reporter_name': self.reporter.name if self.reporter else None,
            'contact_info': self.contact_info,
        }


# ---------- VerificationQuestion ---------- #
class VerificationQuestion(db.Model):
    __tablename__ = 'verification_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    report = db.relationship('Report', backref=db.backref('verification_questions', lazy='select', cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'question': self.question,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ---------- Notification ---------- #
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='SET NULL'), nullable=True, index=True)
    notification_type = db.Column(db.String(20), nullable=False)  # Plain string
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = db.relationship('User', back_populates='notifications', lazy='joined')
    item = db.relationship('Item', lazy='joined', cascade='all, delete-orphan', single_parent=True)

    __table_args__ = (
        Index('ix_notifications_is_read', 'is_read'),
        Index('ix_notifications_user_created', 'user_id', 'created_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'notification_type': self.notification_type,
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

    __table_args__ = (
        Index('ix_matches_confirmed_score', 'is_confirmed', 'match_score'),
        
        CheckConstraint(
            "lost_item_id != found_item_id",
            name='ck_matches_different_items'
        ),
        
        CheckConstraint(
            "match_score IS NULL OR (match_score >= 0 AND match_score <= 100)",
            name='ck_matches_score_range'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'lost_item_id': self.lost_item_id,
            'found_item_id': self.found_item_id,
            'match_score': float(self.match_score) if self.match_score is not None else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_confirmed': self.is_confirmed
        }


# ---------- ItemImage ---------- #
class ItemImage(db.Model):
    __tablename__ = 'item_images'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    image_url = db.Column(db.String(2000), nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    item = db.relationship('Item', back_populates='images', lazy='joined')

    __table_args__ = (
        Index('ix_item_images_uploaded', 'uploaded_at'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'image_url': self.image_url,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func, Index, CheckConstraint, text, UniqueConstraint, Enum
from app import db
from app.auth.models import User
import enum


# Helper function (keeping for backward compatibility)
def enum_to_str(val):
    return getattr(val, 'value', val) if hasattr(val, 'value') else val


# ---------- Enums ---------- #
class ItemStatus(enum.Enum):
    LOST = 'lost'
    FOUND = 'found'
    CLAIMED_PENDING = 'claimed_pending'
    CLAIMED = 'claimed'
    RETURNED = 'returned'
    ARCHIVED = 'archived'


class ReportType(enum.Enum):
    LOST = 'lost'
    FOUND = 'found'


class ClaimStatus(enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'


class NotificationType(enum.Enum):
    ITEM_FOUND = 'item_found'
    ANONYMOUS_ITEM_FOUND = 'anonymous_item_found'
    CLAIM_REQUEST = 'claim_request'
    CLAIM_REQUEST_ANONYMOUS = 'claim_request_anonymous'
    CLAIM_ACCEPTED = 'claim_accepted'
    CLAIM_REJECTED = 'claim_rejected'
    CLAIM_CANCELLED = 'claim_cancelled'
    CLAIM_ACCEPTED_CONFIRMATION = 'claim_accepted_confirmation'
    ITEM_RETURNED = 'item_returned'


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
    status = db.Column(db.String(20), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=False, index=True)
    claimed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    claimed_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Found item tracking - who found it and when
    found_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    found_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Return tracking
    returned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    returned_to = db.Column(db.String(150), nullable=True)
    
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
    found_by = db.relationship('User', foreign_keys=[found_by_id], lazy='joined')
    reports = db.relationship('Report', back_populates='item', lazy='select')
    images = db.relationship('ItemImage', back_populates='item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)
    category = db.relationship('Category', back_populates='items', lazy='joined')
    claims = db.relationship('Claim', back_populates='item', lazy='select', cascade='all, delete-orphan', passive_deletes=True)

    __table_args__ = (
        Index('ix_items_status_created', 'status', 'created_at'),
        Index('ix_items_reporter_created', 'reporter_id', 'created_at'),
        Index('ix_items_category_status', 'category_id', 'status'),
        Index('ix_items_found_by', 'found_by_id'),
        CheckConstraint(
            "status IN ('lost', 'found', 'claimed_pending', 'claimed', 'returned', 'archived')",
            name='ck_items_valid_status'
        ),
        CheckConstraint(
            "NOT (status = 'lost' AND found_by_id IS NOT NULL)",
            name='ck_lost_item_not_found'
        ),
        CheckConstraint(
            "NOT (status = 'found' AND found_by_id IS NULL)",
            name='ck_found_item_has_finder'
        ),
    )

    def __repr__(self):
        return f"<Item id={self.id} name={self.name!r} status={self.status}>"

    def to_dict(self):
        images = [img.to_dict() for img in (self.images or [])]
        
        found_by_user = None
        if self.found_by:
            found_by_user = {
                'id': self.found_by.id,
                'name': self.found_by.name
            }
        
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
            'claimed_by_id': self.claimed_by_id,
            'claimed_by_name': self.claimed_by.name if self.claimed_by else None,
            'found_by_id': self.found_by_id,
            'found_by': found_by_user,
            'found_at': self.found_at.isoformat() if self.found_at else None,
            'returned_at': self.returned_at.isoformat() if self.returned_at else None,
            'returned_to': self.returned_to,
            'reporter_id': self.reporter_id,
            'reporter_name': self.reporter.name if self.reporter else None,
            'images': images,
            'has_pending_claims': any(claim.status == 'pending' for claim in self.claims) if self.claims else False
        }
    
    def is_claimable(self):
        return self.status in ['found', 'claimed_pending']
    
    def is_own_item(self, user_id):
        return self.reporter_id == user_id


# ---------- Report ---------- #
class Report(db.Model):
    __tablename__ = 'reports'
    
    __table_args__ = (
        Index('ix_reports_type_created', 'report_type', 'created_at'),
        Index('ix_reports_user_created', 'reporter_id', 'created_at'),
        Index('ix_reports_item_id', 'item_id'),
        CheckConstraint(
            "NOT (report_type = 'lost' AND is_anonymous = true)",
            name='ck_lost_reports_not_anonymous'
        ),
        CheckConstraint(
            "NOT (report_type = 'lost' AND (contact_info IS NULL OR contact_info = ''))",
            name='ck_lost_reports_have_contact'
        ),
        {'extend_existing': True}
    )

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=False, index=True)
    report_type = db.Column(db.String(20), nullable=False, index=True)
    
    additional_details = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    contact_info = db.Column(db.String(10), nullable=False)
    event_datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id', ondelete='RESTRICT'), nullable=True, index=True)
    specific_spot = db.Column(db.String(255), nullable=True)
    
    item = db.relationship('Item', back_populates='reports', lazy='joined')
    reporter = db.relationship('User', back_populates='reports', lazy='joined')
    location = db.relationship('Location', back_populates='reports', lazy='joined')
    verification_questions = db.relationship('VerificationQuestion', backref='report', lazy='select', cascade='all, delete-orphan')

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
            'location_reported': self.location.name if self.location else "Unknown",
            'additional_details': self.additional_details,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_anonymous': self.is_anonymous,
            'reporter_name': self.reporter.name if self.reporter else None,
            'contact_info': self.contact_info,
            'has_verification_questions': len(self.verification_questions) > 0 if self.verification_questions else False
        }
    
    def is_lost_report(self):
        return self.report_type == 'lost'
    
    def is_found_report(self):
        return self.report_type == 'found'


# ---------- VerificationQuestion ---------- #
class VerificationQuestion(db.Model):
    __tablename__ = 'verification_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'report_id': self.report_id,
            'question': self.question,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ---------- Claim ---------- #
class Claim(db.Model):
    __tablename__ = 'claims'
    
    __table_args__ = (
        Index('ix_claims_status_created', 'status', 'created_at'),
        Index('ix_claims_item_status', 'item_id', 'status'),
        Index('ix_claims_claimant_created', 'claimant_id', 'created_at'),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'cancelled')",
            name='ck_claims_valid_status'
        ),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    verification_answers = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    
    reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    item = db.relationship('Item', back_populates='claims', lazy='joined')
    claimant = db.relationship('User', foreign_keys=[claimant_id], backref='claims_made', lazy='joined')
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='claims_received', lazy='joined')

    def to_dict(self):
        verification_answers = None
        if self.verification_answers:
            import json
            verification_answers = json.loads(self.verification_answers)
        
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else None,
            'claimant_id': self.claimant_id,
            'claimant_name': self.claimant.name if self.claimant else None,
            'reporter_id': self.reporter_id,
            'reporter_name': self.reporter.name if self.reporter else None,
            'verification_answers': verification_answers,
            'status': self.status,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }
    
    def is_expired(self):
        if not self.expires_at or self.status != 'pending':
            return False
        return datetime.now(timezone=True) > self.expires_at
    
    def is_claimable_by_user(self, user_id):
        if self.status != 'pending':
            return False
        if self.is_expired():
            return False
        if self.claimant_id == user_id:
            return False
        if self.item.found_by_id == user_id:
            return False
        return True


# ---------- Notification ---------- #
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='SET NULL'), nullable=True, index=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claims.id', ondelete='CASCADE'), nullable=True, index=True)
    notification_type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user = db.relationship('User', back_populates='notifications', lazy='joined')
    item = db.relationship('Item', lazy='joined')
    claim = db.relationship('Claim', lazy='joined')

    __table_args__ = (
        Index('ix_notifications_is_read', 'is_read'),
        Index('ix_notifications_user_created', 'user_id', 'created_at'),
        CheckConstraint(
            "notification_type IN ('item_found', 'anonymous_item_found', 'claim_request', 'claim_request_anonymous', 'claim_accepted', 'claim_rejected', 'claim_cancelled', 'claim_accepted_confirmation', 'item_returned', 'claim_expired')",
            name='ck_notifications_valid_type'
        ),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else None,
            'claim_id': self.claim_id,
            'notification_type': self.notification_type,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
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
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
        }
from datetime import datetime
import enum
from sqlalchemy import func, Index, CheckConstraint
from app import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    profile_pic = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    items_reported = db.relationship('Item', foreign_keys='Item.reporter_id', back_populates='reporter', lazy='select')
    reports = db.relationship('Report', back_populates='reporter', lazy='select')
    notifications = db.relationship('Notification', back_populates='user', lazy='select')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='select')

    def __repr__(self):
        return f"<User id={self.id} name={self.name!r}>"

    def to_dict(self, public: bool = True):
        base = {
            'id': self.id,
            'name': self.name,
            'profile_pic': self.profile_pic,
            'email': self.email,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else None,
        }
        if public:
            return base
        base.update({
            'google_id': self.google_id,
            'is_active': self.is_active,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        })
        return base


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    performed_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    changes = db.Column(db.Text)

    user = db.relationship('User', back_populates='audit_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'action': self.action,
            'performed_by': self.performed_by,
            'performed_at': self.performed_at.isoformat() if self.performed_at else None,
            'changes': self.changes
        }
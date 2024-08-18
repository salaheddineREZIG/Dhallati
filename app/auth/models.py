from datetime import datetime
from app import db
from ..lost_and_found.models import Item

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_pic = db.Column(db.String(255))  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items_reported = db.relationship('Item',  foreign_keys='Item.reporter_id',back_populates='reporter', lazy='dynamic')
    reports = db.relationship('Report', back_populates='reporter', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'google_id': self.google_id,
            'email': self.email,
            'name': self.name,
            'profile_pic': self.profile_pic
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'insert', 'update', 'delete'
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changes = db.Column(db.Text)  # JSON or text describing the changes

    user = db.relationship('User')
    
    def to_dict(self):  
        return {
            'id': self.id,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'action': self.action,
            'performed_by': self.performed_by,
            'performed_at': self.performed_at,
            'changes': self.changes
        }

from app.constants import ALLOWED_EXTENSIONS
from app import db
from app.auth.models import AuditLog

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_action(user_id, table_name, record_id, action, changes=None):
    log = AuditLog(
        performed_by=user_id,
        table_name=table_name,
        record_id=record_id,
        action=action,
        changes=changes
    )
    db.session.add(log)
    db.session.commit()

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, BooleanField, MultipleFileField, RadioField, SubmitField
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed
from app.constants import ITEM_STATUS, REPORT_TYPE

class ReportItemForm(FlaskForm):
    report_type = RadioField(
        'Report Type', 
        choices=[(report_type, report_type.capitalize()) for report_type in REPORT_TYPE], 
        validators=[DataRequired()]
    )
    name = StringField('Item Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    category = SelectField('Category', coerce=int, validators=[DataRequired()])
    location_reported = StringField('Location Reported', validators=[Optional()])
    event_datetime = DateTimeField(
        'Event DateTime', 
        format='%Y-%m-%dT%H:%M', 
        validators=[Optional()]
    )
    images = MultipleFileField(
        'Upload Images', 
        validators=[
            Optional(), 
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
        ]
    )

    # Report related fields
    is_anonymous = BooleanField('Anonymous Post?', default=False)
    additional_details = TextAreaField('Additional Details', validators=[Optional()])
    contact_info = StringField('Contact Information', validators=[Optional()])
    
    # Submit button
    submit = SubmitField('Submit')

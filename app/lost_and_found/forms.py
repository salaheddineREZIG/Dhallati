from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, DateTimeField, 
                    BooleanField, MultipleFileField, RadioField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, Regexp
from flask_wtf.file import FileAllowed
from app.constants import NAME_LIMIT, DESCRIPTION_LIMIT
from flask_wtf.csrf import CSRFProtect

class ReportItemForm(FlaskForm):
    # Step 1: Basics
    report_type = RadioField(
        'Report Type',
        choices=[('lost', 'I Lost an Item'), ('found', 'I Found an Item')],
        validators=[DataRequired(message='Please select report type')]
    )
    
    is_anonymous = BooleanField(
        'Post Anonymously?',
        default=False,
        description="Hide your name from other users"
    )
    
    category_id = SelectField(
        'Category',
        coerce=int,
        validators=[DataRequired(message='Please select a category')],
        description="What type of item is this?"
    )
    
    # Step 2: Description
    name = StringField(
        'Item Name',
        validators=[
            DataRequired(message='Item name is required'),
            Length(max=NAME_LIMIT, message=f'Item name must be less than {NAME_LIMIT} characters')
        ],
        description="e.g., Black Jansport Backpack, Silver MacBook Pro"
    )
    
    description = TextAreaField(
        'Description',
        validators=[
            Optional(),
            Length(max=DESCRIPTION_LIMIT, message=f'Description must be less than {DESCRIPTION_LIMIT} characters')
        ],
        description="Describe the item, including brand, color, size, unique features..."
    )
    
    images = MultipleFileField(
        'Upload Images',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only images are allowed (jpg, png, gif)')
        ],
        description="You can upload up to 5 images"
    )
    
    additional_details = TextAreaField(
        'Additional Details',
        validators=[
            Optional(),
            Length(max=DESCRIPTION_LIMIT, message=f'Additional details must be less than {DESCRIPTION_LIMIT} characters')
        ],
        description="Any other relevant information not covered above"
    )
    
    # Step 3: Location & Time
    location_id = SelectField(
        'Location',
        coerce=int,
        validators=[Optional()],
        description="Where did this happen?"
    )
    
    specific_spot = StringField(
        'Specific Spot',
        validators=[
            Optional(),
            Length(max=255, message='Specific spot must be less than 255 characters')
        ],
        description="e.g., 2nd floor study room, near vending machine"
    )
    
    event_datetime = DateTimeField(
        'When did this happen?',
        format='%Y-%m-%dT%H:%M',  # Fixed format to match HTML datetime-local
        validators=[Optional()],
        description="Leave empty for current date/time"
    )
    
    # Step 4: Contact & Verification
    contact_info = StringField(
        'Contact Phone Number',
        validators=[
            DataRequired(message='Contact number is required'),
            Length(min=10, max=10, message='Phone number must be exactly 10 digits'),
            Regexp(r'^[0-9]{10}$', message='Enter a valid 10-digit phone number')  # Fixed regex
        ],
        description="10-digit number (e.g., 0698166666)"
    )
    
    verification_question = TextAreaField(
        'Verification Question',
        validators=[Optional()],
        description="For Found items: Question to help verify the real owner"
    )
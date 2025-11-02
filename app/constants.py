import enum

class ReportType(enum.Enum):
    LOST = "LOST"
    FOUND = "FOUND"

ITEM_STATUS = ('lost', 'found', 'returned','pending')
NOTIFICATION_TYPE = ('match_found', 'status_update', 'new_item_reported')
NAME_AND_CONTACT_AND_LOCATION_CHARACTERS = 50
DESCRIPTION_AND_ADDITIONAL_CHARACTERS = 150
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



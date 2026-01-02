from app import create_app
import os

# Force production environment
os.environ['FLASK_ENV'] = 'production'
app = create_app()
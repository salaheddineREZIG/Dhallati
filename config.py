from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for Flask application")
    
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # Use environment variable for database, default to SQLite only in development
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("No DATABASE_URL set for Flask application")
    
    LAGH_UNI_DOMAIN = os.getenv('LAGH_UNI_DOMAIN')
    GOOGLE_TOKEN_INFO = os.getenv('GOOGLE_TOKEN_INFO')
    
    # Make upload folder path more robust
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static', 'images', 'uploads')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Never debug in production
    DEBUG = False
    
    # Additional production settings
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Limit upload size (10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow cookies in HTTP for development

class ProductionConfig(Config):
    pass
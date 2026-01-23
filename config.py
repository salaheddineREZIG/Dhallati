import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Secret key - will be validated later
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    # Other settings
    LAGH_UNI_DOMAIN = os.getenv('LAGH_UNI_DOMAIN')
    GOOGLE_TOKEN_INFO = os.getenv('GOOGLE_TOKEN_INFO')
    
    # Upload folder
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images', 'uploads')
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask settings
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # Security settings (only in production)
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload size limit
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    @classmethod
    def init_app(cls, app):
        """Initialize configuration with the app instance"""
        # Set defaults for development if not set
        if not app.config['SECRET_KEY']:
            if app.config['DEBUG']:
                # Use a default for development
                app.config['SECRET_KEY'] = 'dev-secret-key-for-development-only'
                app.logger.warning('Using default SECRET_KEY for development')
            else:
                raise ValueError('SECRET_KEY must be set in production')
        
        if not app.config['SQLALCHEMY_DATABASE_URI']:
            if app.config['DEBUG']:
                # Default SQLite for development
                app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
                app.logger.warning('Using SQLite database for development')
            else:
                raise ValueError('DATABASE_URL must be set in production')
        
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
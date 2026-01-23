from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
oauth = OAuth()

def create_app(config_class=None):
    """Application factory"""
    from config import Config
    
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = Config
    app.config.from_object(config_class)
    
    # Initialize app with config
    config_class.init_app(app)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    oauth.init_app(app)
    
    # Register OAuth
    if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            access_token_url='https://oauth2.googleapis.com/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            api_base_url='https://www.googleapis.com/oauth2/v2/',
            client_kwargs={'scope': 'openid email profile'}
        )
    
    # Register blueprints
    from app.main import main as main_blueprint
    from app.auth import auth as auth_blueprint
    from app.lost_and_found import lost_and_found as lost_and_found_blueprint
    
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(lost_and_found_blueprint)
    
    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if app.config.get('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    return app
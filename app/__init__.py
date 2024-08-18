from flask import Flask, request
from config import Config
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

# Load environment variables from .env file
load_dotenv()

# Initialize db globally
db = SQLAlchemy()

# Initialize migrate
migrate = Migrate()

oauth = OAuth()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize OAuth here
    oauth.init_app(app)

    # Initialize db here, now it's part of the app's context
    db.init_app(app)
    
    migrate.init_app(app, db)
    
    from app.auth.models import User, AuditLog
    from app.lost_and_found.models import Item, Report, Notification, Match, Location, ItemImage

    # Register OAuth clients
    oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    api_base_url='https://www.googleapis.com/oauth2/v2/',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

    
    from app.main import main as main_blueprint
    from app.auth import auth as auth_blueprint
    from app.lost_and_found import lost_and_found as lost_and_found_blueprint
    # Register blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(lost_and_found_blueprint)

    # Return the configured app
    return app

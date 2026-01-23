from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:13241324@localhost:5432/Dhallati')
    LAGH_UNI_DOMAIN = os.getenv('LAGH_UNI_DOMAIN')
    GOOGLE_TOKEN_INFO = os.getenv('GOOGLE_TOKEN_INFO')
    UPLOAD_FOLDER = os.path.join('app','static', 'images', 'uploads')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.getenv('DEBUG', True)
import os
from dotenv import load_dotenv

# Load env variables from a .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-12345!@#')
    
    # SQLAlchemy configuration
    # Fallback to SQLite database project.db in the root folder if DATABASE_URL is not set
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f'sqlite:///{os.path.join(BASE_DIR, "project.db")}'
    )
    # If the DATABASE_URL starts with postgres://, replace with postgresql:// for compatibility with newer SQLAlchemy versions
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Image upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'app', 'static', 'uploads', 'products'))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB Max Upload Size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY must be set in the environment.')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    
    # PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:@localhost:5432/ats'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login
    LOGIN_MESSAGE = 'Employee login required for dashboard.'


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

    # Email verification
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.office365.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes', 'on'}
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME
    EMAIL_VERIFICATION_REQUIRED = os.environ.get('EMAIL_VERIFICATION_REQUIRED', 'true').lower() in {'1', 'true', 'yes', 'on'}
    EMAIL_VERIFICATION_TOKEN_MAX_AGE = int(os.environ.get('EMAIL_VERIFICATION_TOKEN_MAX_AGE', '86400'))
    MFA_REQUIRED = os.environ.get('MFA_REQUIRED', 'true').lower() in {'1', 'true', 'yes', 'on'}
    MFA_TOKEN_MAX_AGE = int(os.environ.get('MFA_TOKEN_MAX_AGE', '600'))


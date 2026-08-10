import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ENV = os.environ.get('FLASK_ENV') or os.environ.get('APP_ENV') or 'development'
    IS_PRODUCTION = ENV.lower() in {'production', 'prod'}

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if IS_PRODUCTION:
            raise RuntimeError('SECRET_KEY must be set in the environment for production.')
        SECRET_KEY = 'dev-only-change-me'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    
    # Use local SQLite by default so a fresh clone can start without PostgreSQL.
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or 'sqlite:///ats.db'
    )
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

    # Restrict employee self-registration to a specific email domain (e.g. '@yourcompany.com').
    # Leave unset to allow any email domain -- each deployment/client sets its own via .env.
    ALLOWED_EMPLOYEE_EMAIL_DOMAIN = (os.environ.get('ALLOWED_EMPLOYEE_EMAIL_DOMAIN') or '').strip().lower() or None


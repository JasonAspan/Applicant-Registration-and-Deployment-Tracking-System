import smtplib
from email.message import EmailMessage

from flask import current_app, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


EMAIL_VERIFICATION_SALT = 'employee-email-verification'


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def generate_email_verification_token(employee):
    return _serializer().dumps(
        {'employee_id': employee.id, 'email': employee.email},
        salt=EMAIL_VERIFICATION_SALT,
    )


def verify_email_verification_token(token):
    max_age = current_app.config['EMAIL_VERIFICATION_TOKEN_MAX_AGE']
    return _serializer().loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=max_age)


def build_email_verification_url(employee):
    token = generate_email_verification_token(employee)
    return url_for('verify_email', token=token, _external=True)


def send_email_verification(employee):
    server = current_app.config.get('MAIL_SERVER')
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    if not all([server, username, password, sender]):
        raise RuntimeError('Email settings are incomplete. Check MAIL_USERNAME, MAIL_PASSWORD, and MAIL_DEFAULT_SENDER.')

    verification_url = build_email_verification_url(employee)
    subject = 'Verify your ARTS account'
    text_body = (
        f'Hello {employee.username},\n\n'
        'Please verify your ARTS account by opening this link:\n'
        f'{verification_url}\n\n'
        'This verification link expires in 24 hours.\n'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = employee.email
    message.set_content(text_body)

    with smtplib.SMTP(server, current_app.config['MAIL_PORT'], timeout=20) as smtp:
        if current_app.config.get('MAIL_USE_TLS'):
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def send_mfa_code(employee, code):
    server = current_app.config.get('MAIL_SERVER')
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    if not all([server, username, password, sender]):
        raise RuntimeError('Email settings are incomplete. Check MAIL_USERNAME, MAIL_PASSWORD, and MAIL_DEFAULT_SENDER.')

    message = EmailMessage()
    message['Subject'] = 'Your ARTS login verification code'
    message['From'] = sender
    message['To'] = employee.email
    message.set_content(
        f'Hello {employee.username},\n\n'
        f'Your ARTS login verification code is: {code}\n\n'
        'This code expires in 10 minutes. If you did not try to sign in, contact your administrator.\n'
    )

    with smtplib.SMTP(server, current_app.config['MAIL_PORT'], timeout=20) as smtp:
        if current_app.config.get('MAIL_USE_TLS'):
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)


def is_invalid_or_expired_token(error):
    return isinstance(error, (BadSignature, SignatureExpired))

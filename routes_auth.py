"""
Authentication routes for ATS including first-login password reset

Routes:
- First-login password reset
- Password change
- Login with enforcement
"""

import hashlib
import secrets
import time

from flask import (
    request, render_template, redirect, url_for, flash,
    jsonify, current_app, abort, session
)
from flask_login import login_user, logout_user, current_user, login_required
from models import db, Employee, Role
from email_verification import is_invalid_or_expired_token, send_mfa_code, verify_email_verification_token
from rbac_middleware import enforce_first_login_password_reset, log_permission_action
from time_utils import ph_now


def _mfa_code_hash(code):
    secret = current_app.config['SECRET_KEY']
    return hashlib.sha256(f'{code}:{secret}'.encode('utf-8')).hexdigest()


def _clear_pending_mfa():
    for key in ('pending_mfa_user_id', 'pending_mfa_code_hash', 'pending_mfa_expires_at', 'pending_mfa_remember'):
        session.pop(key, None)


def _begin_mfa_challenge(user, remember):
    code = f'{secrets.randbelow(1000000):06d}'
    session['pending_mfa_user_id'] = user.id
    session['pending_mfa_code_hash'] = _mfa_code_hash(code)
    session['pending_mfa_expires_at'] = int(time.time()) + current_app.config.get('MFA_TOKEN_MAX_AGE', 600)
    session['pending_mfa_remember'] = bool(remember)
    send_mfa_code(user, code)


def _complete_login(user, remember):
    now = ph_now()
    user.last_login = now
    user.session_started_at = now
    user.last_seen_at = now
    user.force_logout_at = None
    db.session.commit()

    login_user(user, remember=remember)

    log_permission_action(
        'user_login',
        user,
        reason=f'User logged in from {request.remote_addr}'
    )

    if user.force_password_reset:
        flash('You must reset your password on first login.', 'warning')
        return redirect(url_for('reset_password_first_login'))

    flash(f'Welcome back, {user.username}!', 'success')
    return redirect(url_for('dashboard'))


def _requires_mfa(user):
    if not current_app.config.get('MFA_REQUIRED', True):
        return False
    return not (user.role_obj and user.role_obj.name == 'SUPER_ADMIN')


def register_auth_routes(app):
    """Register authentication-related routes."""

    @app.route('/verify-email/<token>')
    def verify_email(token):
        try:
            payload = verify_email_verification_token(token)
        except Exception as e:
            if is_invalid_or_expired_token(e):
                flash('Verification link is invalid or expired.', 'error')
                return redirect(url_for('employee_login'))
            raise

        employee = Employee.query.filter_by(
            id=payload.get('employee_id'),
            email=payload.get('email'),
            is_deleted=False
        ).first()

        if not employee:
            flash('Verification link is invalid or expired.', 'error')
            return redirect(url_for('employee_login'))

        if not employee.email_verified:
            employee.email_verified = True
            employee.email_verified_at = ph_now()
            db.session.commit()

        flash('Email verified successfully. You may now log in.', 'success')
        return redirect(url_for('employee_login'))
    
    @app.route('/reset-password-first-login', methods=['GET', 'POST'])
    @login_required
    def reset_password_first_login():
        """
        First-login forced password reset page.
        
        This route is shown to users with force_password_reset=True
        They cannot access other pages until password is reset.
        """
        if not current_user.force_password_reset:
            return redirect(url_for('employee_home'))
        
        if request.method == 'POST':
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate passwords
            if not new_password or not confirm_password:
                flash('Both password fields are required.', 'error')
                return render_template('reset_password_first_login.html')
            
            if len(new_password) < 8:
                flash('Password must be at least 8 characters long.', 'error')
                return render_template('reset_password_first_login.html')
            
            if new_password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('reset_password_first_login.html')
            
            # Check if new password is same as old one
            if current_user.check_password(new_password):
                flash('New password cannot be the same as the old password.', 'error')
                return render_template('reset_password_first_login.html')
            
            try:
                current_user.set_password(new_password)
                current_user.force_password_reset = False
                current_user.last_login = ph_now()
                db.session.commit()
                
                log_permission_action(
                    'first_login_password_reset',
                    current_user,
                    reason='User reset password on first login'
                )
                
                flash('Password reset successfully! Welcome to the ATS.', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to reset password: {str(e)}', 'error')
                return render_template('reset_password_first_login.html')
        
        return render_template('reset_password_first_login.html')
    
    
    @app.route('/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        """
        Change password for logged-in user.
        Different from first-login reset - user provides old password.
        """
        if request.method == 'POST':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate inputs
            if not old_password or not new_password or not confirm_password:
                flash('All password fields are required.', 'error')
                return render_template('change_password.html')
            
            # Verify old password
            if not current_user.check_password(old_password):
                flash('Current password is incorrect.', 'error')
                return render_template('change_password.html')
            
            # Validate new password
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'error')
                return render_template('change_password.html')
            
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('change_password.html')
            
            if new_password == old_password:
                flash('New password must be different from current password.', 'error')
                return render_template('change_password.html')
            
            try:
                current_user.set_password(new_password)
                db.session.commit()
                
                log_permission_action(
                    'password_changed',
                    current_user,
                    reason='User changed password'
                )
                
                flash('Password changed successfully!', 'success')
                return redirect(url_for('profile'))
            except Exception as e:
                db.session.rollback()
                flash(f'Failed to change password: {str(e)}', 'error')
                return render_template('change_password.html')
        
        return render_template('change_password.html')
    
    
    @app.route('/employee-login.html', methods=['GET', 'POST'])
    def employee_login():
        """
        Enhanced login route with RBAC checks.
        
        After successful login:
        - If force_password_reset=True, redirect to password reset
        - Otherwise, redirect to dashboard
        """
        # Redirect if already logged in
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username and password are required.', 'error')
                return render_template('employee_login.html')
            
            # Find user
            user = Employee.query.filter_by(username=username, is_deleted=False).first()
            
            if not user:
                flash('Invalid username or password.', 'error')
                return render_template('employee_login.html')
            
            # Check if account is active
            if not user.is_active:
                flash('Your account is locked. Contact administrator.', 'error')
                return render_template('employee_login.html')
            
            # Check password
            if not user.check_password(password):
                flash('Invalid username or password.', 'error')
                return render_template('employee_login.html')

            if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True) and not user.email_verified:
                flash('Please verify your email before logging in.', 'error')
                return render_template('employee_login.html')
            
            # Check if user has a role
            if not user.role_id:
                flash('Your account is not assigned a role. Contact administrator.', 'error')
                return render_template('employee_login.html')

            if _requires_mfa(user):
                try:
                    _begin_mfa_challenge(user, request.form.get('remember_me'))
                except Exception:
                    current_app.logger.exception('Failed to send MFA email')
                    _clear_pending_mfa()
                    flash('Login verification email could not be sent. Please contact an administrator.', 'error')
                    return render_template('employee_login.html')

                flash('Enter the verification code sent to your email.', 'success')
                return redirect(url_for('employee_mfa'))
            
            try:
                return _complete_login(user, request.form.get('remember_me'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Login error: {str(e)}', 'error')
                return render_template('employee_login.html')
        
        return render_template('employee_login.html')

    @app.route('/employee-mfa.html', methods=['GET', 'POST'])
    def employee_mfa():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        pending_user_id = session.get('pending_mfa_user_id')
        expires_at = session.get('pending_mfa_expires_at')
        if not pending_user_id or not expires_at:
            flash('Please sign in again to request a verification code.', 'error')
            return redirect(url_for('employee_login'))

        user = Employee.query.filter_by(id=pending_user_id, is_deleted=False).first()
        if not user or not user.is_active:
            _clear_pending_mfa()
            flash('Please sign in again to request a verification code.', 'error')
            return redirect(url_for('employee_login'))

        if int(time.time()) > int(expires_at):
            _clear_pending_mfa()
            flash('Verification code expired. Please sign in again.', 'error')
            return redirect(url_for('employee_login'))

        if request.method == 'POST':
            code = ''.join(ch for ch in request.form.get('code', '') if ch.isdigit())
            expected_hash = session.get('pending_mfa_code_hash')
            if len(code) != 6 or not secrets.compare_digest(_mfa_code_hash(code), expected_hash or ''):
                flash('Invalid verification code.', 'error')
                return render_template('employee_mfa.html', email=user.email)

            remember = session.get('pending_mfa_remember', False)
            _clear_pending_mfa()
            try:
                return _complete_login(user, remember)
            except Exception as e:
                db.session.rollback()
                flash(f'Login error: {str(e)}', 'error')
                return redirect(url_for('employee_login'))

        return render_template('employee_mfa.html', email=user.email)
    
    
    @app.route('/employee-logout.html', methods=['GET', 'POST'])
    @app.route('/logout', methods=['GET', 'POST'])
    @login_required
    def logout():
        """
        Logout current user and clear session.
        """
        username = current_user.username
        current_user.session_started_at = None
        current_user.last_seen_at = None
        db.session.commit()
        logout_user()
        _clear_pending_mfa()
        flash(f'You have been logged out. Goodbye!', 'success')
        return redirect(url_for('employee_login'))

    @app.route('/api/auth/session-ping', methods=['GET'])
    @login_required
    def api_session_ping():
        return jsonify({'ok': True})
    
    
    @app.route('/api/auth/force-password-reset', methods=['GET'])
    @login_required
    def api_check_force_password_reset():
        """
        Check if current user needs to reset password.
        Used by frontend to redirect to password reset page.
        """
        return jsonify({
            'force_password_reset': current_user.force_password_reset,
            'username': current_user.username,
            'email': current_user.email
        })
    
    
    @app.route('/api/auth/reset-password', methods=['POST'])
    @login_required
    def api_reset_password_first_login():
        """
        API endpoint for first-login password reset.
        """
        if not current_user.force_password_reset:
            return jsonify({'error': 'Password reset not required'}), 400
        
        data = request.get_json() or {}
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        # Validate
        if not new_password or not confirm_password:
            return jsonify({'error': 'Both password fields required'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        if current_user.check_password(new_password):
            return jsonify({'error': 'New password cannot be same as old password'}), 400
        
        try:
            current_user.set_password(new_password)
            current_user.force_password_reset = False
            current_user.last_login = ph_now()
            db.session.commit()
            
            log_permission_action(
                'first_login_password_reset',
                current_user,
                reason='First login password reset via API'
            )
            
            return jsonify({'message': 'Password reset successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to reset password: {str(e)}'}), 500

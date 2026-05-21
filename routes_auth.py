"""
Authentication routes for ATS including first-login password reset

Routes:
- First-login password reset
- Password change
- Login with enforcement
"""

from flask import (
    request, render_template, redirect, url_for, flash, 
    jsonify, current_app, abort
)
from flask_login import login_user, logout_user, current_user, login_required
from models import db, Employee, Role
from rbac_middleware import enforce_first_login_password_reset, log_permission_action
from time_utils import ph_now


def register_auth_routes(app):
    """Register authentication-related routes."""
    
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
            
            # Check if user has a role
            if not user.role_id:
                flash('Your account is not assigned a role. Contact administrator.', 'error')
                return render_template('employee_login.html')
            
            try:
                # Update login/session timestamps
                now = ph_now()
                user.last_login = now
                user.session_started_at = now
                user.last_seen_at = now
                user.force_logout_at = None
                db.session.commit()
                
                # Log in user
                login_user(user, remember=request.form.get('remember_me'))
                
                log_permission_action(
                    'user_login',
                    user,
                    reason=f'User logged in from {request.remote_addr}'
                )
                
                # Check if password reset is required
                if user.force_password_reset:
                    flash('You must reset your password on first login.', 'warning')
                    return redirect(url_for('reset_password_first_login'))
                
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Login error: {str(e)}', 'error')
                return render_template('employee_login.html')
        
        return render_template('employee_login.html')
    
    
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

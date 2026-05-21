"""
RBAC middleware and guards for ATS

Provides:
- Permission checking middleware
- Before/after request hooks
- Protected route decorators
- Permission evaluation utilities
"""

from flask import request, jsonify, redirect, url_for, flash
from flask_login import current_user, logout_user
from functools import wraps
from models import db, Employee, Role, Permission
from auth_rbac import has_permission, get_user_permissions
from time_utils import ph_now


def init_rbac_middleware(app):
    """
    Initialize RBAC middleware for the Flask application.
    
    This function should be called during app creation to set up
    all the necessary hooks and middleware.
    """
    
    @app.before_request
    def before_request():
        """
        Before each request, check:
        1. User is authenticated (if route requires it)
        2. User is active
        3. User has a role assigned
        """
        if current_user.is_authenticated:
            now = ph_now()
            # Update last login
            if not current_user.last_login:
                current_user.last_login = now
                db.session.commit()
            
            # Verify user is still active
            if not current_user.is_active or current_user.is_deleted:
                current_user.session_started_at = None
                current_user.last_seen_at = None
                db.session.commit()
                logout_user()
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'User account is locked or deleted'}), 403
                flash('Your account is locked. Contact administrator.', 'error')
                return redirect(url_for('employee_login'))

            if (
                not current_user.session_started_at or
                (current_user.force_logout_at and current_user.session_started_at <= current_user.force_logout_at)
            ):
                current_user.session_started_at = None
                current_user.last_seen_at = None
                db.session.commit()
                logout_user()
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Session ended by administrator'}), 403
                flash('Your session was ended by administrator.', 'warning')
                return redirect(url_for('employee_login'))

            current_user.last_seen_at = now
            db.session.commit()
            
            # Verify user has a role
            if not current_user.role_id:
                flash('Your account is not assigned a role. Contact administrator.', 'error')
                return redirect(url_for('employee_logout'))
    
    @app.after_request
    def after_request(response):
        """Add security headers"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response


def require_permission_check(permission_key):
    """
    Decorator to check permission on a route.
    Can be used as an alternative to require_permission decorator.
    
    Usage:
        @app.route('/applicants')
        @login_required
        @require_permission_check('view_applicants')
        def view_applicants():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Unauthorized'}), 401
                flash('You must be logged in to access this page.', 'warning')
                return redirect(url_for('employee_login'))
            
            if not has_permission(current_user, permission_key):
                if request.is_json:
                    return jsonify({'error': f'Forbidden - missing permission: {permission_key}'}), 403
                flash(f'You do not have permission to perform this action.', 'danger')
                return redirect(url_for('employee_home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role_check(*role_names):
    """
    Decorator to check role on a route.
    Can be used for role-based access instead of permission-based.
    
    Usage:
        @app.route('/admin/panel')
        @login_required
        @require_role_check('SUPER_ADMIN')
        def admin_panel():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Unauthorized'}), 401
                flash('You must be logged in to access this page.', 'warning')
                return redirect(url_for('employee_login'))
            
            user_role = Role.query.get(current_user.role_id)
            if not user_role or user_role.name not in role_names:
                if request.is_json:
                    return jsonify({'error': f'Forbidden - insufficient role'}), 403
                flash(f'Your role does not have access to this resource.', 'danger')
                return redirect(url_for('employee_home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_first_login_password_reset():
    """
    Helper to check if user needs to reset password on first login.
    
    Should be called in a login route after successful authentication.
    Returns True if password reset is required.
    """
    if current_user.force_password_reset:
        return True
    return False


def enforce_first_login_password_reset():
    """
    Decorator to enforce first-login password reset.
    
    Usage:
        @app.route('/dashboard')
        @login_required
        @enforce_first_login_password_reset()
        def dashboard():
            ...
    
    If password reset is required, redirects to password reset page.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.is_authenticated and current_user.force_password_reset:
                flash('You must reset your password on first login.', 'warning')
                return redirect(url_for('reset_password_first_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_computed_permissions():
    """
    Get all computed permissions for the current user as a dictionary.
    Useful for frontend to show/hide elements based on permissions.
    
    Returns:
        dict: Maps permission keys to boolean values
    """
    if not current_user.is_authenticated:
        return {}
    
    user_perms = get_user_permissions(current_user)
    perm_dict = {}
    for perm_key in user_perms['permissions']:
        perm_dict[perm_key] = True
    
    return perm_dict


def can_edit_user(target_user):
    """
    Check if current user can edit another user.
    
    Rules:
    - SUPER_ADMIN can edit anyone
    - ADMIN can edit LEVEL_1 and LEVEL_2 users
    - Others cannot edit users
    - Users with 'manage_users' permission can edit
    """
    if not has_permission(current_user, 'manage_users'):
        return False
    
    # Cannot edit yourself (use a separate route for that)
    if current_user.id == target_user.id:
        return False
    
    current_role = Role.query.get(current_user.role_id)
    target_role = Role.query.get(target_user.role_id)
    
    if current_role.name == 'SUPER_ADMIN':
        return True
    
    if current_role.name == 'ADMIN':
        # ADMIN can only edit LEVEL_1 and LEVEL_2 users
        if target_role.name in ['LEVEL_1_USER', 'LEVEL_2_USER']:
            return True
    
    return False


def is_user_elevated():
    """
    Check if current user has elevated privileges.
    Returns True if user is SUPER_ADMIN or ADMIN.
    """
    if not current_user.is_authenticated or not current_user.role_id:
        return False
    
    role = Role.query.get(current_user.role_id)
    return role.name in ['SUPER_ADMIN', 'ADMIN']


def is_super_admin():
    """Check if current user is SUPER_ADMIN."""
    if not current_user.is_authenticated or not current_user.role_id:
        return False
    
    role = Role.query.get(current_user.role_id)
    return role.name == 'SUPER_ADMIN'


def log_permission_action(action_type, target_user, permission_key=None, reason=None):
    """
    Log permission-related actions for audit trail.
    
    Args:
        action_type: str, e.g., 'grant_permission', 'revoke_permission', 'user_created'
        target_user: Employee object
        permission_key: str, optional
        reason: str, optional
    """
    # TODO: Implement audit logging to a separate AuditLog table
    # For now, just print to logs
    print(f"[AUDIT] {action_type}: user_id={target_user.id}, permission={permission_key}, reason={reason}, admin_id={current_user.id}")

"""
Authentication and RBAC utilities for ATS

This module provides:
- Permission checking and enforcement
- RBAC decorators for route protection
- Role-based access control helpers
"""

from functools import wraps
from flask import abort, current_app, jsonify
from flask_login import current_user
from sqlalchemy import delete, text
from models import db, Employee, Role, Permission, UserPermission, role_permission

# Define default permission keys
PERMISSION_KEYS = {
    # Applicant management
    'view_applicants': 'View applicants',
    'create_applicant': 'Create applicants',
    'edit_applicant': 'Edit applicants',
    'delete_applicant': 'Delete applicants',
    'export_applicant_cv': 'Export applicant CV',
    'export_applicant_excel': 'Export applicant data to Excel',
    'forward_applicant': 'Forward/reassign applicants',
    
    # Position management
    'manage_positions': 'Manage job positions (create/update/delete)',
    'view_positions': 'View job positions',
    
    # User management
    'manage_users': 'Create, update, delete users',
    'manage_permissions': 'Assign/modify user permissions',
    'view_users': 'View all users',
    
    # Dashboard
    'view_dashboard': 'Access dashboard',
    'manage_dashboard': 'Manage dashboard content',
    
    # Administrative
    'manage_roles': 'Create/modify roles',
    'access_admin_panel': 'Access super admin panel',
}

# Role definitions with default permissions
ROLE_PERMISSIONS = {
    'SUPER_ADMIN': [
        'view_applicants', 'create_applicant', 'edit_applicant', 'delete_applicant',
        'export_applicant_cv', 'export_applicant_excel', 'forward_applicant',
        'manage_positions', 'view_positions',
        'manage_users', 'manage_permissions', 'view_users',
        'view_dashboard', 'manage_dashboard',
        'manage_roles', 'access_admin_panel'
    ],
    'ADMIN': [
        'view_applicants', 'edit_applicant', 'export_applicant_cv', 'export_applicant_excel',
        'forward_applicant', 'manage_positions', 'view_positions', 'view_users',
        'view_dashboard'
    ],
    'LEVEL_2_USER': [
        'view_applicants', 'export_applicant_cv', 'export_applicant_excel',
        'view_positions', 'view_dashboard'
    ],
    'LEVEL_1_USER': [
        'view_applicants', 'export_applicant_cv', 'export_applicant_excel',
        'view_positions', 'view_dashboard'
    ]
}


def has_permission(user, permission_key):
    """
    Check if user has a permission.
    
    Algorithm:
    1. Check user-specific permission overrides (deny takes precedence)
    2. Fall back to role-based permissions
    
    Args:
        user: Employee object
        permission_key: str, permission key to check
        
    Returns:
        bool: True if permission is granted, False otherwise
    """
    if not user or not user.is_active:
        return False
    
    if not user.role_id:
        return False

    role = Role.query.get(user.role_id)
    if not role:
        return False

    if role.name == 'SUPER_ADMIN':
        return True
    
    # Check user-specific permission override
    override = UserPermission.query.filter_by(
        user_id=user.id,
        permission_id=db.session.query(Permission.id).filter_by(key=permission_key).scalar()
    ).first()
    
    if override:
        return override.is_allowed
    
    # Fall back to role permissions
    permission = Permission.query.filter_by(key=permission_key).first()
    if not permission:
        return False
    
    return permission in role.permissions.all()


def require_permission(permission_key):
    """
    Decorator to enforce permission on a route.
    
    Usage:
        @app.route('/admin/users')
        @require_permission('manage_users')
        def manage_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Unauthorized'}), 401
            
            if not has_permission(current_user, permission_key):
                return jsonify({'error': 'Forbidden - insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(*role_names):
    """
    Decorator to enforce role on a route.
    
    Usage:
        @app.route('/admin/panel')
        @require_role('SUPER_ADMIN')
        def admin_panel():
            ...
            
        @app.route('/users')
        @require_role('SUPER_ADMIN', 'ADMIN')
        def user_management():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Unauthorized'}), 401
            
            user_role = Role.query.get(current_user.role_id)
            if not user_role or user_role.name not in role_names:
                return jsonify({'error': 'Forbidden - insufficient role'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions(user):
    """
    Get all permissions for a user (computed).
    
    Returns:
        dict: {
            'role': 'ROLE_NAME',
            'permissions': ['perm1', 'perm2', ...],
            'overrides': {
                'perm': {'is_allowed': True/False, 'reason': '...'}
            }
        }
    """
    if not user or not user.role_id:
        return {'role': None, 'permissions': [], 'overrides': {}}
    
    role = Role.query.get(user.role_id)
    if not role:
        return {'role': None, 'permissions': [], 'overrides': {}}

    if role.name == 'SUPER_ADMIN':
        all_permissions = {permission.key for permission in Permission.query.all()}
        all_permissions.update(PERMISSION_KEYS.keys())
        return {
            'role': role.name,
            'permissions': sorted(all_permissions),
            'overrides': {}
        }

    base_permissions = [p.key for p in role.permissions.all()]
    
    # Compute overrides
    overrides = {}
    user_overrides = UserPermission.query.filter_by(user_id=user.id).all()
    for override in user_overrides:
        overrides[override.permission.key] = {
            'is_allowed': override.is_allowed,
            'reason': override.reason
        }
    
    # Compute final permissions
    final_permissions = set(base_permissions)
    for perm_key, override_info in overrides.items():
        if override_info['is_allowed']:
            final_permissions.add(perm_key)
        else:
            final_permissions.discard(perm_key)
    
    return {
        'role': role.name,
        'permissions': sorted(list(final_permissions)),
        'overrides': overrides
    }


def seed_roles_and_permissions():
    """
    Seed default roles and permissions into database.
    Should be called during app initialization.
    """
    if db.engine.dialect.name == 'postgresql':
        db.session.execute(text("SELECT pg_advisory_xact_lock(2026052901)"))

    # Create or update permissions
    for perm_key, perm_desc in PERMISSION_KEYS.items():
        existing = Permission.query.filter_by(key=perm_key).first()
        if not existing:
            perm = Permission(key=perm_key, description=perm_desc)
            db.session.add(perm)
    
    db.session.flush()
    permissions_by_key = {
        permission.key: permission
        for permission in Permission.query.filter(Permission.key.in_(PERMISSION_KEYS.keys())).all()
    }
    
    # Create or update roles
    for role_name, perm_keys in ROLE_PERMISSIONS.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f'{role_name} role')
            db.session.add(role)
            db.session.flush()
        
        # Clear and re-add permissions
        # Delete all existing role_permission entries for this role
        db.session.execute(delete(role_permission).where(role_permission.c.role_id == role.id))
        db.session.flush()
        
        # Add new permissions
        for perm_key in perm_keys:
            perm = permissions_by_key.get(perm_key)
            if perm:
                db.session.execute(
                    role_permission.insert().values(
                        role_id=role.id,
                        permission_id=perm.id,
                    )
                )
    
    db.session.commit()


def can_manage_user(admin_user, target_user):
    """
    Check if admin_user can manage target_user.
    
    Rules:
    - SUPER_ADMIN can manage anyone
    - ADMIN cannot manage other ADMINs or SUPER_ADMINs
    - Cannot self-manage permissions
    """
    if not has_permission(admin_user, 'manage_users'):
        return False
    
    admin_role = Role.query.get(admin_user.role_id)
    target_role = Role.query.get(target_user.role_id)
    
    if admin_role.name == 'SUPER_ADMIN':
        return True
    
    if admin_role.name == 'ADMIN':
        # ADMIN cannot manage SUPER_ADMIN or other ADMINs
        if target_role.name in ['SUPER_ADMIN', 'ADMIN']:
            return False
        return True
    
    return False

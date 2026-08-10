"""
RBAC and Permission Management API routes

Endpoints:
- User management (create, update, delete, list)
- Permission assignment/revocation
- Role management
- Permission queries for frontend
- First-login password reset
"""

from io import BytesIO

from flask import request, jsonify, render_template, redirect, url_for, flash, abort, send_file
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from functools import wraps

from models import (
    db, Employee, Role, Permission, UserPermission, Applicant,
    ApplicantDashboardDeletion, ApplicantForward, Position, position_assignment,
    Announcement, AnnouncementRead
)
from auth_rbac import (
    has_permission, get_user_permissions, can_manage_user, 
    require_permission, require_role, ROLE_PERMISSIONS, PERMISSION_KEYS
)
from rbac_middleware import (
    require_permission_check, require_role_check, is_super_admin,
    can_edit_user, enforce_first_login_password_reset, log_permission_action
)
from time_utils import ph_iso, ph_now


def _admin_user_profile_payload(user):
    """Build read-only user profile data for SUPER_ADMIN views and APIs."""
    assigned_positions = sorted(
        {position.title for position in list(user.assigned_positions) + list(user.primary_assigned_positions)}
    )

    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role_obj.name if user.role_obj else None,
        'is_active': user.is_active,
        'force_password_reset': user.force_password_reset,
        'created_at': ph_iso(user.created_at),
        'last_login': ph_iso(user.last_login),
        'session_started_at': ph_iso(user.session_started_at),
        'last_seen_at': ph_iso(user.last_seen_at),
        'created_by': user.created_by.username if user.created_by else None,
        'assigned_positions': assigned_positions,
        'applicants_count': user.applicants.count(),
        'remarks_count': len(user.remarked_applicants),
        'has_profile_picture': bool(user.profile_data),
        'profile_picture_url': (
            url_for('api_get_user_profile_picture', user_id=user.id)
            if user.profile_data else None
        ),
    }


def register_rbac_routes(app):
    """Register all RBAC-related routes."""

    def serialize_announcement(announcement, read_ids=None):
        read_ids = read_ids or set()
        return {
            'id': announcement.id,
            'title': announcement.title,
            'message': announcement.message,
            'created_at': ph_iso(announcement.created_at),
            'created_by': announcement.created_by.username if announcement.created_by else 'System',
            'recipient_id': announcement.recipient_employee_id,
            'is_read': announcement.id in read_ids,
        }

    def prune_old_announcements(limit=5):
        global_announcements = Announcement.query.filter(
            Announcement.recipient_employee_id.is_(None)
        ).order_by(
            Announcement.created_at.desc(),
            Announcement.id.desc()
        ).all()
        old_announcements = global_announcements[limit:]
        if not old_announcements:
            return
        old_ids = [announcement.id for announcement in old_announcements]
        AnnouncementRead.query.filter(AnnouncementRead.announcement_id.in_(old_ids)).delete(synchronize_session=False)
        for announcement in old_announcements:
            db.session.delete(announcement)
    
    # ==================== User Management Routes ====================
    
    @app.route('/api/users', methods=['GET'])
    @login_required
    @require_permission_check('view_users')
    def api_get_users():
        """Get list of all users (paginated)."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        include_deleted = request.args.get('include_deleted') == '1' and is_super_admin()
        query = Employee.query
        if not include_deleted:
            query = query.filter(Employee.is_deleted == False)
        query = query.order_by(Employee.created_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        users = []
        for emp in paginated.items:
            users.append({
                'id': emp.id,
                'username': emp.username,
                'email': emp.email,
                'role': emp.role_obj.name if emp.role_obj else None,
                'is_active': emp.is_active,
                'email_verified': emp.email_verified,
                'is_deleted': emp.is_deleted,
                'force_password_reset': emp.force_password_reset,
                'created_at': ph_iso(emp.created_at),
                'last_login': ph_iso(emp.last_login),
            })
        
        return jsonify({
            'users': users,
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page
        })


    @app.route('/api/active-sessions', methods=['GET'])
    @login_required
    @require_permission_check('view_users')
    def api_active_sessions():
        """Get active user sessions for admin monitoring."""
        employees = Employee.query.filter(
            Employee.is_active == True,
            Employee.is_deleted == False,
            Employee.session_started_at.isnot(None)
        ).order_by(Employee.session_started_at.desc()).all()

        return jsonify({
            'sessions': [{
                'user_id': emp.id,
                'username': emp.username,
                'role': emp.role_obj.name if emp.role_obj else None,
                'session_started_at': ph_iso(emp.session_started_at),
                'last_seen_at': ph_iso(emp.last_seen_at),
                'is_current_user': emp.id == current_user.id,
            } for emp in employees]
        })
    
    
    @app.route('/api/users', methods=['POST'])
    @login_required
    @require_permission_check('manage_users')
    def api_create_user():
        """Create a new user (SUPER_ADMIN and ADMIN only)."""
        data = request.get_json() or {}
        
        # Validate required fields
        if not data.get('username') or not data.get('password') or not data.get('role'):
            return jsonify({'error': 'Missing required fields: username, password, role'}), 400
        
        # Check if role exists
        role = Role.query.filter_by(name=data.get('role')).first()
        if not role:
            return jsonify({'error': f'Role not found: {data.get("role")}'}), 404
        
        # Check if admin can manage this role
        admin_role = Role.query.get(current_user.role_id)
        target_role = role
        
        # ADMIN cannot create SUPER_ADMIN or other ADMIN accounts
        if admin_role.name == 'ADMIN' and target_role.name in ['SUPER_ADMIN', 'ADMIN']:
            return jsonify({'error': 'Insufficient privileges to create this role'}), 403
        
        # Check if username already exists
        if Employee.query.filter_by(username=data.get('username'), is_deleted=False).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create new user
        email = data.get('email') or f"{data.get('username')}@company.com"
        
        if Employee.query.filter_by(email=email, is_deleted=False).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        try:
            user = Employee(
                username=data.get('username'),
                email=email,
                role_id=role.id,
                force_password_reset=True,
                is_active=True,
                email_verified=True,
                email_verified_at=ph_now(),
                created_by_id=current_user.id
            )
            user.set_password(data.get('password'))
            
            db.session.add(user)
            db.session.commit()
            
            log_permission_action('user_created', user, reason=f"Created by {current_user.username}")
            
            return jsonify({
                'message': 'User created successfully',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role_obj.name,
                    'force_password_reset': user.force_password_reset
                }
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to create user: {str(e)}'}), 500
    
    
    @app.route('/api/users/<int:user_id>', methods=['GET'])
    @login_required
    @require_permission_check('view_users')
    def api_get_user(user_id):
        """Get user details including permissions."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        
        user_perms = get_user_permissions(user)
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role_obj.name if user.role_obj else None,
            'is_active': user.is_active,
            'force_password_reset': user.force_password_reset,
            'created_at': ph_iso(user.created_at),
            'last_login': ph_iso(user.last_login),
            'permissions': user_perms['permissions'],
            'overrides': user_perms['overrides']
        })


    @app.route('/api/users/<int:user_id>/profile', methods=['GET'])
    @login_required
    @require_permission_check('view_users')
    def api_get_user_profile(user_id):
        """Get read-only user profile details for the admin panel."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        return jsonify(_admin_user_profile_payload(user))


    @app.route('/admin/users/<int:user_id>/profile', methods=['GET'])
    @login_required
    @require_role_check('SUPER_ADMIN')
    def admin_user_profile(user_id):
        """Dedicated SUPER_ADMIN page for viewing a user's profile."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        return render_template(
            'admin_user_profile.html',
            profile=_admin_user_profile_payload(user),
        )


    @app.route('/api/users/<int:user_id>/profile-picture', methods=['GET'])
    @login_required
    @require_permission_check('view_users')
    def api_get_user_profile_picture(user_id):
        """Serve a user's profile picture to admins with user view permission."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        if not user.profile_data:
            abort(404)

        return send_file(
            BytesIO(user.profile_data),
            mimetype=user.profile_content_type or 'application/octet-stream',
            as_attachment=False,
            download_name=user.profile_filename or 'profile',
        )
    
    
    @app.route('/api/users/<int:user_id>', methods=['PATCH'])
    @login_required
    @require_permission_check('manage_users')
    def api_update_user(user_id):
        """Update user (email, active status, etc.)."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        
        # Check if current user can manage this user
        if not can_edit_user(user):
            return jsonify({'error': 'You cannot manage this user'}), 403
        
        data = request.get_json() or {}
        
        # Update username
        if 'username' in data:
            username = (data.get('username') or '').strip()
            if not username:
                return jsonify({'error': 'Username is required'}), 400
            if username != user.username and Employee.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already in use'}), 409
            user.username = username

        # Update email
        if 'email' in data and data['email'] != user.email:
            email = (data.get('email') or '').strip()
            if not email:
                return jsonify({'error': 'Email is required'}), 400
            if Employee.query.filter_by(email=email).first():
                return jsonify({'error': 'Email already in use'}), 409
            user.email = email
        
        # Update active status (SUPER_ADMIN only for certain roles)
        if 'is_active' in data:
            target_role = Role.query.get(user.role_id)
            admin_role = Role.query.get(current_user.role_id)
            
            if admin_role.name == 'SUPER_ADMIN' or target_role.name in ['LEVEL_1_USER', 'LEVEL_2_USER', 'LEVEL_3_USER']:
                user.is_active = data['is_active']
        
        # Update role (SUPER_ADMIN only)
        if 'role' in data and current_user.role_id == Role.query.filter_by(name='SUPER_ADMIN').first().id:
            role = Role.query.filter_by(name=data['role']).first()
            if not role:
                return jsonify({'error': f'Role not found: {data["role"]}'}), 404
            user.role_id = role.id
        
        try:
            db.session.commit()
            log_permission_action('user_updated', user, reason=f"Updated by {current_user.username}")
            
            return jsonify({'message': 'User updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to update user: {str(e)}'}), 500
    
    
    @app.route('/api/users/<int:user_id>/password', methods=['PATCH'])
    @login_required
    def api_change_password(user_id):
        """
        Change password for a user.
        - Users can change their own password
        - SUPER_ADMIN can reset any user's password
        """
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        data = request.get_json() or {}
        
        # Can only change own password unless SUPER_ADMIN
        if current_user.id != user_id:
            if not is_super_admin():
                return jsonify({'error': 'Cannot change another user\'s password'}), 403
        
        if current_user.id == user_id:
            # User changing own password - must provide current password
            if not data.get('current_password'):
                return jsonify({'error': 'Current password required'}), 400
            
            if not current_user.check_password(data.get('current_password')):
                return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Validate new password
        new_password = data.get('new_password')
        if not new_password or len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        force_reset = False
        if current_user.id != user_id and is_super_admin():
            force_reset = bool(data.get('force_password_reset', False))

        try:
            user.set_password(new_password)
            user.force_password_reset = force_reset
            db.session.commit()
            
            log_permission_action('password_changed', user, reason=f"Changed by {current_user.username}")
            
            return jsonify({'message': 'Password changed successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to change password: {str(e)}'}), 500
    
    
    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @login_required
    @require_permission_check('manage_users')
    def api_delete_user(user_id):
        """Lock a user account (sets inactive, does not delete the record)."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        
        # Cannot delete self
        if current_user.id == user_id:
            return jsonify({'error': 'Cannot lock your own account'}), 400
        
        # Check if current user can manage this user
        if not can_edit_user(user):
            return jsonify({'error': 'You cannot lock this user'}), 403
        
        try:
            user.is_active = False
            db.session.commit()
            
            log_permission_action('user_locked', user, reason=f"Locked by {current_user.username}")
            
            return jsonify({'message': 'User locked successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to lock user: {str(e)}'}), 500


    @app.route('/api/users/<int:user_id>/permanent', methods=['DELETE'])
    @login_required
    @require_permission_check('manage_users')
    def api_permanently_delete_user(user_id):
        """Forget a user account identity while preserving internal audit links."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()

        if current_user.id == user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400

        if not can_edit_user(user):
            return jsonify({'error': 'You cannot delete this user'}), 403

        try:
            username = user.username
            deleted_at = ph_now()
            user.is_active = False
            user.is_deleted = True
            user.username = f'deleted_user_{user.id}_{int(deleted_at.timestamp())}'
            user.email = f'deleted_user_{user.id}_{int(deleted_at.timestamp())}@deleted.local'
            user.email_verified = False
            user.email_verified_at = None
            user.email_verification_sent_at = None
            user.deleted_at = deleted_at
            user.deleted_by_id = current_user.id
            user.session_started_at = None
            user.last_seen_at = None
            user.force_logout_at = deleted_at
            db.session.commit()

            log_permission_action('user_deleted', current_user, reason=f"Deleted and forgot user {username}")
            return jsonify({'message': 'User deleted and forgotten successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500


    @app.route('/api/users/<int:user_id>/restore', methods=['POST'])
    @login_required
    @require_permission_check('manage_users')
    def api_restore_user(user_id):
        """Deleted users are forgotten and must register again."""
        return jsonify({'error': 'Deleted users cannot be restored. The user must register again.'}), 410


    @app.route('/api/users/<int:user_id>/remote-logout', methods=['POST'])
    @login_required
    @require_permission_check('manage_users')
    def api_remote_logout_user(user_id):
        """End an active user session."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()

        if current_user.id == user_id:
            return jsonify({'error': 'Cannot remotely log out your own account'}), 400

        if not can_edit_user(user):
            return jsonify({'error': 'You cannot remotely log out this user'}), 403

        try:
            user.force_logout_at = ph_now()
            user.session_started_at = None
            user.last_seen_at = None
            db.session.commit()
            log_permission_action('user_remote_logout', user, reason=f"Remote logout by {current_user.username}")
            return jsonify({'message': 'User logged out successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to log out user: {str(e)}'}), 500
    
    
    # ==================== Permission Management Routes ====================
    
    @app.route('/api/permissions', methods=['GET'])
    @login_required
    def api_get_permissions():
        """Get list of all available permissions."""
        permissions = Permission.query.order_by(Permission.category, Permission.key).all()
        
        result = {}
        for perm in permissions:
            category = perm.category or 'other'
            if category not in result:
                result[category] = []
            
            result[category].append({
                'id': perm.id,
                'key': perm.key,
                'description': perm.description
            })
        
        return jsonify(result)
    
    
    @app.route('/api/users/<int:user_id>/permissions', methods=['GET'])
    @login_required
    @require_permission_check('manage_permissions')
    def api_get_user_permissions(user_id):
        """Get user's computed permissions."""
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        user_perms = get_user_permissions(user)
        
        return jsonify(user_perms)
    
    
    @app.route('/api/users/<int:user_id>/permissions', methods=['POST'])
    @login_required
    @require_permission_check('manage_permissions')
    def api_assign_permission(user_id):
        """
        Assign or override a permission for a user.
        SUPER_ADMIN only.
        """
        if not is_super_admin():
            return jsonify({'error': 'Only SUPER_ADMIN can manage permissions'}), 403
        
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        data = request.get_json() or {}
        
        perm_key = data.get('permission_key')
        is_allowed = data.get('is_allowed', True)
        reason = data.get('reason')
        
        if not perm_key:
            return jsonify({'error': 'permission_key is required'}), 400
        
        permission = Permission.query.filter_by(key=perm_key).first()
        if not permission:
            return jsonify({'error': f'Permission not found: {perm_key}'}), 404
        
        try:
            # Check if override already exists
            override = UserPermission.query.filter_by(
                user_id=user_id,
                permission_id=permission.id
            ).first()
            
            if override:
                override.is_allowed = is_allowed
                override.reason = reason
                override.created_by_id = current_user.id
            else:
                override = UserPermission(
                    user_id=user_id,
                    permission_id=permission.id,
                    is_allowed=is_allowed,
                    reason=reason,
                    created_by_id=current_user.id
                )
                db.session.add(override)
            
            db.session.commit()
            
            action = 'grant_permission' if is_allowed else 'revoke_permission'
            log_permission_action(action, user, permission_key=perm_key, reason=reason)
            
            return jsonify({
                'message': 'Permission updated successfully',
                'override': {
                    'permission_key': perm_key,
                    'is_allowed': is_allowed,
                    'reason': reason
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to update permission: {str(e)}'}), 500
    
    
    @app.route('/api/users/<int:user_id>/permissions/<perm_key>', methods=['DELETE'])
    @login_required
    @require_permission_check('manage_permissions')
    def api_remove_permission_override(user_id, perm_key):
        """
        Remove a permission override for a user (revert to role default).
        SUPER_ADMIN only.
        """
        if not is_super_admin():
            return jsonify({'error': 'Only SUPER_ADMIN can manage permissions'}), 403
        
        user = Employee.query.filter_by(id=user_id, is_deleted=False).first_or_404()
        permission = Permission.query.filter_by(key=perm_key).first()
        
        if not permission:
            return jsonify({'error': f'Permission not found: {perm_key}'}), 404
        
        try:
            override = UserPermission.query.filter_by(
                user_id=user_id,
                permission_id=permission.id
            ).first()
            
            if override:
                db.session.delete(override)
                db.session.commit()
                log_permission_action('permission_override_removed', user, permission_key=perm_key)
            
            return jsonify({'message': 'Permission override removed'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to remove permission: {str(e)}'}), 500
    
    
    # ==================== Role Management Routes ====================
    
    @app.route('/api/roles', methods=['GET'])
    @login_required
    def api_get_roles():
        """Get list of all roles with their permissions."""
        roles = Role.query.all()
        
        result = []
        for role in roles:
            perms = [p.key for p in role.permissions.all()]
            result.append({
                'id': role.id,
                'name': role.name,
                'description': role.description,
                'permissions': perms
            })
        
        return jsonify({'roles': result})
    
    
    # ==================== Permission Checking Routes ====================
    
    @app.route('/api/check-permission', methods=['POST'])
    @login_required
    def api_check_permission():
        """
        Check if current user has a specific permission.
        Used by frontend to show/hide UI elements.
        """
        data = request.get_json() or {}
        perm_key = data.get('permission_key')
        
        if not perm_key:
            return jsonify({'error': 'permission_key is required'}), 400
        
        has_perm = has_permission(current_user, perm_key)
        
        return jsonify({'permission_key': perm_key, 'has_permission': has_perm})
    
    
    @app.route('/api/my-permissions', methods=['GET'])
    @login_required
    def api_get_my_permissions():
        """Get all computed permissions for current user."""
        user_perms = get_user_permissions(current_user)
        
        return jsonify(user_perms)


    # ==================== Announcement Routes ====================

    @app.route('/api/announcements', methods=['GET'])
    @login_required
    def api_get_announcements():
        """Get the latest global announcements and current user's private notifications."""
        if request.args.get('scope') == 'global' and is_super_admin():
            query = Announcement.query.filter(Announcement.recipient_employee_id.is_(None))
        else:
            query = Announcement.query.filter(
                or_(
                    Announcement.recipient_employee_id.is_(None),
                    Announcement.recipient_employee_id == current_user.id,
                )
            )

        announcements = query.order_by(
            Announcement.created_at.desc(),
            Announcement.id.desc()
        ).limit(5).all()
        announcement_ids = [announcement.id for announcement in announcements]
        read_ids = set()
        if announcement_ids:
            read_ids = {
                row[0] for row in db.session.query(AnnouncementRead.announcement_id)
                .filter(
                    AnnouncementRead.employee_id == current_user.id,
                    AnnouncementRead.announcement_id.in_(announcement_ids),
                )
                .all()
            }

        return jsonify({
            'announcements': [serialize_announcement(announcement, read_ids) for announcement in announcements],
            'unread_count': sum(1 for announcement in announcements if announcement.id not in read_ids),
        })


    @app.route('/api/announcements', methods=['POST'])
    @login_required
    def api_create_announcement():
        """Create an announcement. The system keeps only the newest five."""
        if not is_super_admin():
            return jsonify({'error': 'Only SUPER_ADMIN can compose announcements'}), 403

        data = request.get_json() or {}
        title = (data.get('title') or '').strip()
        message = (data.get('message') or '').strip()

        if not title:
            return jsonify({'error': 'Announcement title is required'}), 400
        if not message:
            return jsonify({'error': 'Announcement message is required'}), 400
        if len(title) > 120:
            return jsonify({'error': 'Announcement title must be 120 characters or fewer'}), 400
        if len(message) > 2000:
            return jsonify({'error': 'Announcement message must be 2000 characters or fewer'}), 400

        try:
            announcement = Announcement(
                title=title,
                message=message,
                created_by_id=current_user.id,
                recipient_employee_id=None,
            )
            db.session.add(announcement)
            db.session.flush()
            prune_old_announcements(limit=5)
            db.session.commit()
            log_permission_action('announcement_created', current_user, reason=f'Created announcement {announcement.id}')
            return jsonify({
                'message': 'Announcement published',
                'announcement': serialize_announcement(announcement, set()),
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to create announcement: {str(e)}'}), 500


    @app.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
    @login_required
    def api_delete_announcement(announcement_id):
        """Delete an announcement from the current list."""
        if not is_super_admin():
            return jsonify({'error': 'Only SUPER_ADMIN can delete announcements'}), 403

        announcement = Announcement.query.get_or_404(announcement_id)
        if announcement.recipient_employee_id is not None:
            return jsonify({'error': 'Private notifications cannot be deleted here'}), 403
        try:
            AnnouncementRead.query.filter_by(announcement_id=announcement.id).delete(synchronize_session=False)
            db.session.delete(announcement)
            db.session.commit()
            log_permission_action('announcement_deleted', current_user, reason=f'Deleted announcement {announcement_id}')
            return jsonify({'message': 'Announcement deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Failed to delete announcement: {str(e)}'}), 500


    @app.route('/api/announcements/<int:announcement_id>/read', methods=['POST'])
    @login_required
    def api_mark_announcement_read(announcement_id):
        """Mark one announcement as read for the current user."""
        Announcement.query.get_or_404(announcement_id)
        existing = AnnouncementRead.query.filter_by(
            announcement_id=announcement_id,
            employee_id=current_user.id,
        ).first()
        if not existing:
            db.session.add(AnnouncementRead(
                announcement_id=announcement_id,
                employee_id=current_user.id,
            ))
            db.session.commit()
        return jsonify({'message': 'Announcement marked as read'})

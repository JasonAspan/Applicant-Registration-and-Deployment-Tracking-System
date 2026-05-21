"""
RBAC Usage Examples for ATS Routes

This file shows concrete examples of how to use RBAC decorators and utilities
in your existing routes (routes_employee.py, routes_applicant.py, etc.)
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

# Import RBAC utilities
from rbac_middleware import (
    require_permission_check,
    require_role_check,
    enforce_first_login_password_reset,
    has_permission,
    is_super_admin,
    can_edit_user,
    get_user_permissions
)
from models import db, Applicant, Employee


# ============================================================================
# EXAMPLE 1: Dashboard with Permission Check
# ============================================================================

@app.route('/dashboard')
@login_required
@enforce_first_login_password_reset()  # Force password reset on first login
@require_permission_check('view_dashboard')  # Check permission
def dashboard():
    """
    Dashboard page accessible to all authorized users.
    
    - First-login password reset is enforced
    - Only users with 'view_dashboard' permission can access
    - 403 Forbidden returned if user lacks permission
    """
    try:
        # Get applicants for this user
        if is_super_admin():
            # SUPER_ADMIN sees all applicants
            applicants = Applicant.query.all()
        else:
            # Others see only their assigned applicants
            applicants = current_user.applicants
        
        # Get user's computed permissions for frontend
        user_perms = get_user_permissions(current_user)
        
        return render_template(
            'dashboard.html',
            applicants=applicants,
            user_permissions=user_perms['permissions']
        )
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('employee_home'))


# ============================================================================
# EXAMPLE 2: Manage Positions (Role-Based)
# ============================================================================

@app.route('/positions', methods=['GET', 'POST'])
@login_required
@enforce_first_login_password_reset()
@require_role_check('SUPER_ADMIN', 'ADMIN')  # Only SUPER_ADMIN and ADMIN
def manage_positions():
    """
    Manage job positions.
    
    - Only SUPER_ADMIN and ADMIN roles can access
    - Others get 403 Forbidden
    - Can be further restricted via permission override
    """
    if request.method == 'POST':
        # Additional permission check for creation
        if not has_permission(current_user, 'manage_positions'):
            return jsonify({'error': 'Permission denied'}), 403
        
        # Process position creation
        pass
    
    # GET - list positions
    return render_template('positions.html')


# ============================================================================
# EXAMPLE 3: Forward Applicant (Permission-Based)
# ============================================================================

@app.route('/applicants/<int:applicant_id>/forward', methods=['POST'])
@login_required
@enforce_first_login_password_reset()
@require_permission_check('forward_applicant')  # Explicit permission check
def forward_applicant(applicant_id):
    """
    Forward an applicant to another recruiter.
    
    - Requires 'forward_applicant' permission
    - Normally only ADMIN has this
    - SUPER_ADMIN can grant this to others via permission override
    - 403 Forbidden if user lacks permission
    """
    applicant = Applicant.query.get_or_404(applicant_id)
    
    # Get the target employee
    target_employee_id = request.form.get('target_employee_id')
    target = Employee.query.get_or_404(target_employee_id)
    
    # Update assignment
    applicant.employee_id = target.id
    db.session.commit()
    
    flash(f'Applicant forwarded to {target.username}', 'success')
    return redirect(url_for('view_applicant', applicant_id=applicant_id))


# ============================================================================
# EXAMPLE 4: Export Applicant Data (Permission-Based)
# ============================================================================

@app.route('/applicants/<int:applicant_id>/cv/download')
@login_required
@enforce_first_login_password_reset()
@require_permission_check('export_applicant_cv')  # Check permission
def download_cv(applicant_id):
    """
    Download applicant CV.
    
    - Requires 'export_applicant_cv' permission
    - Available to: ADMIN, LEVEL_2_USER, LEVEL_1_USER
    - Can be extended to other roles via override
    """
    applicant = Applicant.query.get_or_404(applicant_id)
    
    if not applicant.cv_data:
        flash('CV not available', 'error')
        return redirect(url_for('view_applicant', applicant_id=applicant_id))
    
    from io import BytesIO
    return send_file(
        BytesIO(applicant.cv_data),
        mimetype=applicant.cv_content_type,
        as_attachment=True,
        download_name=applicant.cv_filename
    )


# ============================================================================
# EXAMPLE 5: User Management (Admin Only)
# ============================================================================

@app.route('/users')
@login_required
@enforce_first_login_password_reset()
@require_permission_check('view_users')  # Check permission
def list_users():
    """
    List all users.
    
    - Requires 'view_users' permission
    - Only SUPER_ADMIN and ADMIN have this
    """
    users = Employee.query.all()
    
    # Filter users based on what current user can manage
    manageable_users = []
    for user in users:
        if can_edit_user(user):
            manageable_users.append(user)
    
    return render_template('users.html', users=manageable_users)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@enforce_first_login_password_reset()
@require_permission_check('manage_users')  # Check permission
def edit_user(user_id):
    """
    Edit user details.
    
    - Requires 'manage_users' permission
    - Uses can_edit_user() to verify current user can manage target user
    - ADMIN cannot manage other ADMINs or SUPER_ADMINs
    """
    user = Employee.query.get_or_404(user_id)
    
    # Check if current user can manage this user
    if not can_edit_user(user):
        flash('You cannot manage this user', 'error')
        return redirect(url_for('list_users'))
    
    if request.method == 'POST':
        # Update user
        user.email = request.form.get('email', user.email)
        user.is_active = request.form.get('is_active') == 'on'
        
        db.session.commit()
        flash('User updated', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('edit_user.html', user=user)


# ============================================================================
# EXAMPLE 6: Create User (SUPER_ADMIN only)
# ============================================================================

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
@enforce_first_login_password_reset()
@require_role_check('SUPER_ADMIN')  # Restrict to SUPER_ADMIN only
def create_user():
    """
    Create a new user.
    
    - Only SUPER_ADMIN can access this route
    - ADMIN cannot access (gets 403 Forbidden)
    - Note: In practice, use the /api/users endpoint instead
    """
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        
        # Create user...
        pass
    
    return render_template('create_user.html')


# ============================================================================
# EXAMPLE 7: Manual Permission Check in Route Handler
# ============================================================================

@app.route('/applicants/<int:applicant_id>/delete', methods=['POST'])
@login_required
@enforce_first_login_password_reset()
def delete_applicant(applicant_id):
    """
    Delete an applicant.
    
    - Instead of decorator, we manually check permission
    - Useful for conditional logic or partial permissions
    - Returns 403 with JSON for API endpoints
    """
    applicant = Applicant.query.get_or_404(applicant_id)
    
    # Manual permission check
    if not has_permission(current_user, 'delete_applicant'):
        if request.is_json:
            return jsonify({'error': 'Permission denied'}), 403
        else:
            flash('You do not have permission to delete applicants', 'error')
            return redirect(url_for('view_applicant', applicant_id=applicant_id))
    
    # Permission granted, proceed with deletion
    applicant.is_deleted = True  # or hard delete: db.session.delete(applicant)
    db.session.commit()
    
    flash('Applicant deleted', 'success')
    return redirect(url_for('list_applicants'))


# ============================================================================
# EXAMPLE 8: Dynamic UI Rendering Based on Permissions
# ============================================================================

@app.route('/applicants/<int:applicant_id>')
@login_required
@enforce_first_login_password_reset()
@require_permission_check('view_applicants')
def view_applicant(applicant_id):
    """
    View applicant details with dynamic UI based on permissions.
    
    - Show/hide buttons based on user permissions
    - Pass computed permissions to template
    """
    applicant = Applicant.query.get_or_404(applicant_id)
    
    # Get user's permissions
    user_perms = get_user_permissions(current_user)
    
    # Create permission lookup for template
    has_perm = {perm: True for perm in user_perms['permissions']}
    
    return render_template(
        'view_applicant.html',
        applicant=applicant,
        permissions=has_perm
    )


# In the template (view_applicant.html):
"""
<div class="applicant-details">
    <h2>{{ applicant.full_name }}</h2>
    <p>Email: {{ applicant.email }}</p>
    
    <!-- Only show edit button if user has permission -->
    {% if permissions.get('edit_applicant') %}
        <a href="{{ url_for('edit_applicant', applicant_id=applicant.id) }}" 
           class="btn btn-primary">Edit</a>
    {% endif %}
    
    <!-- Only show delete button if user has permission -->
    {% if permissions.get('delete_applicant') %}
        <form method="POST" action="{{ url_for('delete_applicant', applicant_id=applicant.id) }}"
              style="display: inline;">
            <button type="submit" class="btn btn-danger" 
                    onclick="return confirm('Delete this applicant?')">Delete</button>
        </form>
    {% endif %}
    
    <!-- Only show forward button if user has permission -->
    {% if permissions.get('forward_applicant') %}
        <button class="btn btn-info" data-toggle="modal" data-target="#forwardModal">
            Forward to Recruiter
        </button>
    {% endif %}
    
    <!-- Only show export buttons if user has permission -->
    {% if permissions.get('export_applicant_cv') %}
        <a href="{{ url_for('download_cv', applicant_id=applicant.id) }}" 
           class="btn btn-secondary">Download CV</a>
    {% endif %}
    
    {% if permissions.get('export_applicant_excel') %}
        <button class="btn btn-secondary" onclick="exportToExcel()">Export Excel</button>
    {% endif %}
</div>
"""


# ============================================================================
# EXAMPLE 9: Permission Override Scenario
# ============================================================================

"""
Scenario: Promote LEVEL_2_USER to temporary project lead

1. Current situation:
   User: john (LEVEL_2_USER)
   - Can view and export
   - Cannot forward or edit applicants

2. Grant permission override:
   POST /api/users/5/permissions
   {
       "permission_key": "forward_applicant",
       "is_allowed": true,
       "reason": "Promoted to temporary project lead for Q2 2026"
   }

3. Result:
   - john now has forward_applicant permission
   - Override stored in UserPermission table
   - When john logs in, has_permission('forward_applicant') returns True
   - UI buttons appear for forwarding
   - API endpoint allows forwarding

4. Remove override when done:
   DELETE /api/users/5/permissions/forward_applicant
   - Override removed
   - Reverts to LEVEL_2_USER defaults
"""


# ============================================================================
# EXAMPLE 10: Admin Check Helper Functions
# ============================================================================

@app.route('/applicants/bulk-action', methods=['POST'])
@login_required
@enforce_first_login_password_reset()
def bulk_applicant_action():
    """
    Example of using helper functions in route handlers.
    """
    action = request.form.get('action')
    applicant_ids = request.form.getlist('applicant_ids')
    
    # Check permission based on action
    permission_map = {
        'forward': 'forward_applicant',
        'delete': 'delete_applicant',
        'export': 'export_applicant_excel'
    }
    
    required_perm = permission_map.get(action)
    
    if required_perm and not has_permission(current_user, required_perm):
        flash(f'You do not have permission to {action} applicants', 'error')
        return redirect(url_for('list_applicants'))
    
    # Perform action for each applicant
    for app_id in applicant_ids:
        applicant = Applicant.query.get(app_id)
        if applicant:
            if action == 'forward':
                applicant.employee_id = request.form.get('target_employee_id')
            elif action == 'delete':
                applicant.is_deleted = True
    
    db.session.commit()
    flash(f'{action.capitalize()} completed for {len(applicant_ids)} applicant(s)', 'success')
    return redirect(url_for('list_applicants'))


# ============================================================================
# SUMMARY OF DECORATORS AND UTILITIES
# ============================================================================

"""
DECORATORS:

@require_permission_check('permission_key')
    - Check if user has specific permission
    - Returns 403 if not
    - Use when endpoint requires specific permission

@require_role_check('ROLE1', 'ROLE2', ...)
    - Check if user has one of specified roles
    - Returns 403 if not
    - Use for role-based access (rare)

@enforce_first_login_password_reset()
    - Force user to reset password on first login
    - Redirects to password reset page
    - Apply to all protected routes


UTILITY FUNCTIONS:

has_permission(user, permission_key) -> bool
    - Check if user has permission (role + overrides)
    - Returns True/False
    - Use for conditional logic in routes

get_user_permissions(user) -> dict
    - Get all computed permissions for user
    - Returns {'role': 'NAME', 'permissions': [...], 'overrides': {...}}
    - Use to pass to templates

is_super_admin() -> bool
    - Check if current user is SUPER_ADMIN
    - Returns True/False

can_edit_user(target_user) -> bool
    - Check if current user can manage target user
    - Respects role hierarchy
    - Returns True/False

get_computed_permissions() -> dict
    - Get computed permissions for current user as dict
    - Returns {'permission_key': True, ...}
    - Use in templates for quick lookups
"""

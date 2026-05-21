+"""
RBAC Integration Guide for ATS

This document explains how to integrate the RBAC system into the existing ATS application.
"""

# ============================================================================
# 1. UPDATE ats_app.py
# ============================================================================

"""
In ats_app.py, you need to:
1. Import the RBAC modules
2. Call seed_roles_and_permissions() during app creation
3. Initialize RBAC middleware
4. Register RBAC routes

Replace the create_app function with the following:
"""

# --- START: Update ats_app.py ---

from flask import Flask, redirect, url_for
from flask_login import LoginManager
from sqlalchemy import inspect, text

from config import Config
from models import db, Employee, Role
from auth_rbac import seed_roles_and_permissions
from rbac_middleware import init_rbac_middleware


login_manager = LoginManager()
login_manager.login_view = 'employee_login'
login_manager.login_message = 'Employee login required for dashboard.'


@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))


def ensure_db_schema():
    """... existing code ..."""
    pass


def create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home'):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    
    with app.app_context():
        ensure_db_schema()
        
        # RBAC: Initialize database schema and seed roles/permissions
        db.create_all()
        seed_roles_and_permissions()
        
        # RBAC: Initialize RBAC middleware
        init_rbac_middleware(app)
    
    if enable_applicant:
        from routes_applicant import register_applicant_routes
        register_applicant_routes(app)
    
    if enable_employee:
        from routes_employee import register_employee_routes
        register_employee_routes(app)
        
        # RBAC: Register auth routes (password reset, change password)
        from routes_auth import register_auth_routes
        register_auth_routes(app)
        
        # RBAC: Register RBAC management routes
        from routes_rbac import register_rbac_routes
        register_rbac_routes(app)
    
    @app.route('/')
    def root():
        if root_redirect == 'applicant_home':
            return redirect(url_for('applicant_home'))
        elif root_redirect == 'employee_home':
            return redirect(url_for('employee_home'))
        elif root_redirect == 'dashboard':
            return redirect(url_for('dashboard'))
        return redirect(url_for('applicant_home'))
    
    return app


# --- END: Update ats_app.py ---


# ============================================================================
# 2. UPDATE routes_employee.py
# ============================================================================

"""
In routes_employee.py, add the following to the register_employee_routes function:

1. Update the employee_login route to handle first-login password reset
2. Add route protection with @enforce_first_login_password_reset()
3. Update dashboard route to check permissions

These changes are already handled in routes_auth.py, but you need to:
- Import the necessary decorators from rbac_middleware
- Add permission checks to protected routes
"""

# Example route updates for routes_employee.py:

"""
@app.route('/dashboard')
@login_required
@enforce_first_login_password_reset()
@require_permission_check('view_dashboard')
def dashboard():
    # Dashboard logic
    pass

@app.route('/positions')
@login_required
@enforce_first_login_password_reset()
@require_permission_check('manage_positions')
def manage_positions():
    # Position management logic
    pass
"""


# ============================================================================
# 3. INITIALIZATION & SETUP
# ============================================================================

"""
To set up the RBAC system:

STEP 1: Update requirements.txt (already done)
    - Run: pip install -r requirements.txt

STEP 2: Seed the database
    - Run: python seed_rbac.py
    - This creates:
        * All roles (SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER)
        * All permissions
        * Default users:
            - Username: SUPERADMIN, Password: <set SUPERADMIN_INITIAL_PASSWORD>
            - Username: ADMIN, Password: <set ADMIN_INITIAL_PASSWORD>

STEP 3: Start the application
    - Run: python app.py
    - Navigate to http://localhost:5000/employee-login.html
    - Log in with SUPERADMIN credentials
    - You will be forced to reset your password

STEP 4: Access Admin Panel
    - After password reset, you can access the admin panel
    - Route: /admin/panel (to be added)
    - Or use the API endpoints directly
"""


# ============================================================================
# 4. ADD ADMIN PANEL ROUTE
# ============================================================================

"""
Add this route to routes_rbac.py or create a new routes_admin.py:
"""

@app.route('/admin/panel')
@login_required
@require_role_check('SUPER_ADMIN')
def admin_panel():
    \"\"\"SUPER_ADMIN only: User and permission management panel\"\"\"
    return render_template('admin_panel.html')


# ============================================================================
# 5. PERMISSION DECORATOR USAGE EXAMPLES
# ============================================================================

"""
Example 1: Require specific permission
    @app.route('/applicants/forward', methods=['POST'])
    @login_required
    @require_permission('forward_applicant')
    def forward_applicant():
        # Only users with 'forward_applicant' permission can access
        pass

Example 2: Require specific role
    @app.route('/admin/users', methods=['GET'])
    @login_required
    @require_role('SUPER_ADMIN', 'ADMIN')
    def manage_users():
        # Only SUPER_ADMIN or ADMIN can access
        pass

Example 3: Check permission in middleware
    @app.route('/dashboard')
    @login_required
    @enforce_first_login_password_reset()
    @require_permission_check('view_dashboard')
    def dashboard():
        pass

Example 4: Manual permission check
    from rbac_middleware import has_permission
    
    @app.route('/applicants')
    @login_required
    def view_applicants():
        if not has_permission(current_user, 'view_applicants'):
            abort(403)
        # Process applicants
        pass
"""


# ============================================================================
# 6. FRONTEND: PERMISSION-BASED UI RENDERING
# ============================================================================

"""
In your templates, check permissions before showing UI elements:

Example 1: Check permission using template variable
    {% if current_user.has_permission('manage_users') %}
        <a href="/admin/panel">Admin Panel</a>
    {% endif %}

Example 2: Use API to check permissions
    fetch('/api/check-permission', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({permission_key: 'manage_users'})
    })
    .then(r => r.json())
    .then(data => {
        if (data.has_permission) {
            // Show admin button
        }
    });

Example 3: Get all user permissions
    fetch('/api/my-permissions')
        .then(r => r.json())
        .then(data => {
            console.log(data.permissions); // Array of permission keys
        });
"""


# ============================================================================
# 7. API ENDPOINTS REFERENCE
# ============================================================================

"""
USER MANAGEMENT:
    GET  /api/users                          - List all users
    POST /api/users                          - Create new user
    GET  /api/users/<id>                     - Get user details
    PATCH /api/users/<id>                    - Update user
    DELETE /api/users/<id>                   - Deactivate user
    PATCH /api/users/<id>/password           - Change password

PERMISSION MANAGEMENT:
    GET  /api/permissions                    - List all permissions
    GET  /api/users/<id>/permissions         - Get user's permissions
    POST /api/users/<id>/permissions         - Assign permission
    DELETE /api/users/<id>/permissions/<key> - Remove permission override

ROLE MANAGEMENT:
    GET  /api/roles                          - List all roles

PERMISSION CHECKING:
    POST /api/check-permission               - Check single permission
    GET  /api/my-permissions                 - Get current user's permissions

AUTHENTICATION:
    GET  /api/auth/force-password-reset      - Check if reset needed
    POST /api/auth/reset-password            - API-based password reset
"""


# ============================================================================
# 8. SECURITY CONSIDERATIONS
# ============================================================================

"""
✓ Passwords are hashed using werkzeug.security (bcrypt-compatible)
✓ First-login password reset enforced on all initial accounts
✓ Permission checks at middleware level (before route handler)
✓ Role-based and permission-based access control combined
✓ User-specific permission overrides evaluated with precedence
✓ SUPER_ADMIN cannot be removed or disabled by ADMIN
✓ Server-side permission validation on all API endpoints
✓ Audit logging for permission and user changes

TODO for Production:
    [ ] Enable HTTPS enforcement
    [ ] Implement rate limiting on login attempts
    [ ] Add comprehensive audit logging to database
    [ ] Implement session timeout
    [ ] Add two-factor authentication
    [ ] Encrypt sensitive data fields
    [ ] Implement API key authentication for service-to-service
    [ ] Add CSRF protection verification
    [ ] Implement account lockout after failed attempts
    [ ] Add IP-based access restrictions
"""


# ============================================================================
# 9. TESTING THE RBAC SYSTEM
# ============================================================================

"""
Test Script Scenarios:

1. Seed Database:
   python seed_rbac.py

2. Test SUPER_ADMIN Login:
   - Username: SUPERADMIN
   - Password: <set SUPERADMIN_INITIAL_PASSWORD>
   - Should be forced to reset password
   - After reset, should have full access

3. Test ADMIN Login:
   - Create via admin panel
   - Should be able to manage LEVEL_1 and LEVEL_2 users
   - Should NOT be able to manage SUPER_ADMIN

4. Test Permission Overrides:
   - Grant LEVEL_2_USER the 'forward_applicant' permission
   - User should now be able to forward applicants
   - Remove the override
   - User should no longer have permission

5. Test Password Reset:
   - Create a user via admin panel
   - User logs in, forced to reset password
   - Cannot access other pages until password is reset
   - After reset, full access

6. Test Permission Denials:
   - Manually test 403 responses
   - Verify user gets error messages
   - Check that UI elements are hidden for unauthorized users
"""


# ============================================================================
# 10. TROUBLESHOOTING
# ============================================================================

"""
Issue: "User account is not assigned a role"
Fix: Run seed_rbac.py to create roles, then assign role to user

Issue: "403 Forbidden - insufficient permissions"
Fix: Check user's role and permission overrides in admin panel

Issue: "Force password reset not clearing"
Fix: Ensure force_password_reset is set to False after reset
    UPDATE employee SET force_password_reset = FALSE WHERE id = <user_id>;

Issue: Permission changes not taking effect
Fix: Clear browser cache and logout/login
    Or check if permission override exists with db.session.query(UserPermission)

Issue: Admin cannot create users
Fix: Verify admin has role_id set and 'manage_users' permission
    Check Role table: ADMIN role should have manage_users permission
"""


# ============================================================================
# 11. MIGRATION FROM EXISTING SYSTEM
# ============================================================================

"""
If you have existing users:

1. Backup your database
2. Run: python seed_rbac.py
3. Run this migration script:

    from models import db, Employee, Role
    
    # Get the LEVEL_1_USER role (least privileged for existing users)
    role = Role.query.filter_by(name='LEVEL_1_USER').first()
    
    # Assign role to existing employees
    for emp in Employee.query.filter(Employee.role_id == None).all():
        emp.role_id = role.id
    
    db.session.commit()

4. Test thoroughly before going to production
"""


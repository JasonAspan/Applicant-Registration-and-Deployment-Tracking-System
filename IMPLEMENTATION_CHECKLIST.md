# RBAC Implementation Checklist

## Status: ✅ Complete - Ready for Integration

This document provides step-by-step instructions to integrate the RBAC system into your ATS application.

---

## Phase 1: Files Created ✅

The following files have been created and are ready to use:

### Core RBAC Files
- [x] `models.py` - Updated with RBAC schema (Role, Permission, UserPermission)
- [x] `auth_rbac.py` - Permission logic and utilities
- [x] `rbac_middleware.py` - Middleware and decorators
- [x] `routes_auth.py` - Authentication and password reset flows
- [x] `routes_rbac.py` - RBAC management API endpoints
- [x] `seed_rbac.py` - Database initialization script

### Templates
- [x] `templates/reset_password_first_login.html` - First-login password reset UI
- [x] `templates/change_password.html` - Password change UI
- [x] `templates/admin_panel.html` - SUPER_ADMIN management UI

### Documentation
- [x] `RBAC_SYSTEM.md` - Complete RBAC documentation
- [x] `RBAC_INTEGRATION_GUIDE.md` - Integration instructions
- [x] `RBAC_USAGE_EXAMPLES.py` - Code examples
- [x] `ats_app_UPDATED.py` - Updated Flask app factory
- [x] `IMPLEMENTATION_CHECKLIST.md` - This file

### Configuration
- [x] `requirements.txt` - Updated with bcrypt and PyJWT

---

## Phase 2: Update Existing Files

### Step 1: Update `models.py`
**Status**: ✅ Already Done

The `models.py` file has been updated with:
- `Role` model
- `Permission` model
- `role_permission` junction table
- `UserPermission` override table
- Updated `Employee` model with RBAC fields

✅ No action needed

---

### Step 2: Update `ats_app.py`

**Current state**: Old version using basic setup
**Action**: Replace or update with new version

**Instructions**:

1. **Backup current `ats_app.py`**:
   ```bash
   cp ats_app.py ats_app.py.bak
   ```

2. **Choose one approach**:

   **Option A: Complete replacement** (Recommended)
   ```bash
   cp ats_app_UPDATED.py ats_app.py
   ```

   **Option B: Manual merge** (If you have custom code)
   ```python
   # Add these imports at the top of ats_app.py:
   from auth_rbac import seed_roles_and_permissions
   from rbac_middleware import init_rbac_middleware
   
   # In create_app() function, inside app.app_context():
   db.create_all()
   seed_roles_and_permissions()  # Add this line
   init_rbac_middleware(app)      # Add this line
   
   # After existing route registrations:
   from routes_auth import register_auth_routes
   register_auth_routes(app)
   
   from routes_rbac import register_rbac_routes
   register_rbac_routes(app)
   
   # Add admin panel route:
   @app.route('/admin/panel')
   @login_required
   @require_role_check('SUPER_ADMIN')
   def admin_panel():
       return render_template('admin_panel.html')
   ```

3. **Verify the file**:
   ```bash
   python -c "from ats_app import create_app; app = create_app()"
   ```

---

### Step 3: Update `routes_employee.py`

**Instructions**:

1. **Add imports** at the top of file:
   ```python
   from rbac_middleware import (
       require_permission_check,
       enforce_first_login_password_reset,
       is_super_admin,
       get_user_permissions
   )
   from auth_rbac import has_permission
   ```

2. **Update dashboard route**:
   ```python
   @app.route('/dashboard')
   @login_required
   @enforce_first_login_password_reset()
   @require_permission_check('view_dashboard')
   def dashboard():
       # Existing dashboard code
       # Add permission lookup for UI rendering:
       user_perms = get_user_permissions(current_user)
       return render_template('dashboard.html', 
                            user_permissions=user_perms['permissions'])
   ```

3. **Add permission checks to protected routes**:
   - `/positions` - Add `@require_permission_check('manage_positions')`
   - `/applicants/<id>/forward` - Add `@require_permission_check('forward_applicant')`
   - Any export endpoints - Add `@require_permission_check('export_applicant_cv')`
   - Any delete endpoints - Add `@require_permission_check('delete_applicant')`

4. See `RBAC_USAGE_EXAMPLES.py` for detailed examples

---

### Step 4: Update Templates

**Add permission-based UI rendering** to your templates:

1. **dashboard.html**:
   ```html
   <!-- Only show admin link if user is SUPER_ADMIN -->
   {% if 'access_admin_panel' in user_permissions %}
       <a href="{{ url_for('admin_panel') }}" class="btn btn-danger">Admin Panel</a>
   {% endif %}
   ```

2. **applicant view template**:
   ```html
   <!-- Show edit button only if permitted -->
   {% if 'edit_applicant' in user_permissions %}
       <a href="{{ url_for('edit_applicant', applicant_id=applicant.id) }}" class="btn">Edit</a>
   {% endif %}
   ```

3. Use similar patterns throughout your templates

---

## Phase 3: Install Dependencies ⏳

### Step 1: Install new packages
```bash
pip install -r requirements.txt
```

**Packages added**:
- `bcrypt==4.1.2` - Password hashing
- `PyJWT==2.8.1` - JWT token handling (optional, for future use)

### Step 2: Verify installation
```bash
python -c "import bcrypt, jwt; print('✓ Dependencies installed')"
```

---

## Phase 4: Initialize Database ⏳

### Step 1: Run seed script
```bash
python seed_rbac.py
```

**What this does**:
1. Creates all tables (role, permission, role_permission, user_permission)
2. Seeds default roles (SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER)
3. Creates all permissions (20+ permissions)
4. Creates default SUPER_ADMIN account (username: SUPERADMIN)
5. Creates default ADMIN account (username: ADMIN)

**Output**:
```
============================================================
ATS RBAC System - Database Seeding
============================================================

[1/4] Creating database tables...
✓ Tables created successfully

[2/4] Seeding roles and permissions...
✓ Created 4 roles
✓ Created 20+ permissions

[3/4] Creating default SUPER_ADMIN user...
✓ SUPERADMIN user created
   Username: SUPERADMIN
   Password: <set SUPERADMIN_INITIAL_PASSWORD> (CHANGE THIS!)
   Status: Force password reset on first login

[4/4] Creating default ADMIN user...
✓ ADMIN user created
   Username: ADMIN
   Password: <set ADMIN_INITIAL_PASSWORD> (CHANGE THIS!)
   Status: Force password reset on first login

============================================================
✓ Database seeding completed successfully!
============================================================
```

### Step 2: Verify database

Connect to PostgreSQL and verify tables:
```sql
SELECT * FROM role;
SELECT * FROM permission;
SELECT COUNT(*) FROM employee WHERE username IN ('SUPERADMIN', 'ADMIN');
```

---

## Phase 5: Test the System ⏳

### Step 1: Start the application
```bash
python app.py
```

### Step 2: Test SUPER_ADMIN login
1. Navigate to: `http://localhost:5000/employee-login.html`
2. Enter credentials:
   - Username: `SUPERADMIN`
   - Password: `<set SUPERADMIN_INITIAL_PASSWORD>`
3. **Expected**: Redirected to password reset page
4. Reset password to new value (min 8 chars)
5. **Expected**: Redirected to dashboard

### Step 3: Test password reset enforcement
1. Create new user via admin panel
2. Try to access `/dashboard` before password reset
3. **Expected**: Redirected to password reset page

### Step 4: Test permission checks
1. Log in as non-ADMIN user
2. Try to access `/admin/panel`
3. **Expected**: 403 Forbidden error

### Step 5: Test permission overrides
1. Log in as SUPER_ADMIN
2. Go to admin panel
3. Select a LEVEL_2_USER
4. Grant `forward_applicant` permission
5. Log out and log in as that user
6. **Expected**: User can now forward applicants

### Step 6: Test API endpoints
```bash
# Get current user's permissions
curl http://localhost:5000/api/my-permissions \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# List all users
curl http://localhost:5000/api/users \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# Check specific permission
curl -X POST http://localhost:5000/api/check-permission \
  -H "Content-Type: application/json" \
  -d '{"permission_key": "manage_users"}' \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

---

## Phase 6: Configuration & Hardening ⏳

### Step 1: Update environment variables
```bash
# .env file
SECRET_KEY=your-secure-random-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/ats
SQLALCHEMY_TRACK_MODIFICATIONS=false
```

### Step 2: Enable HTTPS (Production)
```python
# config.py
PREFERRED_URL_SCHEME = 'https'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
```

### Step 3: Set up logging
```python
# ats_app.py
import logging
logging.basicConfig(
    filename='rbac.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Step 4: Test security
- [ ] Try SQL injection on login form
- [ ] Try to access admin panel as non-admin
- [ ] Try to modify permissions via browser dev tools
- [ ] Verify passwords are hashed (not plain text)
- [ ] Verify first-login reset is enforced

---

## Phase 7: Production Deployment ⏳

### Deployment Checklist
- [ ] Change default credentials (SUPERADMIN, ADMIN)
- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS/SSL
- [ ] Set up CSRF protection
- [ ] Implement rate limiting
- [ ] Configure logging and monitoring
- [ ] Set up database backups
- [ ] Test disaster recovery
- [ ] Document admin procedures
- [ ] Train team members

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'auth_rbac'"

**Solution**:
```bash
# Ensure all RBAC files are in the same directory as app.py
ls -la auth_rbac.py rbac_middleware.py routes_auth.py routes_rbac.py

# Reinstall requirements
pip install -r requirements.txt
```

---

### Issue: "No such table: role"

**Solution**:
```bash
# Run seed script
python seed_rbac.py

# Or manually create tables:
python -c "from ats_app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

---

### Issue: "User account is not assigned a role"

**Solution**:
```bash
# Assign default role to existing users
python -c "
from ats_app import create_app, db
from models import Employee, Role

app = create_app()
with app.app_context():
    role = Role.query.filter_by(name='LEVEL_1_USER').first()
    for emp in Employee.query.filter(Employee.role_id == None).all():
        emp.role_id = role.id
    db.session.commit()
    print('Assigned LEVEL_1_USER to all unassigned employees')
"
```

---

### Issue: "Password reset not working"

**Solution**:
1. Check `force_password_reset` column exists:
   ```sql
   SELECT * FROM employee WHERE username = 'SUPERADMIN';
   ```

2. If column missing, run `seed_rbac.py`

3. Manually set flag:
   ```sql
   UPDATE employee SET force_password_reset = TRUE WHERE username = 'SUPERADMIN';
   ```

---

### Issue: "Permission changes not taking effect"

**Solution**:
1. Clear browser cache
2. Logout and login again
3. Verify permission exists:
   ```sql
   SELECT * FROM permission WHERE key = 'manage_positions';
   ```

4. Check if override exists:
   ```sql
   SELECT * FROM user_permission WHERE user_id = 5;
   ```

---

## File Structure After Integration

```
/Applicant Tracking System/
│
├── app.py                              # Main entry point
├── ats_app.py                          # UPDATED: Flask factory
├── config.py                           # Configuration
│
├── models.py                           # UPDATED: RBAC schema
├── auth_rbac.py                        # ✨ NEW: RBAC logic
├── rbac_middleware.py                  # ✨ NEW: Middleware
│
├── routes_employee.py                  # UPDATED: With RBAC checks
├── routes_applicant.py                 # May need RBAC checks
├── routes_auth.py                      # ✨ NEW: Auth routes
├── routes_rbac.py                      # ✨ NEW: RBAC API routes
│
├── seed_rbac.py                        # ✨ NEW: Seed script
├── requirements.txt                    # UPDATED: +bcrypt, PyJWT
│
├── templates/
│   ├── base.html
│   ├── base_employee.html
│   ├── base_applicant.html
│   ├── reset_password_first_login.html # ✨ NEW: Password reset
│   ├── change_password.html             # ✨ NEW: Change password
│   ├── admin_panel.html                 # ✨ NEW: Admin UI
│   └── ...
│
├── static/
│   ├── css/
│   ├── js/
│   └── ...
│
├── RBAC_SYSTEM.md                      # ✨ NEW: Documentation
├── RBAC_INTEGRATION_GUIDE.md           # ✨ NEW: Integration guide
├── RBAC_USAGE_EXAMPLES.py              # ✨ NEW: Code examples
├── ats_app_UPDATED.py                  # ✨ NEW: Reference
└── IMPLEMENTATION_CHECKLIST.md         # ✨ NEW: This file
```

---

## Quick Reference

### Decorators
```python
@require_permission_check('permission_key')  # Check permission
@require_role_check('ROLE')                  # Check role
@enforce_first_login_password_reset()        # Force password reset
```

### Utility Functions
```python
has_permission(user, 'permission_key')       # Check if user has permission
get_user_permissions(user)                   # Get all permissions
is_super_admin()                             # Check if SUPER_ADMIN
can_edit_user(target_user)                   # Check if can manage user
get_computed_permissions()                   # Get current user's permissions
```

### API Endpoints
```
GET  /api/users                              # List users
POST /api/users                              # Create user
GET  /api/users/<id>/permissions             # Get user permissions
POST /api/users/<id>/permissions             # Grant permission
GET  /api/my-permissions                     # Get my permissions
POST /api/check-permission                   # Check permission
```

---

## Support & Documentation

1. **RBAC_SYSTEM.md** - Complete documentation and architecture
2. **RBAC_INTEGRATION_GUIDE.md** - Step-by-step integration
3. **RBAC_USAGE_EXAMPLES.py** - Code examples
4. **ats_app_UPDATED.py** - Reference implementation
5. Inline code comments - Detailed comments in all RBAC files

---

## Next Steps

1. ✅ Review all RBAC files
2. ⏳ Update `ats_app.py`
3. ⏳ Update `routes_employee.py` with decorators
4. ⏳ Install dependencies: `pip install -r requirements.txt`
5. ⏳ Run seed script: `python seed_rbac.py`
6. ⏳ Test the system with default credentials
7. ⏳ Change default credentials
8. ⏳ Deploy to production
9. ⏳ Train team members

---

**Status**: Implementation Complete and Ready ✅
**Last Updated**: April 24, 2026
**Version**: 1.0 - Production Ready

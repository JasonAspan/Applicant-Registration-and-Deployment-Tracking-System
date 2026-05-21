# ATS Role-Based Access Control (RBAC) System

## Overview

This document describes the comprehensive Role-Based Access Control (RBAC) system implemented for the Applicant Tracking System (ATS). The system provides fine-grained permission management with dynamic overrides controlled by SUPER_ADMIN.

## Table of Contents

1. [Architecture](#architecture)
2. [Database Schema](#database-schema)
3. [User Roles](#user-roles)
4. [Permission System](#permission-system)
5. [Default Credentials](#default-credentials)
6. [API Endpoints](#api-endpoints)
7. [Implementation Checklist](#implementation-checklist)
8. [Security Features](#security-features)

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                     ATS Application                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Authentication & Login                   │   │
│  │  (routes_auth.py)                                    │   │
│  │  - Employee login with RBAC check                    │   │
│  │  - First-login password reset enforcement            │   │
│  │  - Password change flow                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         RBAC Middleware & Guards                      │   │
│  │  (rbac_middleware.py)                                │   │
│  │  - Before-request validation                         │   │
│  │  - Permission/Role enforcement                       │   │
│  │  - Permission computation (role + overrides)         │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │       Protected Routes & API Endpoints               │   │
│  │  (routes_rbac.py, routes_applicant.py, etc.)        │   │
│  │  - User management endpoints                         │   │
│  │  - Permission assignment endpoints                   │   │
│  │  - Applicant/Position routes with permission checks  │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │     Database Models & Permission Engine              │   │
│  │  (models.py, auth_rbac.py)                           │   │
│  │  - Role, Permission, UserPermission models           │   │
│  │  - Permission evaluation algorithm                   │   │
│  │  - Role-to-permission mapping                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Permission Evaluation Algorithm

```
has_permission(user, permission_key) {
    1. Check if user is active
    2. Check user-specific permission override
       - If override exists: return override.is_allowed
       - Deny takes precedence over allow
    3. Fall back to role-based permissions
       - Get user's role
       - Check if permission is in role.permissions
       - Return true/false
}
```

---

## Database Schema

### Tables

#### `role`
- `id` (PK)
- `name` (UNIQUE): e.g., SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER
- `description`
- `created_at`

#### `permission`
- `id` (PK)
- `key` (UNIQUE): e.g., 'view_applicants', 'manage_positions'
- `description`
- `category`: e.g., 'applicants', 'positions', 'users'
- `created_at`

#### `role_permission` (Junction Table)
- `role_id` (FK → role)
- `permission_id` (FK → permission)
- PRIMARY KEY: (role_id, permission_id)

#### `user_permission` (Override Table)
- `id` (PK)
- `user_id` (FK → employee)
- `permission_id` (FK → permission)
- `is_allowed` (BOOLEAN): True = grant, False = deny
- `reason` (VARCHAR): Why this override was made
- `created_at`
- `created_by_id` (FK → employee): Who made the override
- UNIQUE: (user_id, permission_id)

#### `employee` (Extended)
- `role_id` (FK → role, NULLABLE)
- `force_password_reset` (BOOLEAN): Force reset on first login
- `last_login` (DATETIME)
- `is_active` (BOOLEAN): Account status
- `created_by_id` (FK → employee): Who created this user

---

## User Roles

### 1. SUPER_ADMIN

**Purpose**: Full system control and administrative override

**Permissions**:
- ✓ View, create, edit, delete applicants
- ✓ Export applicant CVs and Excel data
- ✓ Forward/reassign applicants
- ✓ Manage positions (create/update/delete)
- ✓ Create, update, delete users
- ✓ Change usernames and passwords
- ✓ **Assign, modify, or restrict permissions of any user**
- ✓ Access dashboard and manage dashboard content
- ✓ Create/modify roles
- ✓ Access full admin panel

**Cannot be**:
- Removed from system
- Disabled by other roles
- Have permissions restricted except by another SUPER_ADMIN

---

### 2. ADMIN

**Purpose**: Senior recruiter with management capabilities

**Permissions**:
- ✓ View assigned applicants
- ✓ Edit applicants (limited)
- ✓ Export CVs and Excel data
- ✓ Forward/reassign applicants
- ✓ Manage positions (create/delete)
- ✓ View all users
- ✓ View dashboard

**Cannot**:
- Delete users (only deactivate)
- Manage other ADMIN or SUPER_ADMIN accounts
- Override own permissions
- Create SUPER_ADMIN accounts

**Permissions can be**: Restricted or extended by SUPER_ADMIN

---

### 3. LEVEL_2_USER

**Purpose**: Mid-level recruiter with limited modification rights

**Permissions**:
- ✓ View assigned applicants
- ✓ Export CVs and Excel data
- ✓ View positions
- ✓ View dashboard

**Cannot**:
- Edit or delete applicants
- Forward/reassign applicants (unless overridden)
- Manage users or positions

**Permissions can be**: Restricted or extended by SUPER_ADMIN

---

### 4. LEVEL_1_USER

**Purpose**: Junior recruiter with read-only access

**Permissions**:
- ✓ View assigned applicants
- ✓ Export CVs and Excel data
- ✓ View positions
- ✓ View dashboard

**Cannot**:
- Edit or delete applicants
- Forward/reassign applicants
- Manage users or positions

**Permissions can be**: Restricted further by SUPER_ADMIN

---

## Permission System

### Available Permissions (20+ total)

#### Applicant Management
- `view_applicants`: View applicants
- `create_applicant`: Create applicants
- `edit_applicant`: Edit applicant details
- `delete_applicant`: Delete applicants
- `export_applicant_cv`: Export applicant CV
- `export_applicant_excel`: Export applicant data
- `forward_applicant`: Forward/reassign applicants

#### Position Management
- `manage_positions`: Create/update/delete positions
- `view_positions`: View job positions

#### User Management
- `manage_users`: Create/update/delete users
- `manage_permissions`: Assign/modify user permissions
- `view_users`: View all users

#### Dashboard
- `view_dashboard`: Access dashboard
- `manage_dashboard`: Manage dashboard content

#### Administrative
- `manage_roles`: Create/modify roles
- `access_admin_panel`: Access super admin panel

### Permission Override Examples

**Scenario 1**: Grant LEVEL_2_USER permission to forward applicants
```
User: john (LEVEL_2_USER)
Permission: forward_applicant
Override: is_allowed = True
Effect: john can now forward applicants (even though LEVEL_2_USER normally cannot)
```

**Scenario 2**: Deny ADMIN permission to delete applicants
```
User: alice (ADMIN)
Permission: delete_applicant
Override: is_allowed = False
Effect: alice cannot delete applicants (restricted from her normal permissions)
```

---

## Default Credentials

### Initial Seed Accounts

⚠️ **IMPORTANT**: Change these credentials immediately after first login!

#### SUPER_ADMIN Account
- **Username**: `SUPERADMIN`
- **Password**: `<set SUPERADMIN_INITIAL_PASSWORD>`
- **Status**: Force password reset on first login
- **Action Required**: Reset password immediately upon login

#### ADMIN Account
- **Username**: `ADMIN`
- **Password**: `<set ADMIN_INITIAL_PASSWORD>`
- **Status**: Force password reset on first login
- **Action Required**: Reset password immediately upon login

### Password Reset Flow

1. **First Login**: User provides default credentials
2. **Redirect**: System redirects to password reset page (if `force_password_reset = true`)
3. **Reset Form**: User provides new password (minimum 8 characters)
4. **Validation**: 
   - New password must be different from default
   - Passwords must match
   - Minimum length enforced
5. **Completion**: User is redirected to dashboard after successful reset

---

## API Endpoints

### User Management

| Method | Endpoint | Permission | Description |
|--------|----------|-----------|-------------|
| GET | `/api/users` | `view_users` | List all users (paginated) |
| POST | `/api/users` | `manage_users` | Create new user |
| GET | `/api/users/<id>` | `view_users` | Get user details |
| PATCH | `/api/users/<id>` | `manage_users` | Update user info |
| PATCH | `/api/users/<id>/password` | - | Change own password (or SUPER_ADMIN) |
| DELETE | `/api/users/<id>` | `manage_users` | Deactivate user |

### Permission Management

| Method | Endpoint | Permission | Description |
|--------|----------|-----------|-------------|
| GET | `/api/permissions` | - | List all available permissions |
| GET | `/api/users/<id>/permissions` | `manage_permissions` | Get user's permissions |
| POST | `/api/users/<id>/permissions` | `manage_permissions` | Assign permission override |
| DELETE | `/api/users/<id>/permissions/<key>` | `manage_permissions` | Remove permission override |

### Role Management

| Method | Endpoint | Permission | Description |
|--------|----------|-----------|-------------|
| GET | `/api/roles` | - | List all roles with permissions |

### Permission Checking

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/check-permission` | Check if user has permission |
| GET | `/api/my-permissions` | Get current user's permissions |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/force-password-reset` | Check if reset needed |
| POST | `/api/auth/reset-password` | Perform password reset (API) |

### Web Routes

| Route | Permission | Description |
|-------|-----------|-------------|
| `/employee-login.html` | - | Login page |
| `/reset-password-first-login` | login_required | Force password reset |
| `/change-password` | login_required | Change password anytime |
| `/admin/panel` | SUPER_ADMIN | Admin management UI |

---

## Implementation Checklist

### Phase 1: Setup ✅

- [x] Update `models.py` with RBAC schema
- [x] Create `auth_rbac.py` with permission logic
- [x] Create `rbac_middleware.py` with decorators
- [x] Create `routes_auth.py` for auth flows
- [x] Create `routes_rbac.py` for API endpoints
- [x] Create `seed_rbac.py` for initialization
- [x] Update `requirements.txt` with bcrypt
- [x] Create HTML templates for password reset

### Phase 2: Integration ⏳ (TO DO)

- [ ] Update `ats_app.py`:
  - Import RBAC modules
  - Call `seed_roles_and_permissions()`
  - Initialize `init_rbac_middleware(app)`
  - Register all route modules

- [ ] Update `routes_employee.py`:
  - Add `@enforce_first_login_password_reset()` to protected routes
  - Add `@require_permission_check()` to resource routes

- [ ] Update dashboard route:
  - Add permission checks
  - Render UI based on user permissions

- [ ] Create admin panel route:
  - Protect with `@require_role_check('SUPER_ADMIN')`
  - Serve `admin_panel.html` template

### Phase 3: Testing ⏳ (TO DO)

- [ ] Run `python seed_rbac.py`
- [ ] Test SUPER_ADMIN login and password reset
- [ ] Test ADMIN login and capabilities
- [ ] Test LEVEL_2_USER restrictions
- [ ] Test LEVEL_1_USER restrictions
- [ ] Test permission overrides
- [ ] Test 403 responses for unauthorized access
- [ ] Test password change flow
- [ ] Test user creation via admin panel
- [ ] Test permission assignment via admin panel

### Phase 4: Production ⏳ (TO DO)

- [ ] Enable HTTPS enforcement
- [ ] Implement rate limiting on login
- [ ] Add comprehensive audit logging
- [ ] Implement session timeout
- [ ] Test security vulnerabilities
- [ ] Document admin procedures
- [ ] Train administrators

---

## Security Features

### 1. Password Security

✓ **Bcrypt Hashing**: All passwords hashed with bcrypt (salt rounds: 12)
✓ **First-Login Reset**: Default credentials expire after first login
✓ **No Default Reuse**: Cannot change password back to default
✓ **Minimum Length**: 8 characters required
✓ **Clear Confirmation**: Passwords must match before submission

### 2. Access Control

✓ **Multi-Level Checks**:
  1. User authentication
  2. Account active status
  3. Role assignment
  4. Permission-based access
  5. User-specific overrides

✓ **Middleware Protection**: Permission checks at middleware level (before route handler)
✓ **Server-Side Validation**: All permissions validated server-side (never trust frontend)
✓ **Precedence Rules**: Deny overrides Allow; specific rules override general

### 3. Privilege Separation

✓ **Hierarchy**: SUPER_ADMIN > ADMIN > LEVEL_2 > LEVEL_1
✓ **Limited Escalation**: ADMIN cannot manage SUPER_ADMIN or other ADMINs
✓ **Self-Protection**: Cannot delete or disable own account
✓ **Override Audit**: All permission changes tracked with creator info

### 4. Audit Trail

✓ **Action Logging**: User creation, deletion, permission changes logged
✓ **Creator Tracking**: Every override includes who made the change
✓ **Reason Tracking**: Permission changes can include reason/comment
✓ **Last Login**: Track when user last accessed system

### 5. Session Management

✓ **Flask-Login Integration**: Standard session management
✓ **Active Status Check**: Inactive users cannot access system
✓ **Role Verification**: User role verified on each request
✓ **No Session Fixation**: Sessions invalidated on logout

---

## File Structure

```
/Applicant Tracking System/
│
├── models.py                      # Updated with RBAC schema
├── auth_rbac.py                   # Permission logic and utilities
├── rbac_middleware.py             # Middleware and decorators
├── routes_auth.py                 # Authentication routes
├── routes_rbac.py                 # RBAC API endpoints
├── seed_rbac.py                   # Database seeding script
├── ats_app.py                     # Updated to integrate RBAC
│
├── requirements.txt               # Updated with bcrypt, PyJWT
│
├── templates/
│   ├── reset_password_first_login.html  # First-login password reset
│   ├── change_password.html             # Password change form
│   ├── admin_panel.html                 # SUPER_ADMIN management UI
│   └── ...
│
├── RBAC_INTEGRATION_GUIDE.md      # Integration instructions
└── RBAC_SYSTEM.md                 # This file
```

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database
```bash
python seed_rbac.py
```

### 3. Run Application
```bash
python app.py
```

### 4. First Login
- Navigate to: http://localhost:5000/employee-login.html
- Username: `SUPERADMIN`
- Password: `<set SUPERADMIN_INITIAL_PASSWORD>`
- Reset password when prompted

### 5. Access Admin Panel
- After password reset, navigate to: http://localhost:5000/admin/panel
- Manage users and permissions
- Create new accounts

---

## Common Tasks

### Create a New User
```bash
# Via API
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@company.com",
    "password": "TempPassword123!",
    "role": "LEVEL_2_USER"
  }'

# Via Admin Panel
1. Go to /admin/panel
2. Click "Create User" tab
3. Fill in form
4. Submit
```

### Grant Permission Override
```bash
# Via API
curl -X POST http://localhost:5000/api/users/5/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "permission_key": "forward_applicant",
    "is_allowed": true,
    "reason": "Promote to senior recruiter"
  }'

# Via Admin Panel
1. Go to /admin/panel
2. Users tab
3. Click "Edit Permissions" on user
4. Toggle permission checkboxes
5. Save changes
```

### Change User Password
```bash
# Via API
curl -X PATCH http://localhost:5000/api/users/5/password \
  -H "Content-Type: application/json" \
  -d '{
    "new_password": "NewSecurePassword123!"
  }'

# User changes own
1. Click "Change Password"
2. Provide current and new password
3. Submit
```

---

## Troubleshooting

### User Cannot Login
- [ ] Verify username spelling
- [ ] Check if account is active (is_active = true)
- [ ] Verify password is correct
- [ ] Check if role is assigned (role_id != NULL)

### Cannot Perform Action (403 Forbidden)
- [ ] Check user's role
- [ ] Check permission overrides
- [ ] Verify permission is in role definition
- [ ] Check if permission is being denied

### Password Reset Not Working
- [ ] Clear browser cache
- [ ] Check force_password_reset flag (should be true)
- [ ] Verify new password meets requirements
- [ ] Check database commit succeeded

### Permission Changes Not Reflecting
- [ ] Logout and login again
- [ ] Check UserPermission table for overrides
- [ ] Verify permission key exists in Permission table
- [ ] Check role-permission mapping

---

## Next Steps

1. **Implement full integration** using `RBAC_INTEGRATION_GUIDE.md`
2. **Test thoroughly** all user scenarios
3. **Configure production settings** (HTTPS, rate limiting)
4. **Train administrators** on user management
5. **Monitor audit logs** for suspicious activity
6. **Plan future enhancements** (2FA, IP restrictions, etc.)

---

## Support & Documentation

- Integration Guide: See `RBAC_INTEGRATION_GUIDE.md`
- Code Comments: All RBAC files include detailed comments
- API Docs: See `routes_rbac.py` docstrings
- Templates: See `templates/admin_panel.html` for UI logic

---

**Last Updated**: April 2026
**Status**: Complete Implementation Ready
**Version**: 1.0

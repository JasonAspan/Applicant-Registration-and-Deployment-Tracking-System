# 🔐 RBAC Admin Panel - Complete UI Guide

## 🎯 Access the Admin Panel

**URL:** `http://localhost:5000/admin-panel.html`

**Requirements:**
- Must be logged in as a user with `manage_users` permission
- By default, only **SUPER_ADMIN** and **ADMIN** roles have this permission

---

## 📋 Features Overview

### 1. **📊 Dashboard**
- **Overview Statistics:**
  - Total Users count
  - Active Users count
  - Total Roles (4)
  - Total Permissions (16)
  
- **Quick Actions:**
  - Create New User
  - View All Permissions
  - View All Roles

- **System Information:**
  - RBAC Status (Active/Inactive)
  - Current logged-in user
  - Configured roles list
  - Last system update time

---

### 2. **👥 User Management**

#### Create New User
- **Fields:**
  - Username (unique, required)
  - Email (required)
  - Initial Password (min 8 chars, required)
  - Role Selection (LEVEL_1_USER, LEVEL_2_USER, ADMIN, SUPER_ADMIN)

- **Features:**
  - Password will be automatically reset on first login for security
  - User can be assigned any role
  - Email validation included

#### User List View
For each user, you can:
- **View user card** with:
  - Username and email
  - Assigned role badge
  - Active/Inactive status
  - Password reset flag (if applicable)

- **Actions available:**
  - 🔐 **Manage Permissions** - Open permission editor modal
  - ✏️ **Edit User** - Modify user details
  - 🔒 **Deactivate/Activate** - Toggle user status

---

### 3. **👔 Role Configuration**

View all **4 predefined roles** with their:
- **Role Name:** SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER
- **Description:** What the role does
- **Assigned Permissions:** Grid view of all permissions for that role

Each role has a specific set of baseline permissions:

#### SUPER_ADMIN
- All permissions (full system access)
- Can create and manage all users
- Can modify all permissions

#### ADMIN
- Can manage applicants and positions
- Can create LEVEL_1 and LEVEL_2 users
- Cannot create other ADMINs or modify their permissions

#### LEVEL_2_USER
- Can view applicants
- Can export CVs and data
- Cannot create/edit positions or users

#### LEVEL_1_USER
- Can view applicants
- Limited export capabilities
- Read-only access

---

### 4. **🔑 Permissions Catalog**

View all **16 available permissions** organized by category:

#### Applicant Management (6 permissions)
- `view_applicants` - View applicants
- `create_applicant` - Create applicants
- `edit_applicant` - Edit applicants
- `delete_applicant` - Delete applicants
- `export_applicant_cv` - Export CV
- `export_applicant_excel` - Export to Excel

#### Position Management (2 permissions)
- `manage_positions` - Create/Update/Delete positions
- `view_positions` - View positions

#### User Management (4 permissions)
- `manage_users` - Create/Update/Delete users
- `view_users` - View user list
- `edit_user_role` - Change user roles
- `manage_user_permissions` - Grant/Revoke permissions

#### Admin Features (4 permissions)
- `view_audit_logs` - View activity logs
- `system_settings` - Modify system settings
- `view_reports` - Access reports
- `view_analytics` - View analytics

---

### 5. **🔐 Permission Management (Modal)**

When you click **🔐 Permissions** on a user:

- **User Info Display:**
  - Username shown
  - Current role displayed

- **Permission Grid:**
  - All permissions shown as cards
  - Checkbox for each permission
  - "Grant Permission" label
  - Shows if permission is a custom override

- **How It Works:**
  - ✅ **Checked** = Permission granted (either from role or override)
  - ❌ **Unchecked** = Permission denied (override takes precedence)
  - 🔹 **Custom Override** indicator = User-specific modification

- **Save Changes:**
  - Click "Save Changes" button
  - System updates permission overrides
  - User gets new permissions immediately

---

### 6. **⚙️ Settings & Configuration**

#### 🔒 Security Settings
- **Force Password Reset on First Login** (toggle)
  - Enabled by default
  - Forces users to set their own password on first login
  
- **Password Expiration (days)**
  - Default: 90 days
  - Set to 0 to disable

#### 🔐 Permission Settings
- **Strict Permission Checking** (toggle)
  - When enabled, any DENY permission blocks access
  - Deny takes precedence over allow

#### 📋 Audit Settings
- **Log All Login Attempts** (toggle)
  - Track user access patterns
  
- **Log Permission Changes** (toggle)
  - Track when permissions are modified

---

## 🎨 UI Components & Design

### Color Scheme
- **Primary:** Purple gradient (#667eea → #764ba2)
- **Success:** Green (#28a745)
- **Danger:** Red (#dc3545)
- **Warning:** Orange (#ffc107)
- **Info:** Blue (#17a2b8)

### Navigation
- **Left Sidebar** with 5 main sections:
  - 📊 Dashboard
  - 👥 Users
  - 👔 Roles
  - 🔑 Permissions
  - ⚙️ Settings

- **Tab indicators** show active section
- **Sticky sidebar** for easy navigation

### Cards & Badges
- **Role Badges:** Color-coded by role type
- **Status Badges:** Active (green) / Inactive (red)
- **Permission Cards:** Display key, description, category
- **User Cards:** Display user info with action buttons

---

## 🔄 User Workflow Example

### Scenario: Create LEVEL_1_USER and Grant Custom Permission

1. **Navigate to Users** → Click "Create New User"
2. **Fill in details:**
   - Username: john.doe
   - Email: john@company.com
   - Password: TempPassword123
   - Role: LEVEL_1_USER
3. **Click "Create User"**
4. **User appears in list** with role badge
5. **Click "🔐 Permissions"** on new user
6. **In modal:**
   - Find `export_applicant_excel`
   - Check the checkbox to grant permission
7. **Click "Save Changes"**
8. **User now has that extra permission**

---

## 🛡️ Permission Logic

### How Permissions Work

**For each permission check:**

1. **Check SUPER_ADMIN** → If yes, always allow ✅
2. **Check User-Specific Overrides**
   - If DENY exists → Block access ❌
   - If ALLOW exists → Grant access ✅
3. **Check Role Permissions** → Use role defaults
4. **If no override/role perm** → Deny by default ❌

**Example:**
```
User: john_doe
Role: LEVEL_1_USER (only has: view_applicants)

Override: export_applicant_excel = ALLOW
Override: delete_applicant = DENY

Result:
- view_applicants: ✅ (from role)
- export_applicant_excel: ✅ (from override)
- delete_applicant: ❌ (from override)
- create_applicant: ❌ (not in role, no override)
```

---

## 📱 Responsive Design

The admin panel is **fully responsive:**
- **Desktop:** 3-column sidebar + main content
- **Tablet:** Adjusted sidebar width
- **Mobile:** Stack layout, collapsible sidebar

---

## 🚀 Quick Tips

1. **Always change default passwords** after creating users
2. **SUPER_ADMIN account** should be protected
3. **Use permission overrides** sparingly to avoid confusion
4. **Enable audit logging** to track changes
5. **Set password expiration** for security compliance
6. **Review user permissions** regularly
7. **Deactivate unused accounts** instead of deleting

---

## 🔗 Related API Endpoints

All operations use these API endpoints:

```
GET  /api/users                          - List all users
GET  /api/users/<id>/permissions        - Get user permissions
POST /api/users/<id>/permissions        - Grant permission
DELETE /api/users/<id>/permissions/<key> - Revoke permission

GET  /api/roles                          - List all roles
GET  /api/permissions                    - List all permissions
GET  /api/my-permissions                 - Get current user permissions
```

---

**Status:** ✅ Production Ready | **Version:** 1.0 | **Last Updated:** April 2026

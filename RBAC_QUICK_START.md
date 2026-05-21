# 🚀 Quick Start: Accessing the RBAC Admin Panel

## ⏱️ TL;DR - Get Started in 30 Seconds

1. **Open browser** → Go to: `http://localhost:5000/admin-panel.html`
2. **You're already logged in** as SUPERADMIN
3. **Explore the 5 main sections** using the left sidebar
4. **That's it!** The panel is fully functional

---

## 🔑 Access Requirements

The RBAC Admin Panel requires:
- ✅ User must be logged in
- ✅ User must have `manage_users` permission
- ✅ By default: **SUPERADMIN** and **ADMIN** roles have this permission

### Default Admin Accounts

| Role | Username | Password | First Login |
|------|----------|----------|-------------|
| Super Admin | SUPERADMIN | <set SUPERADMIN_INITIAL_PASSWORD> | Reset required |
| Admin | ADMIN | <set ADMIN_INITIAL_PASSWORD> | Reset required |

---

## 📍 Navigation Map

```
http://localhost:5000/admin-panel.html
│
├── 📊 Dashboard (Default)
│   ├── Statistics Cards
│   ├── Quick Actions
│   └── System Info
│
├── 👥 Users
│   ├── Create New User Form
│   └── Users List
│       ├── View Details
│       ├── Manage Permissions (Modal)
│       ├── Edit User
│       └── Deactivate/Activate
│
├── 👔 Roles
│   ├── SUPER_ADMIN
│   ├── ADMIN
│   ├── LEVEL_2_USER
│   └── LEVEL_1_USER
│       (Each with permission list)
│
├── 🔑 Permissions
│   ├── Applicant Management (6)
│   ├── Position Management (2)
│   ├── User Management (4)
│   └── Admin Features (4)
│
└── ⚙️ Settings
    ├── Security Settings
    ├── Permission Settings
    └── Audit Settings
```

---

## 📊 Dashboard - Overview

The **Dashboard** is your command center with:

### Statistics (4 Cards)
```
👥 Total Users        ✅ Active Users       👔 Total Roles       🔑 Total Perms
    15                    12                    4                     16
```

### Quick Actions
```
[➕ Create User]  [🔍 View Permissions]  [📋 View Roles]
```

### System Information Table
```
Status:           🟢 Active
Current User:     SUPERADMIN
Roles:            4 (SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER)
Last Updated:     Just now
```

---

## 👥 Users - Complete User Management

### Create a New User

**Step 1:** Navigate to **👥 Users** tab

**Step 2:** Fill the "Create New User" form
```
Username:        [john.doe____________]
Email:           [john@company.com____]
Password:        [TempPassword123_____] (min 8 chars)
Role:            [LEVEL_2_USER ▼]
```

**Step 3:** Click **"✅ Create User"**

**Note:** User will be forced to reset password on first login.

### Manage Existing Users

Each user in the list shows:
```
👤 john.doe
john@company.com
[ADMIN] [🟢 Active]
[🔐 Permissions] [✏️ Edit] [🔒 Deactivate]
```

#### 🔐 Edit Permissions
1. Click **🔐 Permissions** button
2. Modal opens with permission grid
3. Check/uncheck permissions as needed
4. Click **💾 Save Changes**

#### ✏️ Edit User
- Change user details (coming soon)

#### 🔒 Deactivate/Activate
- Toggle user status
- Deactivated users cannot login

---

## 👔 Roles - View Role Definitions

View all 4 roles with their baseline permissions:

### Role Hierarchy
```
SUPER_ADMIN (16 permissions)
  └─ Full system access, manage all users

ADMIN (12 permissions)
  └─ Manage applicants & positions, create lower users

LEVEL_2_USER (6 permissions)
  └─ View & export applicants, limited actions

LEVEL_1_USER (4 permissions)
  └─ Read-only access, minimal permissions
```

Each role card shows:
- **Role name** and description
- **Permission count**
- **All assigned permissions** in a grid

---

## 🔑 Permissions - Permission Catalog

View all **16 available permissions** organized by category:

### Permission Categories

#### 🗂️ Applicant Management (6)
- `view_applicants` - View applicants list
- `create_applicant` - Add new applicants
- `edit_applicant` - Modify applicant info
- `delete_applicant` - Remove applicants
- `export_applicant_cv` - Download CVs
- `export_applicant_excel` - Export to Excel

#### 📍 Position Management (2)
- `manage_positions` - Create/Edit/Delete positions
- `view_positions` - View open positions

#### 👥 User Management (4)
- `manage_users` - Create/Edit/Delete users
- `view_users` - View user list
- `edit_user_role` - Change user roles
- `manage_user_permissions` - Grant/Revoke perms

#### ⚙️ Admin Features (4)
- `view_audit_logs` - View activity logs
- `system_settings` - Modify settings
- `view_reports` - Access reports
- `view_analytics` - View analytics

---

## ⚙️ Settings - System Configuration

### 🔒 Security Settings

**Force Password Reset on First Login**
- ✅ Default: ON
- Forces new users to set their own password
- Best practice for security

**Password Expiration**
- Default: 90 days
- Set to 0 to disable
- Enforces periodic password changes

### 🔐 Permission Settings

**Strict Permission Checking**
- ☐ Default: OFF
- When ON: Any DENY permission blocks access
- Deny takes precedence over Allow

### 📋 Audit Settings

**Log All Login Attempts**
- ✅ Default: ON
- Tracks when users login/logout

**Log Permission Changes**
- ✅ Default: ON
- Tracks all permission modifications

---

## 🎯 Common Tasks

### Task 1: Create a New Employee
```
1. Go to 👥 Users
2. Fill in Create User form
3. Set role to LEVEL_1_USER or LEVEL_2_USER
4. Click "Create User"
5. User appears in list
6. User will be prompted to reset password on first login
```

### Task 2: Grant Special Permission to User
```
1. Go to 👥 Users
2. Find user in list
3. Click "🔐 Permissions"
4. Find permission you want to grant
5. Check the checkbox
6. Click "Save Changes"
7. User now has that permission
```

### Task 3: Deactivate a User
```
1. Go to 👥 Users
2. Find user
3. Click "🔒 Deactivate"
4. Confirm in dialog
5. User marked as inactive
6. User cannot login (optional enforcement)
```

### Task 4: View What a Role Can Do
```
1. Go to 👔 Roles
2. Find the role card
3. See all permissions in the grid
4. Each permission shows category & description
```

### Task 5: Check System Security Settings
```
1. Go to ⚙️ Settings
2. Review "🔒 Security Settings"
3. Adjust password expiration if needed
4. Enable/disable first login reset
5. Click "Save"
```

---

## 🔄 Permission Logic Explained

### How Permissions Work

When a user tries to access something:

```
Step 1: Is user SUPER_ADMIN?
  YES → Allow access immediately ✅
  
Step 2: Check User-Specific Overrides
  ALLOW found?    → Grant access ✅
  DENY found?     → Block access ❌
  Not found?      → Go to Step 3
  
Step 3: Check Role Permissions
  Permission in role? → Grant access ✅
  Not in role?        → Block access ❌
```

### Example Scenario

```
User: jane_smith
Role: LEVEL_2_USER

Role Permissions:
  ✅ view_applicants
  ✅ export_applicant_cv
  ✅ export_applicant_excel

Overrides Set:
  ✅ delete_applicant = ALLOW (added by admin)
  ❌ manage_positions = DENY (removed by admin)

Result:
  ✅ view_applicants      (from role)
  ✅ export_applicant_cv  (from role)
  ✅ delete_applicant     (from override)
  ❌ manage_positions     (from override)
  ❌ create_applicant     (not in role, no override)
```

---

## 🎨 UI Tips & Tricks

### Navigation Tips
- **Left sidebar sticks** when scrolling - always visible
- **Tab indicators** show which section is active
- **Color coding** on badges shows role/status
- **Hover effects** on cards show interactivity

### Data Display Tips
- **User cards** show all info at a glance
- **Permission cards** organized by category
- **Role cards** expandable with permissions
- **Stat cards** show key metrics

### Action Tips
- **Modal opens** for detailed operations
- **Confirmations** prevent accidental actions
- **Checkboxes** for bulk-like operations
- **Buttons** grouped by action type

---

## ⚡ Performance Notes

The admin panel is optimized for:
- ✅ Fast data loading (API integration)
- ✅ Smooth animations (0.3s transitions)
- ✅ Responsive design (mobile-friendly)
- ✅ Accessible interface (WCAG standards)

---

## 🐛 Troubleshooting

### Can't Access Admin Panel
**Error:** 403 Forbidden

**Solution:**
- Check if logged in
- Check if user has `manage_users` permission
- Try logging in as SUPERADMIN

### Permissions Not Updating
**Problem:** Saved permissions don't take effect

**Solution:**
- Refresh page
- Clear browser cache
- Try logging out and back in
- Check user's role permissions

### Sidebar Not Sticky on Mobile
**Expected Behavior:** On mobile, sidebar scrolls with content
- This is by design for mobile usability
- Use horizontal swipe to access on very small screens

---

## 📞 Support Resources

### Documentation Files
- **RBAC_SYSTEM.md** - Complete reference
- **RBAC_INTEGRATION_GUIDE.md** - Integration steps
- **RBAC_USAGE_EXAMPLES.py** - Code examples
- **IMPLEMENTATION_CHECKLIST.md** - Setup guide

### Key Files
- **rbac_admin_panel.html** - The admin UI
- **auth_rbac.py** - Permission engine
- **routes_rbac.py** - API endpoints
- **models.py** - Database schema

---

## ✨ What's Next?

1. ✅ Explore the Dashboard
2. ✅ Create test users
3. ✅ Manage their permissions
4. ✅ Review role definitions
5. ✅ Check security settings
6. ✅ Deploy to production

---

**Status:** ✅ Ready to Use  
**Version:** 1.0  
**Last Updated:** April 2026  

**Questions?** Check the documentation files or review the inline code comments!

# 🎨 RBAC Admin Panel - Visual Walkthrough

## 🚀 Step 1: Access the Admin Panel

**URL:** `http://localhost:5000/admin-panel.html`

After logging in as SUPERADMIN, you'll see:

```
╔══════════════════════════════════════════════════════════════════════╗
║                     🔐 RBAC Admin Control Panel                      ║
║           Role-Based Access Control & Permission Management          ║
╚══════════════════════════════════════════════════════════════════════╝

┌──────────────────────┬────────────────────────────────────────────────┐
│   SIDEBAR MENU       │           DASHBOARD CONTENT                    │
│ ┌────────────────┐   │                                                │
│ │ 📊 Dashboard   │   │ 📊 Dashboard Overview                          │
│ │ 👥 Users       │   │                                                │
│ │ 👔 Roles       │   │ Statistics:                                    │
│ │ 🔑 Permissions │   │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐          │
│ │ ⚙️  Settings    │   │ │ 👥   │ │ ✅   │ │ 👔   │ │ 🔑   │          │
│ │                │   │ │ 15   │ │ 12   │ │ 4    │ │ 16   │          │
│ │                │   │ │Users │ │Active│ │Roles │ │Perms │          │
│ │                │   │ └──────┘ └──────┘ └──────┘ └──────┘          │
│ └────────────────┘   │                                                │
│                      │ Quick Actions:                                 │
│                      │ [➕ Create] [🔍 View] [📋 Logs]               │
│                      │                                                │
│                      │ System Info:                                   │
│                      │ Status: 🟢 Active                              │
│                      │ User: SUPERADMIN                               │
│                      │ Roles: 4 configured                            │
└──────────────────────┴────────────────────────────────────────────────┘
```

---

## 👥 Step 2: Manage Users

Click **👥 Users** in the sidebar:

```
┌──────────────────────────────────────────────────────────────────────┐
│ USERS SECTION                                                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ CREATE NEW USER FORM:                                                │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ Username:  [john_doe______________]                           ║   │
│ ║ Email:     [john@company.com_____]                            ║   │
│ ║ Password:  [MinimumPassword123___] (min 8 chars)             ║   │
│ ║ Role:      [LEVEL_2_USER        ▼]                           ║   │
│ ║                                                               ║   │
│ ║ ⚠️  User will be forced to reset password on first login      ║   │
│ ║                                                               ║   │
│ ║                               [✅ Create User]                ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ ALL USERS:                                                            │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 👤 SUPERADMIN                                                   │ │
│ │ superadmin@company.com                                          │ │
│ │ [SUPER_ADMIN] [🟢 Active]                                       │ │
│ │ [🔐 Permissions] [✏️ Edit] [🔒 Deactivate]                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 👤 ADMIN                                                        │ │
│ │ admin@company.com                                               │ │
│ │ [ADMIN] [🟢 Active]                                             │ │
│ │ [🔐 Permissions] [✏️ Edit] [🔒 Deactivate]                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 👤 john_doe                                                     │ │
│ │ john@company.com                                                │ │
│ │ [LEVEL_2_USER] [🟢 Active] [⚠️ Reset Password]                 │ │
│ │ [🔐 Permissions] [✏️ Edit] [🔒 Deactivate]                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Step 3: Edit User Permissions (Modal)

Click **🔐 Permissions** on any user:

```
╔══════════════════════════════════════════════════════════════════════╗
║ ✏️  Edit User Permissions                                      [✕]   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║ User: john_doe                                                       ║
║ Role: LEVEL_2_USER                                                   ║
║                                                                      ║
║ Permission Overrides:                                                ║
║                                                                      ║
║ ┌────────────────────────┐ ┌────────────────────────┐               ║
║ │ ☑ view_applicants      │ │ ☑ export_applicant_cv │               ║
║ │   View applicants      │ │   Export applicant CV │               ║
║ │ [applicants]           │ │ [applicants]          │               ║
║ └────────────────────────┘ └────────────────────────┘               ║
║                                                                      ║
║ ┌────────────────────────┐ ┌────────────────────────┐               ║
║ │ ☑ export_app_excel     │ │ ☐ manage_positions     │               ║
║ │   Export to Excel      │ │   Manage positions     │               ║
║ │ [applicants] 🔹        │ │ [positions]            │               ║
║ │ Custom override        │ │                        │               ║
║ └────────────────────────┘ └────────────────────────┘               ║
║                                                                      ║
║ ┌────────────────────────┐ ┌────────────────────────┐               ║
║ │ ☐ manage_users         │ │ ☐ view_audit_logs      │               ║
║ │   Manage users         │ │   View audit logs      │               ║
║ │ [users]                │ │ [admin]                │               ║
║ └────────────────────────┘ └────────────────────────┘               ║
║                                                                      ║
║ [Close]  [💾 Save Changes]                                           ║
╚══════════════════════════════════════════════════════════════════════╝

Legend:
  ☑ = Permission granted
  ☐ = Permission denied/not set
  🔹 = Custom override (different from role default)
```

---

## 👔 Step 4: View Roles

Click **👔 Roles** in the sidebar:

```
┌──────────────────────────────────────────────────────────────────────┐
│ ROLES SECTION                                                         │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ℹ️  Roles define baseline permissions. Users can have individual     │
│    overrides.                                                         │
│                                                                       │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ SUPER_ADMIN                                                   ║   │
│ ║ Unlimited system access - all permissions included           ║   │
│ ║                                                               ║   │
│ ║ Permissions (16):                                             ║   │
│ ║ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐  ║   │
│ ║ │ view_applicants  │ │ edit_applicant   │ │ delete_appli │  ║   │
│ ║ │ View applicants  │ │ Edit applicants  │ │ Delete appli │  ║   │
│ ║ │ [applicants]     │ │ [applicants]     │ │ [applicants] │  ║   │
│ ║ └──────────────────┘ └──────────────────┘ └──────────────┘  ║   │
│ ║                                                               ║   │
│ ║ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐  ║   │
│ ║ │ manage_users     │ │ system_settings  │ │ view_reports │  ║   │
│ ║ │ Manage users     │ │ System settings  │ │ View reports │  ║   │
│ ║ │ [users]          │ │ [admin]          │ │ [admin]      │  ║   │
│ ║ └──────────────────┘ └──────────────────┘ └──────────────┘  ║   │
│ ║                  ... (10 more permissions)                    ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ ADMIN                                                           ║   │
│ ║ Manager role - applicants & positions management              ║   │
│ ║                                                               ║   │
│ ║ Permissions (12):                                             ║   │
│ ║ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐  ║   │
│ ║ │ view_applicants  │ │ manage_positions │ │ edit_appli   │  ║   │
│ ║ │ View applicants  │ │ Manage positions │ │ Edit appli   │  ║   │
│ ║ │ [applicants]     │ │ [positions]      │ │ [applicants] │  ║   │
│ ║ └──────────────────┘ └──────────────────┘ └──────────────┘  ║   │
│ ║                  ... (9 more permissions)                      ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ LEVEL_2_USER                                                  ║   │
│ ║ Read-only with export capabilities                           ║   │
│ ║                                                               ║   │
│ ║ Permissions (6):                                              ║   │
│ ║ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐  ║   │
│ ║ │ view_applicants  │ │ export_cv        │ │ export_excel │  ║   │
│ ║ │ View applicants  │ │ Export CV        │ │ Export Excel │  ║   │
│ ║ │ [applicants]     │ │ [applicants]     │ │ [applicants] │  ║   │
│ ║ └──────────────────┘ └──────────────────┘ └──────────────┘  ║   │
│ ║                  ... (3 more permissions)                      ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ LEVEL_1_USER                                                  ║   │
│ ║ Basic viewer with minimal access                             ║   │
│ ║                                                               ║   │
│ ║ Permissions (4):                                              ║   │
│ ║ ┌──────────────────┐ ┌──────────────────┐                    ║   │
│ ║ │ view_applicants  │ │ view_positions   │                    ║   │
│ ║ │ View applicants  │ │ View positions   │                    ║   │
│ ║ │ [applicants]     │ │ [positions]      │                    ║   │
│ ║ └──────────────────┘ └──────────────────┘                    ║   │
│ ║                  ... (2 more permissions)                      ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Step 5: View All Permissions

Click **🔑 Permissions** in the sidebar:

```
┌──────────────────────────────────────────────────────────────────────┐
│ PERMISSIONS SECTION                                                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ℹ️  All available permissions in the system.                         │
│    Users inherit from roles and get individual overrides.            │
│                                                                       │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│ │ view_applicants  │ │ edit_applicant   │ │ create_applicant │     │
│ │ View applicants  │ │ Edit applicants  │ │ Create applicant │     │
│ │ [applicants]     │ │ [applicants]     │ │ [applicants]     │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│ │ delete_applicant │ │ export_app_cv    │ │ export_app_excel │     │
│ │ Delete applicant │ │ Export app CV    │ │ Export app Excel │     │
│ │ [applicants]     │ │ [applicants]     │ │ [applicants]     │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│ │ manage_positions │ │ view_positions   │ │ manage_users     │     │
│ │ Manage positions │ │ View positions   │ │ Manage users     │     │
│ │ [positions]      │ │ [positions]      │ │ [users]          │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│ │ view_users       │ │ edit_user_role   │ │ manage_user_perms│     │
│ │ View users       │ │ Edit user role   │ │ Manage user perm │     │
│ │ [users]          │ │ [users]          │ │ [users]          │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐     │
│ │ view_audit_logs  │ │ system_settings  │ │ view_reports     │     │
│ │ View audit logs  │ │ System settings  │ │ View reports     │     │
│ │ [admin]          │ │ [admin]          │ │ [admin]          │     │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘     │
│                                                                       │
│ ┌──────────────────┐                                                 │
│ │ view_analytics   │                                                 │
│ │ View analytics   │                                                 │
│ │ [admin]          │                                                 │
│ └──────────────────┘                                                 │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Step 6: Configure Settings

Click **⚙️ Settings** in the sidebar:

```
┌──────────────────────────────────────────────────────────────────────┐
│ SETTINGS SECTION                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ 🔒 SECURITY SETTINGS                                                  │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ ☑ Force Password Reset on First Login                         ║   │
│ ║   Users must change password on login                         ║   │
│ ║                                                               ║   │
│ ║ Password Expiration: [90] days                                ║   │
│ ║ (Set 0 to disable)                                            ║   │
│ ║                                                               ║   │
│ ║                              [💾 Save]                        ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ 🔐 PERMISSION SETTINGS                                                │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ ☐ Strict Permission Checking                                  ║   │
│ ║   Deny takes precedence over allow                            ║   │
│ ║                                                               ║   │
│ ║                              [💾 Save]                        ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
│ 📋 AUDIT SETTINGS                                                     │
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ ☑ Log All Login Attempts                                      ║   │
│ ║   Track when users access the system                          ║   │
│ ║                                                               ║   │
│ ║ ☑ Log Permission Changes                                      ║   │
│ ║   Track all permission modifications                          ║   │
│ ║                                                               ║   │
│ ║                              [💾 Save]                        ║   │
│ ╚═══════════════════════════════════════════════════════════════╝   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Color Coding Guide

| Color | Meaning | Example |
|-------|---------|---------|
| 🔴 Red | Danger/Super Admin | SUPER_ADMIN role |
| 🟠 Orange | Warning/Admin | ADMIN role |
| 🔵 Blue | Info/Level 2 | LEVEL_2_USER role |
| ⚫ Gray | Level 1/Inactive | LEVEL_1_USER, Inactive user |
| 🟢 Green | Active/Success | Active users, ✅ checkmarks |

---

## 📊 Key Metrics Displayed

**Dashboard Statistics:**
```
Total Users:     Count of all users in system
Active Users:    Users with is_active = true
Total Roles:     4 (SUPER_ADMIN, ADMIN, LEVEL_2, LEVEL_1)
Total Perms:     16 permissions available
```

**User Information:**
```
Role:            Assigned role (determines baseline perms)
Status:          Active/Inactive
Last Login:      When user last accessed system
Password Reset:  ⚠️ Required on first login
```

**Permission Categories:**
```
Applicants (🗂️):   6 permissions
Positions (📍):    2 permissions
Users (👥):        4 permissions
Admin (⚙️):        4 permissions
```

---

## 🚀 What Happens When You Save?

### Creating a User:
1. User added to database with hashed password
2. User assigned to role with baseline permissions
3. `force_password_reset` flag set to TRUE
4. User appears in user list immediately
5. User must reset password on first login

### Editing Permissions:
1. Permission overrides stored in database
2. Changes applied immediately
3. User's effective permissions updated
4. Next action checks updated permissions
5. Audit log records the change (if enabled)

### Changing Settings:
1. System-wide settings updated
2. Applied to all new operations
3. Existing sessions may need refresh
4. Takes effect after page reload

---

**Ready to explore?** Go to: `http://localhost:5000/admin-panel.html`

🎉 Welcome to your RBAC Admin Control Panel!

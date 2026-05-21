# RBAC Fix TODO

## Completed
- [x] Stop running server
- [x] Read all relevant source files
- [x] Edit ats_app.py - Wire up RBAC middleware, seed roles/permissions, register RBAC & Auth routes
- [x] Edit routes_employee.py - Remove duplicate login/logout, assign default role on registration, fix admin panel template
- [x] Edit routes_auth.py - Rename employee_logout to logout for template compatibility
- [x] Edit base_employee.html - Add admin panel navigation link
- [x] Seed database with roles/permissions/users
- [x] Fix existing employees without roles (assigned default roles)
- [x] Restart server and verify endpoints respond
- [x] Final end-to-end verification


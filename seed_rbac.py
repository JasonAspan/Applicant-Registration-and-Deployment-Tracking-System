"""
Seed script for ATS RBAC system.

Creates initial roles, permissions, and default users:
- SUPER_ADMIN (username: SUPERADMIN)
- ADMIN (username: ADMIN)

Run with: python seed_rbac.py

Initial passwords are read from SUPERADMIN_INITIAL_PASSWORD and
ADMIN_INITIAL_PASSWORD, or prompted interactively.
"""

import sys
import os
from getpass import getpass

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_app import create_app, db
from models import Employee, Role, Permission
from auth_rbac import seed_roles_and_permissions, ROLE_PERMISSIONS, PERMISSION_KEYS


def initial_password(env_name, username):
    password = os.environ.get(env_name)
    if password:
        return password
    return getpass(f'Initial password for {username}: ')


def seed_database():
    """Seed initial roles, permissions, and users."""
    
    app = create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home')
    
    with app.app_context():
        print("\n" + "="*60)
        print("ATS RBAC System - Database Seeding")
        print("="*60)
        
        # Create all tables
        print("\n[1/4] Creating database tables...")
        db.create_all()
        print("✓ Tables created successfully")
        
        # Seed roles and permissions
        print("\n[2/4] Seeding roles and permissions...")
        seed_roles_and_permissions()
        print(f"✓ Created {len(ROLE_PERMISSIONS)} roles")
        print(f"✓ Created {len(PERMISSION_KEYS)} permissions")
        
        # Create SUPER_ADMIN user
        print("\n[3/4] Creating default SUPER_ADMIN user...")
        superadmin_user = Employee.query.filter_by(username='SUPERADMIN').first()
        
        if superadmin_user:
            print("⚠ SUPERADMIN user already exists, skipping creation")
        else:
            superadmin_role = Role.query.filter_by(name='SUPER_ADMIN').first()
            if not superadmin_role:
                print("✗ SUPER_ADMIN role not found")
                return False
            
            superadmin = Employee(
                username='SUPERADMIN',
                email='superadmin@company.com',
                role_id=superadmin_role.id,
                force_password_reset=True,
                is_active=True
            )
            superadmin.set_password(initial_password('SUPERADMIN_INITIAL_PASSWORD', 'SUPERADMIN'))
            db.session.add(superadmin)
            db.session.commit()
            print("✓ SUPERADMIN user created")
            print("   Username: SUPERADMIN")
            print("   Password: set from environment/prompt")
            print("   Status: Force password reset on first login")
        
        # Create ADMIN user
        print("\n[4/4] Creating default ADMIN user...")
        admin_user = Employee.query.filter_by(username='ADMIN').first()
        
        if admin_user:
            print("⚠ ADMIN user already exists, skipping creation")
        else:
            admin_role = Role.query.filter_by(name='ADMIN').first()
            if not admin_role:
                print("✗ ADMIN role not found")
                return False
            
            admin = Employee(
                username='ADMIN',
                email='admin@company.com',
                role_id=admin_role.id,
                force_password_reset=True,
                is_active=True,
                created_by_id=superadmin_user.id if superadmin_user else None
            )
            admin.set_password(initial_password('ADMIN_INITIAL_PASSWORD', 'ADMIN'))
            db.session.add(admin)
            db.session.commit()
            print("✓ ADMIN user created")
            print("   Username: ADMIN")
            print("   Password: set from environment/prompt")
            print("   Status: Force password reset on first login")
        
        print("\n" + "="*60)
        print("✓ Database seeding completed successfully!")
        print("="*60)
        print("\nNEXT STEPS:")
        print("1. Start the application")
        print("2. Log in as SUPERADMIN with the password you provided")
        print("3. You will be forced to change the password")
        print("4. Create additional users and assign roles via admin panel")
        print("\nSECURITY REMINDERS:")
        print("- Rotate any previously seeded default passwords immediately!")
        print("- Use strong, unique passwords for all accounts")
        print("- Never commit default credentials to version control")
        print("- Enable password hashing verification in production")
        print("\n")
        
        return True


if __name__ == '__main__':
    try:
        success = seed_database()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

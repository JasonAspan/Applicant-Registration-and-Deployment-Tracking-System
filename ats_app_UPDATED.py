"""
Updated ats_app.py with full RBAC integration

This file shows how to integrate all RBAC components into the Flask app.
"""

from flask import Flask, redirect, url_for
from flask_login import LoginManager
from sqlalchemy import inspect, text

from config import Config
from models import db, Employee, Role

# RBAC Imports
from auth_rbac import seed_roles_and_permissions
from rbac_middleware import init_rbac_middleware


login_manager = LoginManager()
login_manager.login_view = 'employee_login'
login_manager.login_message = 'Employee login required for dashboard.'


@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))


def ensure_db_schema():
    """Ensure database schema is up to date."""
    try:
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        def ensure_varchar_len(table, column, min_len):
            if table not in tables:
                return
            col = next((c for c in inspector.get_columns(table) if c['name'] == column), None)
            if not col:
                return
            length = getattr(col.get('type'), 'length', None)
            if length is not None and length < min_len:
                db.session.execute(text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR({min_len})'))
                db.session.commit()

        ensure_varchar_len('employee', 'password_hash', 255)
        
        if 'employee' in tables:
            employee_cols = {c['name'] for c in inspector.get_columns('employee')}
            if 'profile_filename' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN profile_filename VARCHAR(255)'))
                db.session.commit()
            if 'profile_content_type' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN profile_content_type VARCHAR(100)'))
                db.session.commit()
            if 'profile_data' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN profile_data BYTEA'))
                db.session.commit()
            
            # RBAC: Add RBAC columns if they don't exist
            if 'role_id' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN role_id INTEGER REFERENCES role(id)'))
                db.session.commit()
            if 'force_password_reset' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN force_password_reset BOOLEAN DEFAULT FALSE'))
                db.session.commit()
            if 'last_login' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN last_login TIMESTAMP'))
                db.session.commit()
            if 'is_active' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN is_active BOOLEAN DEFAULT TRUE'))
                db.session.commit()
            if 'created_by_id' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN created_by_id INTEGER REFERENCES employee(id)'))
                db.session.commit()

        if 'applicant' not in tables:
            return

        cols = {c['name'] for c in inspector.get_columns('applicant')}
        if 'gender' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN gender VARCHAR(10)'))
            db.session.commit()
        if 'password_hash' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN password_hash VARCHAR(128)'))
            db.session.commit()
        ensure_varchar_len('applicant', 'password_hash', 255)

        if 'cv_filename' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN cv_filename VARCHAR(255)'))
            db.session.commit()
        if 'cv_content_type' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN cv_content_type VARCHAR(100)'))
            db.session.commit()
        if 'cv_data' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN cv_data BYTEA'))
            db.session.commit()

        applicant_cols_by_name = {c['name']: c for c in inspector.get_columns('applicant')}
        resume_col = applicant_cols_by_name.get('resume')
        if resume_col and not resume_col.get('nullable', True):
            db.session.execute(text('ALTER TABLE applicant ALTER COLUMN resume DROP NOT NULL'))
            db.session.commit()

        employee_id_col = applicant_cols_by_name.get('employee_id')
        if employee_id_col and not employee_id_col.get('nullable', True):
            db.session.execute(text('ALTER TABLE applicant ALTER COLUMN employee_id DROP NOT NULL'))
            db.session.commit()
    except Exception as e:
        print(f"Warning: Could not ensure database schema: {e}")


def create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home'):
    """
    Create and configure the Flask application.
    
    Args:
        enable_applicant: Enable applicant-related routes
        enable_employee: Enable employee/internal routes
        root_redirect: Where to redirect root path
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    
    with app.app_context():
        # Ensure database schema
        ensure_db_schema()
        
        # Create all tables
        db.create_all()
        
        # RBAC: Seed roles and permissions (idempotent)
        try:
            seed_roles_and_permissions()
            print("✓ RBAC: Roles and permissions initialized")
        except Exception as e:
            print(f"⚠ RBAC: Could not seed roles/permissions: {e}")
        
        # RBAC: Initialize middleware
        init_rbac_middleware(app)
        print("✓ RBAC: Middleware initialized")
    
    # Register routes
    if enable_applicant:
        from routes_applicant import register_applicant_routes
        register_applicant_routes(app)
        print("✓ Applicant routes registered")
    
    if enable_employee:
        from routes_employee import register_employee_routes
        register_employee_routes(app)
        print("✓ Employee routes registered")
        
        # RBAC: Register authentication routes
        from routes_auth import register_auth_routes
        register_auth_routes(app)
        print("✓ RBAC: Auth routes registered")
        
        # RBAC: Register RBAC management routes
        from routes_rbac import register_rbac_routes
        register_rbac_routes(app)
        print("✓ RBAC: Management routes registered")
        
        # RBAC: Admin panel route
        from flask_login import login_required
        from rbac_middleware import require_role_check
        
        @app.route('/admin/panel')
        @login_required
        @require_role_check('SUPER_ADMIN')
        def admin_panel():
            """SUPER_ADMIN only: User and permission management panel"""
            from flask import render_template
            return render_template('admin_panel.html')
        
        print("✓ RBAC: Admin panel route registered")
    
    # Root route
    @app.route('/')
    def root():
        """Redirect root path to configured destination"""
        if root_redirect == 'applicant_home':
            return redirect(url_for('applicant_home'))
        elif root_redirect == 'employee_home':
            return redirect(url_for('employee_home'))
        elif root_redirect == 'dashboard':
            return redirect(url_for('dashboard'))
        return redirect(url_for('applicant_home'))
    
    return app

from flask import Flask, flash, jsonify, redirect, request, url_for
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from sqlalchemy import inspect, text

from config import Config
from models import db, Employee, Position
from rbac_middleware import init_rbac_middleware
from auth_rbac import seed_roles_and_permissions


login_manager = LoginManager()
login_manager.login_view = 'employee_login'
login_manager.login_message = 'Employee login required for dashboard.'
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    return Employee.query.get(int(user_id))


def ensure_db_schema():
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
            # RBAC columns
            if 'role_id' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN role_id INTEGER'))
                db.session.commit()
            if 'force_password_reset' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN force_password_reset BOOLEAN DEFAULT 0'))
                db.session.commit()
            if 'last_login' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN last_login DATETIME'))
                db.session.commit()
            if 'session_started_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN session_started_at DATETIME'))
                db.session.commit()
            if 'last_seen_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN last_seen_at DATETIME'))
                db.session.commit()
            if 'force_logout_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN force_logout_at DATETIME'))
                db.session.commit()
            if 'email_verified' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN email_verified BOOLEAN DEFAULT TRUE NOT NULL'))
                db.session.commit()
            if 'email_verified_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN email_verified_at DATETIME'))
                db.session.commit()
            if 'email_verification_sent_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN email_verification_sent_at DATETIME'))
                db.session.commit()
            if 'is_active' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN is_active BOOLEAN DEFAULT 1'))
                db.session.commit()
            if 'created_by_id' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN created_by_id INTEGER'))
                db.session.commit()
            if 'is_deleted' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN is_deleted BOOLEAN DEFAULT 0'))
                db.session.commit()
            if 'deleted_at' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN deleted_at DATETIME'))
                db.session.commit()
            if 'deleted_by_id' not in employee_cols:
                db.session.execute(text('ALTER TABLE employee ADD COLUMN deleted_by_id INTEGER'))
                db.session.commit()

        if 'applicant' not in tables:
            return

        if 'announcement' in tables:
            announcement_cols = {c['name'] for c in inspector.get_columns('announcement')}
            if 'recipient_employee_id' not in announcement_cols:
                db.session.execute(text('ALTER TABLE announcement ADD COLUMN recipient_employee_id INTEGER'))
                db.session.commit()

        cols = {c['name'] for c in inspector.get_columns('applicant')}
        if 'gender' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN gender VARCHAR(10)'))
            db.session.commit()
        middle_initial_col = next((c for c in inspector.get_columns('applicant') if c['name'] == 'middle_initial'), None)
        middle_initial_len = getattr(middle_initial_col.get('type'), 'length', None) if middle_initial_col else None
        if middle_initial_len is not None and db.engine.dialect.name != 'sqlite':
            db.session.execute(text('ALTER TABLE applicant ALTER COLUMN middle_initial TYPE TEXT'))
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
        if 'remarked_by_id' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN remarked_by_id INTEGER'))
            db.session.commit()
        if 'remarked_at' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN remarked_at DATETIME'))
            db.session.commit()
        if 'is_deleted' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN is_deleted BOOLEAN DEFAULT 0'))
            db.session.commit()
        if 'deleted_at' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN deleted_at DATETIME'))
            db.session.commit()
        if 'deleted_by_id' not in cols:
            db.session.execute(text('ALTER TABLE applicant ADD COLUMN deleted_by_id INTEGER'))
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

        # Position table migration
        if 'position' not in tables:
            db.session.execute(text('''
                CREATE TABLE position (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER,
                    assigned_employee_id INTEGER,
                    FOREIGN KEY (created_by_id) REFERENCES employee(id),
                    FOREIGN KEY (assigned_employee_id) REFERENCES employee(id)
                )
            '''))
            # Create index
            db.session.execute(text('CREATE INDEX idx_position_title ON position(title)'))
            db.session.execute(text('CREATE INDEX idx_position_is_active ON position(is_active)'))
            db.session.execute(text('CREATE INDEX idx_position_assigned_employee_id ON position(assigned_employee_id)'))
            db.session.commit()
        else:
            # Check if position table needs columns
            position_cols = {c['name'] for c in inspector.get_columns('position')}
            if 'is_active' not in position_cols:
                db.session.execute(text('ALTER TABLE position ADD COLUMN is_active BOOLEAN DEFAULT 1'))
                db.session.commit()
            if 'updated_at' not in position_cols:
                db.session.execute(text('ALTER TABLE position ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP'))
                db.session.commit()
            if 'created_by_id' not in position_cols:
                db.session.execute(text('ALTER TABLE position ADD COLUMN created_by_id INTEGER'))
                db.session.commit()
            if 'assigned_employee_id' not in position_cols:
                db.session.execute(text('ALTER TABLE position ADD COLUMN assigned_employee_id INTEGER'))
                db.session.commit()

        if 'position' in tables and 'employee' in tables:
            default_owner = Employee.query.filter(Employee.role_obj.has(name='SUPER_ADMIN'), Employee.is_active == True).first()
            if not default_owner:
                default_owner = Employee.query.filter_by(is_active=True).first()
            if default_owner:
                db.session.execute(
                    text('UPDATE position SET assigned_employee_id = :employee_id WHERE assigned_employee_id IS NULL'),
                    {'employee_id': default_owner.id}
                )
                db.session.commit()

        tables = set(inspector.get_table_names())
        if 'position_assignment' not in tables:
            db.session.execute(text('''
                CREATE TABLE position_assignment (
                    position_id INTEGER NOT NULL,
                    employee_id INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (position_id, employee_id),
                    FOREIGN KEY (position_id) REFERENCES position(id),
                    FOREIGN KEY (employee_id) REFERENCES employee(id)
                )
            '''))
            db.session.commit()

        if 'position' in tables and 'employee' in tables and 'position_assignment' in set(inspector.get_table_names()):
            changed_assignments = False
            for position in Position.query.filter(Position.assigned_employee_id.isnot(None)).all():
                assigned_ids = {employee.id for employee in position.assigned_employees}
                if position.assigned_employee_id not in assigned_ids and position.assigned_employee:
                    position.assigned_employees.append(position.assigned_employee)
                    changed_assignments = True
            if changed_assignments:
                db.session.commit()
    except Exception as e:
        print(f'Warning: could not ensure DB schema: {e}')


def create_app(*, enable_applicant: bool, enable_employee: bool, root_redirect: str | None = None):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    if root_redirect:
        @app.route('/')
        def root():
            return redirect(url_for(root_redirect))

    with app.app_context():
        db.create_all()
        ensure_db_schema()

    if enable_applicant:
        from routes_applicant import register_applicant_routes
        register_applicant_routes(app)

    if enable_employee:
        from routes_employee import register_employee_routes
        register_employee_routes(app)

        from routes_auth import register_auth_routes
        register_auth_routes(app)

        from routes_rbac import register_rbac_routes
        register_rbac_routes(app)

        from routes_positions import register_positions_routes
        register_positions_routes(app)

    init_rbac_middleware(app)

    @app.context_processor
    def inject_rbac_helpers():
        from auth_rbac import has_permission
        return dict(has_permission=has_permission, csrf_token=generate_csrf)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'CSRF validation failed'}), 400
        flash('Security token expired or missing. Please try again.', 'error')
        return redirect(request.referrer or url_for(root_redirect or 'employee_login'))

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Uploaded file is too large. Maximum size is 5MB.'}), 413
        return 'Uploaded file is too large. Maximum size is 5MB.', 413

    @app.errorhandler(HTTPException)
    def handle_api_http_exception(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': error.description or error.name}), error.code
        return error

    with app.app_context():
        seed_roles_and_permissions()

    return app

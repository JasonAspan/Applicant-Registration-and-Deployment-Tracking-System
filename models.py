from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from time_utils import ph_now

db = SQLAlchemy()


# ==================== RBAC Models ====================

class Role(db.Model):
    """User roles: SUPER_ADMIN, ADMIN, LEVEL_2_USER, LEVEL_1_USER"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=ph_now)

    employees = db.relationship('Employee', backref='role_obj', lazy='dynamic')
    permissions = db.relationship('Permission', secondary='role_permission', backref='roles', lazy='dynamic')

    def __repr__(self):
        return f'<Role {self.name}>'


class Permission(db.Model):
    """Fine-grained permissions"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)  # e.g., 'manage_positions', 'view_applicants'
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., 'applicants', 'positions', 'users'
    created_at = db.Column(db.DateTime, default=ph_now)

    def __repr__(self):
        return f'<Permission {self.key}>'


role_permission = db.Table(
    'role_permission',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)


position_assignment = db.Table(
    'position_assignment',
    db.Column('position_id', db.Integer, db.ForeignKey('position.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employee.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=ph_now)
)


class UserPermission(db.Model):
    """Override permissions per user (SUPER_ADMIN can grant/deny any permission)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'), nullable=False, index=True)
    is_allowed = db.Column(db.Boolean, nullable=False, default=True)  # True=allow, False=deny
    reason = db.Column(db.String(255))  # Why this override
    created_at = db.Column(db.DateTime, default=ph_now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'))  # Who made the override

    user = db.relationship('Employee', foreign_keys=[user_id], backref='permission_overrides')
    permission = db.relationship('Permission', backref='user_overrides')
    created_by = db.relationship('Employee', foreign_keys=[created_by_id])

    db.UniqueConstraint('user_id', 'permission_id', name='uq_user_permission')

    def __repr__(self):
        return f'<UserPermission user_id={self.user_id}, permission={self.permission.key}, allowed={self.is_allowed}>'


# ==================== Employee Model ====================

class Employee(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_filename = db.Column(db.String(255))
    profile_content_type = db.Column(db.String(100))
    profile_data = db.Column(db.LargeBinary)
    
    # RBAC fields
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True, index=True)
    force_password_reset = db.Column(db.Boolean, default=False)  # Force reset on first login
    last_login = db.Column(db.DateTime)
    session_started_at = db.Column(db.DateTime)
    last_seen_at = db.Column(db.DateTime)
    force_logout_at = db.Column(db.DateTime)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verified_at = db.Column(db.DateTime)
    email_verification_sent_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=ph_now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)

    applicants = db.relationship('Applicant', backref='employee', lazy='dynamic', foreign_keys='Applicant.employee_id')
    created_by = db.relationship('Employee', remote_side=[id], backref='created_employees', foreign_keys=[created_by_id])
    deleted_by = db.relationship('Employee', remote_side=[id], foreign_keys=[deleted_by_id])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Employee {self.username}>'

class Applicant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_initial = db.Column(db.Text)
    suffix = db.Column(db.String(20))
    age = db.Column(db.Integer)
    birth_date = db.Column(db.DateTime)
    gender = db.Column(db.String(10), nullable=True)
    contact_number = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    job_position = db.Column(db.String(50), nullable=False)
    resume = db.Column(db.Text, nullable=True)
    password_hash = db.Column(db.String(255))
    cv_filename = db.Column(db.String(255))
    cv_content_type = db.Column(db.String(100))
    cv_data = db.Column(db.LargeBinary)
    status = db.Column(db.String(20), default='pending')
    applied_at = db.Column(db.DateTime, default=ph_now)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    remarked_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True, index=True)
    remarked_at = db.Column(db.DateTime)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    deleted_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)

    remarked_by = db.relationship('Employee', foreign_keys=[remarked_by_id], backref='remarked_applicants')
    deleted_by = db.relationship('Employee', foreign_keys=[deleted_by_id])

    # password_hash is currently unused (applicants do not log in)

    @property
    def full_name(self):
        name_parts = [self.first_name, self.middle_initial, self.last_name]
        if self.suffix:
            name_parts.append(self.suffix)
        return ' '.join([p for p in name_parts if p])

    def __repr__(self):
        return f'<Applicant {self.full_name or self.first_name}>'


class ProfileTodo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    text = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=ph_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=ph_now, onupdate=ph_now, nullable=False)

    employee = db.relationship('Employee', backref=db.backref('profile_todos', lazy='dynamic'))

    def __repr__(self):
        return f'<ProfileTodo employee_id={self.employee_id} text={self.text[:24]!r}>'


class ApplicantDashboardDeletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    deleted_at = db.Column(db.DateTime, default=ph_now, nullable=False)

    applicant = db.relationship('Applicant', backref=db.backref('dashboard_deletions', lazy='dynamic'))
    employee = db.relationship('Employee', backref=db.backref('dashboard_deletions', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('applicant_id', 'employee_id', name='uq_applicant_dashboard_deletion'),
    )

    def __repr__(self):
        return f'<ApplicantDashboardDeletion applicant_id={self.applicant_id} employee_id={self.employee_id}>'


class ApplicantForward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicant.id'), nullable=False, index=True)
    from_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    to_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    forwarded_at = db.Column(db.DateTime, default=ph_now, nullable=False)

    applicant = db.relationship('Applicant', backref=db.backref('forwards', lazy='dynamic'))
    from_employee = db.relationship('Employee', foreign_keys=[from_employee_id], backref=db.backref('sent_applicant_forwards', lazy='dynamic'))
    to_employee = db.relationship('Employee', foreign_keys=[to_employee_id], backref=db.backref('received_applicant_forwards', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('applicant_id', 'to_employee_id', name='uq_applicant_forward_recipient'),
    )

    def __repr__(self):
        return f'<ApplicantForward applicant_id={self.applicant_id} to_employee_id={self.to_employee_id}>'


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=ph_now, nullable=False, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True, index=True)
    recipient_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True, index=True)

    created_by = db.relationship('Employee', foreign_keys=[created_by_id], backref=db.backref('announcements_created', lazy='dynamic'))
    recipient_employee = db.relationship('Employee', foreign_keys=[recipient_employee_id], backref=db.backref('notifications_received', lazy='dynamic'))

    def __repr__(self):
        return f'<Announcement {self.title}>'


class AnnouncementRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcement.id'), nullable=False, index=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False, index=True)
    read_at = db.Column(db.DateTime, default=ph_now, nullable=False)

    announcement = db.relationship('Announcement', backref=db.backref('read_receipts', lazy='dynamic'))
    employee = db.relationship('Employee', backref=db.backref('announcement_reads', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('announcement_id', 'employee_id', name='uq_announcement_read_employee'),
    )

    def __repr__(self):
        return f'<AnnouncementRead announcement_id={self.announcement_id} employee_id={self.employee_id}>'


# ==================== Position Model ====================

class Position(db.Model):
    """Applicant job positions - managed by SUPERADMIN"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=ph_now)
    updated_at = db.Column(db.DateTime, default=ph_now, onupdate=ph_now)
    created_by_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    assigned_employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True, index=True)

    created_by = db.relationship('Employee', backref='positions_created', foreign_keys=[created_by_id])
    assigned_employee = db.relationship('Employee', backref='primary_assigned_positions', foreign_keys=[assigned_employee_id])
    assigned_employees = db.relationship(
        'Employee',
        secondary=position_assignment,
        backref=db.backref('assigned_positions', lazy='dynamic'),
        lazy='select'
    )

    def __repr__(self):
        return f'<Position {self.title}>'

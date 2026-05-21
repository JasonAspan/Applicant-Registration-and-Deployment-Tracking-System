from datetime import date, datetime

from flask import flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models import Applicant, Employee, Position, db
from routes_employee import APPLICANT_OPEN_STATUS

MAX_CV_BYTES = 5 * 1024 * 1024

ALLOWED_CV_TYPES = {
    '.pdf': {
        'content_type': 'application/pdf',
        'validator': lambda data: data.startswith(b'%PDF')
    },
    '.doc': {
        'content_type': 'application/msword',
        'validator': lambda data: data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    },
    '.docx': {
        'content_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'validator': lambda data: data.startswith(b'PK\x03\x04')
    }
}


def normalize_identity_text(value):
    return ' '.join((value or '').strip().lower().split())


def normalize_contact_number(value):
    return ''.join(char for char in str(value or '') if char.isdigit())


def normalize_birth_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def is_same_applicant_identity(applicant, first_name, last_name, middle_initial, suffix, contact_number, birth_date):
    return (
        normalize_identity_text(applicant.first_name) == normalize_identity_text(first_name)
        and normalize_identity_text(applicant.last_name) == normalize_identity_text(last_name)
        and normalize_identity_text(applicant.middle_initial) == normalize_identity_text(middle_initial)
        and normalize_identity_text(applicant.suffix) == normalize_identity_text(suffix)
        and normalize_contact_number(applicant.contact_number) == normalize_contact_number(contact_number)
        and normalize_birth_date(applicant.birth_date) == normalize_birth_date(birth_date)
    )


def duplicate_application_exists(first_name, last_name, middle_initial, suffix, contact_number, birth_date):
    candidates = Applicant.query.filter(
        Applicant.is_deleted == False,
        db.func.lower(db.func.trim(Applicant.first_name)) == normalize_identity_text(first_name),
        db.func.lower(db.func.trim(Applicant.last_name)) == normalize_identity_text(last_name),
    ).all()
    return any(
        is_same_applicant_identity(
            applicant,
            first_name,
            last_name,
            middle_initial,
            suffix,
            contact_number,
            birth_date,
        )
        for applicant in candidates
    )


def register_applicant_routes(app):
    def active_position_recipients(position):
        recipients = [employee for employee in position.assigned_employees if employee.is_active and not employee.is_deleted]
        if position.assigned_employee and position.assigned_employee.is_active and not position.assigned_employee.is_deleted and position.assigned_employee not in recipients:
            recipients.append(position.assigned_employee)
        if recipients:
            return recipients

        fallback = Employee.query.filter(
            Employee.is_active == True,
            Employee.is_deleted == False,
            Employee.role_obj.has(name='LEVEL_1_USER') | Employee.role_obj.has(name='LEVEL_2_USER')
        ).order_by(Employee.id.asc()).first()
        if fallback:
            return [fallback]

        fallback = Employee.query.filter_by(is_active=True, is_deleted=False).order_by(Employee.id.asc()).first()
        return [fallback] if fallback else []

    @app.route('/applicant')
    @app.route('/applicant/')
    def applicant_home():
        return redirect(url_for('applicant_register'))

    @app.route('/applicant-register.html', methods=['GET', 'POST'])
    def applicant_register():
        if request.method == 'POST':
            first_name = request.form['first_name'].strip()
            last_name = request.form['last_name'].strip()
            middle_initial = request.form.get('middle_initial', '').strip()
            suffix = request.form.get('suffix', '').strip()
            age = int(request.form['age'])
            birth_date_str = request.form['birth_date']
            birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
            gender = request.form['gender']
            contact_number = normalize_contact_number(request.form['contact_number'])
            email = request.form['email'].strip()
            job_position = request.form['job_position'].strip()
            position = Position.query.filter_by(title=job_position, is_active=True).first()
            assigned_employees = active_position_recipients(position) if position else []
            if not position or not assigned_employees:
                flash('Please select an available position.', 'error')
                return render_template('applicant_register.html')

            if duplicate_application_exists(first_name, last_name, middle_initial, suffix, contact_number, birth_date):
                flash('An application already exists for this applicant name, contact number, and birth date.', 'error')
                return render_template('applicant_register.html')

            filename = None
            cv_content_type = None
            cv_bytes = None
            cv_file = request.files.get('cv')
            if cv_file and cv_file.filename:
                filename = secure_filename(cv_file.filename)
                extension = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                cv_type = ALLOWED_CV_TYPES.get(extension)
                if not cv_type:
                    flash('CV must be a PDF, DOC, or DOCX file.', 'error')
                    return render_template('applicant_register.html')

                cv_bytes = cv_file.read()
                if len(cv_bytes) > MAX_CV_BYTES:
                    flash('CV must be 5MB or smaller.', 'error')
                    return render_template('applicant_register.html')

                if not cv_type['validator'](cv_bytes):
                    flash('Invalid CV file format.', 'error')
                    return render_template('applicant_register.html')

                cv_content_type = cv_type['content_type']

            applicant = Applicant(
                first_name=first_name,
                last_name=last_name,
                middle_initial=middle_initial,
                suffix=suffix,
                age=age,
                birth_date=birth_date,
                gender=gender,
                contact_number=contact_number,
                email=email,
                job_position=job_position,
                resume=None,
                cv_filename=filename,
                cv_content_type=cv_content_type,
                cv_data=cv_bytes,
                status=APPLICANT_OPEN_STATUS,
                employee_id=assigned_employees[0].id
            )
            db.session.add(applicant)
            db.session.commit()
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('applicant_home'))

        return render_template('applicant_register.html')

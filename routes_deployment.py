from datetime import datetime
from io import BytesIO

from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from models import Applicant, ApplicantDocument, Employee, db
from auth_rbac import has_permission
from time_utils import ph_now

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024

ALLOWED_DOCUMENT_TYPES = {
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
    },
    '.jpg': {
        'content_type': 'image/jpeg',
        'validator': lambda data: data.startswith(b'\xff\xd8\xff')
    },
    '.jpeg': {
        'content_type': 'image/jpeg',
        'validator': lambda data: data.startswith(b'\xff\xd8\xff')
    },
    '.png': {
        'content_type': 'image/png',
        'validator': lambda data: data.startswith(b'\x89PNG\r\n\x1a\n')
    },
}

DEPLOYMENT_STATUSES = ('Deployed', 'Change Employer', 'Repatriated', 'Finished Contract', 'Renewal of Contract')


def register_deployment_routes(app):
    """Register deployment-tracking routes for the Deployed Applicants page."""

    def parse_date(value):
        value = (value or '').strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            return None

    def contract_state(applicant):
        if not applicant.contract_end_date:
            return 'none'
        return 'ended' if applicant.contract_end_date < ph_now().date() else 'active'

    def validate_document_file(file_storage):
        filename = secure_filename(file_storage.filename or '')
        extension = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        doc_type = ALLOWED_DOCUMENT_TYPES.get(extension)
        if not doc_type:
            return None, None, None, f'{file_storage.filename}: unsupported file type.'

        data = file_storage.read()
        if not data:
            return None, None, None, f'{file_storage.filename}: file is empty.'
        if len(data) > MAX_DOCUMENT_BYTES:
            return None, None, None, f'{file_storage.filename}: exceeds the 5MB size limit.'
        if not doc_type['validator'](data):
            return None, None, None, f'{file_storage.filename}: file content does not match its extension.'

        return filename, doc_type['content_type'], data, None

    def get_deployed_applicant_or_404(applicant_id):
        return Applicant.query.filter_by(id=applicant_id, status='Deployed', is_deleted=False).first_or_404()

    @app.route('/deployed-applicants.html')
    @login_required
    def deployed_applicants():
        if not has_permission(current_user, 'view_deployed_applicants'):
            flash('You do not have permission to view deployed applicants.', 'error')
            return redirect(url_for('employee_home'))

        filters = {
            'q': (request.args.get('q') or '').strip(),
            'employer': (request.args.get('employer') or '').strip(),
            'job_position': (request.args.get('job_position') or '').strip(),
            'status': (request.args.get('status') or '').strip(),
            'recruiter_id': (request.args.get('recruiter_id') or '').strip(),
            'date_from': (request.args.get('date_from') or '').strip(),
            'date_to': (request.args.get('date_to') or '').strip(),
        }

        query = Applicant.query.filter_by(status='Deployed', is_deleted=False)

        if filters['q']:
            like = f"%{filters['q']}%"
            query = query.filter(or_(
                Applicant.first_name.ilike(like),
                Applicant.last_name.ilike(like),
                Applicant.middle_initial.ilike(like),
                Applicant.contact_number.ilike(like),
                Applicant.email.ilike(like),
            ))
        if filters['employer']:
            query = query.filter(Applicant.employer_name.ilike(f"%{filters['employer']}%"))
        if filters['job_position']:
            query = query.filter(Applicant.job_position == filters['job_position'])
        if filters['status']:
            if filters['status'] == 'Deployed':
                query = query.filter(or_(Applicant.deployment_status == 'Deployed', Applicant.deployment_status.is_(None)))
            else:
                query = query.filter(Applicant.deployment_status == filters['status'])
        if filters['recruiter_id']:
            query = query.filter(Applicant.deployed_by_id == filters['recruiter_id'])
        date_from = parse_date(filters['date_from'])
        if date_from:
            query = query.filter(Applicant.deployed_at >= datetime.combine(date_from, datetime.min.time()))
        date_to = parse_date(filters['date_to'])
        if date_to:
            query = query.filter(Applicant.deployed_at <= datetime.combine(date_to, datetime.max.time()))

        applicants = query.order_by(Applicant.deployed_at.desc()).all()
        rows = [(applicant, contract_state(applicant)) for applicant in applicants]
        can_manage = has_permission(current_user, 'manage_deployed_applicants')

        job_positions = [
            r[0] for r in Applicant.query
            .filter_by(status='Deployed', is_deleted=False)
            .with_entities(Applicant.job_position)
            .distinct()
            .order_by(Applicant.job_position.asc())
            .all()
            if r[0]
        ]
        recruiters = (
            Employee.query
            .join(Applicant, Applicant.deployed_by_id == Employee.id)
            .filter(Applicant.status == 'Deployed', Applicant.is_deleted == False)
            .distinct()
            .order_by(Employee.username.asc())
            .all()
        )

        return render_template(
            'deployed_applicants.html',
            rows=rows,
            can_manage=can_manage,
            deployment_statuses=DEPLOYMENT_STATUSES,
            filters=filters,
            job_positions=job_positions,
            recruiters=recruiters,
            can_view_recruitment_dashboard=has_permission(current_user, 'view_applicants'),
        )

    @app.route('/deployed-applicants/<int:applicant_id>/update', methods=['POST'])
    @login_required
    def update_deployment_details(applicant_id):
        if not has_permission(current_user, 'manage_deployed_applicants'):
            flash('You do not have permission to manage deployed applicants.', 'error')
            return redirect(url_for('deployed_applicants'))

        applicant = get_deployed_applicant_or_404(applicant_id)

        deployment_status = (request.form.get('deployment_status') or '').strip()
        if deployment_status and deployment_status not in DEPLOYMENT_STATUSES:
            flash('Select a valid deployment status.', 'error')
            return redirect(request.referrer or url_for('deployed_applicants'))

        applicant.employer_name = (request.form.get('employer_name') or '').strip() or None
        applicant.deployment_country = (request.form.get('deployment_country') or '').strip() or None
        applicant.contract_start_date = parse_date(request.form.get('contract_start_date'))
        applicant.contract_end_date = parse_date(request.form.get('contract_end_date'))
        applicant.deployment_status = deployment_status or None
        applicant.deployment_remarks = (request.form.get('deployment_remarks') or '').strip() or None
        applicant.deployment_updated_at = ph_now()

        db.session.commit()
        flash('Deployment details updated.', 'success')
        return redirect(request.referrer or url_for('deployed_applicants'))

    @app.route('/deployed-applicants/<int:applicant_id>/documents')
    @login_required
    def deployment_documents(applicant_id):
        if not has_permission(current_user, 'view_deployed_applicants'):
            flash('You do not have permission to view deployed applicants.', 'error')
            return redirect(url_for('employee_home'))

        applicant = get_deployed_applicant_or_404(applicant_id)
        documents = applicant.documents.all()
        can_manage = has_permission(current_user, 'manage_deployed_applicants')

        return render_template(
            'deployment_documents.html',
            applicant=applicant,
            documents=documents,
            can_manage=can_manage,
        )

    @app.route('/deployed-applicants/<int:applicant_id>/documents/upload', methods=['POST'])
    @login_required
    def upload_deployment_document(applicant_id):
        if not has_permission(current_user, 'manage_deployed_applicants'):
            flash('You do not have permission to upload documents.', 'error')
            return redirect(url_for('deployed_applicants'))

        applicant = get_deployed_applicant_or_404(applicant_id)
        files = [f for f in request.files.getlist('documents') if f and f.filename]

        if not files:
            flash('Choose at least one file to upload.', 'error')
            return redirect(url_for('deployment_documents', applicant_id=applicant_id))

        uploaded_count = 0
        errors = []
        for file_storage in files:
            filename, content_type, data, error = validate_document_file(file_storage)
            if error:
                errors.append(error)
                continue
            db.session.add(ApplicantDocument(
                applicant_id=applicant.id,
                label=(request.form.get('label') or '').strip() or filename,
                filename=filename,
                content_type=content_type,
                data=data,
                uploaded_by_id=current_user.id,
                uploaded_at=ph_now(),
            ))
            uploaded_count += 1

        if uploaded_count:
            db.session.commit()
            flash(f'Uploaded {uploaded_count} document(s).', 'success')
        if errors:
            flash('Some files were rejected: ' + ' '.join(errors), 'error')

        return redirect(url_for('deployment_documents', applicant_id=applicant_id))

    @app.route('/deployed-applicants/<int:applicant_id>/documents/<int:document_id>/download')
    @login_required
    def download_deployment_document(applicant_id, document_id):
        if not has_permission(current_user, 'view_deployed_applicants'):
            flash('You do not have permission to view deployed applicants.', 'error')
            return redirect(url_for('employee_home'))

        document = ApplicantDocument.query.filter_by(id=document_id, applicant_id=applicant_id).first_or_404()
        return send_file(
            BytesIO(document.data),
            mimetype=document.content_type or 'application/octet-stream',
            as_attachment=True,
            download_name=document.filename,
        )

    @app.route('/deployed-applicants/<int:applicant_id>/documents/<int:document_id>/edit', methods=['POST'])
    @login_required
    def edit_deployment_document(applicant_id, document_id):
        if not has_permission(current_user, 'manage_deployed_applicants'):
            flash('You do not have permission to edit documents.', 'error')
            return redirect(url_for('deployed_applicants'))

        document = ApplicantDocument.query.filter_by(id=document_id, applicant_id=applicant_id).first_or_404()

        label = (request.form.get('label') or '').strip()
        if label:
            document.label = label

        replacement = request.files.get('replacement')
        if replacement and replacement.filename:
            filename, content_type, data, error = validate_document_file(replacement)
            if error:
                flash(error, 'error')
                return redirect(url_for('deployment_documents', applicant_id=applicant_id))
            document.filename = filename
            document.content_type = content_type
            document.data = data
            document.uploaded_by_id = current_user.id
            document.uploaded_at = ph_now()

        db.session.commit()
        flash('Document updated.', 'success')
        return redirect(url_for('deployment_documents', applicant_id=applicant_id))

    @app.route('/deployed-applicants/<int:applicant_id>/documents/<int:document_id>/delete', methods=['POST'])
    @login_required
    def delete_deployment_document(applicant_id, document_id):
        if not has_permission(current_user, 'manage_deployed_applicants'):
            flash('You do not have permission to delete documents.', 'error')
            return redirect(url_for('deployed_applicants'))

        document = ApplicantDocument.query.filter_by(id=document_id, applicant_id=applicant_id).first_or_404()
        db.session.delete(document)
        db.session.commit()
        flash('Document deleted.', 'success')
        return redirect(url_for('deployment_documents', applicant_id=applicant_id))

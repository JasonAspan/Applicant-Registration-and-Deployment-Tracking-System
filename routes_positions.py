from flask import jsonify, request
from functools import wraps
from flask_login import current_user, login_required
from models import Applicant, Employee, Position, db
from auth_rbac import has_permission


def require_manage_positions(f):
    """Decorator: only users with manage_positions can change positions."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        if not current_user.is_authenticated:
            return jsonify({'error': 'Unauthorized'}), 401
        if not has_permission(current_user, 'manage_positions'):
            return jsonify({'error': 'Missing permission: manage_positions'}), 403
        return f(*args, **kwargs)
    return decorated_function


def register_positions_routes(app):
    """Register position management routes"""

    def applicant_selectable_positions_query():
        return Position.query.filter(Position.is_active == True).order_by(Position.title.asc())

    def serialize_position(position):
        assigned_users = sorted(position.assigned_employees, key=lambda user: user.username.lower())
        assigned_user = assigned_users[0] if assigned_users else position.assigned_employee
        return {
            'id': position.id,
            'title': position.title,
            'is_active': position.is_active,
            'assigned_employee_id': assigned_user.id if assigned_user else position.assigned_employee_id,
            'assigned_employee_ids': [user.id for user in assigned_users],
            'assigned_employee': {
                'id': assigned_user.id,
                'username': assigned_user.username,
                'email': assigned_user.email
            } if assigned_user else None,
            'assigned_employees': [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
                for user in assigned_users
            ],
            'created_at': position.created_at.isoformat() if position.created_at else None,
            'updated_at': position.updated_at.isoformat() if position.updated_at else None
        }

    def get_valid_assigned_employees(data):
        assigned_employee_ids = data.get('assigned_employee_ids')
        if assigned_employee_ids is None:
            assigned_employee_ids = data.get('assigned_employee_id')

        if not isinstance(assigned_employee_ids, list):
            assigned_employee_ids = [assigned_employee_ids]

        cleaned_ids = []
        for employee_id in assigned_employee_ids:
            try:
                employee_id = int(employee_id)
            except (TypeError, ValueError):
                continue
            if employee_id not in cleaned_ids:
                cleaned_ids.append(employee_id)

        if not cleaned_ids:
            return [], None, None

        employees = Employee.query.filter(
            Employee.id.in_(cleaned_ids),
            Employee.is_active == True,
            Employee.is_deleted == False,
            Employee.role_obj.has(name='LEVEL_1_USER') | Employee.role_obj.has(name='LEVEL_2_USER')
        ).all()

        if len(employees) != len(cleaned_ids):
            return [], jsonify({'success': False, 'message': 'Assigned users must be active LEVEL_1_USER or LEVEL_2_USER accounts'}), 400

        employees_by_id = {employee.id: employee for employee in employees}
        return [employees_by_id[employee_id] for employee_id in cleaned_ids], None, None

    def default_assigned_employees():
        if current_user.is_authenticated and current_user.is_active:
            return [current_user]
        return []

    @app.route('/api/positions', methods=['GET'])
    def get_positions():
        """Get active positions that applicants can select."""
        try:
            positions = applicant_selectable_positions_query().all()
            return jsonify([serialize_position(p) for p in positions])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/positions/all', methods=['GET'])
    @login_required
    def get_all_positions():
        """Get all positions including inactive (admin only)"""
        try:
            from flask_login import current_user
            if not has_permission(current_user, 'view_positions') and not has_permission(current_user, 'manage_positions'):
                return jsonify({'error': 'Missing permission: view_positions'}), 403

            positions = Position.query.order_by(Position.title.asc()).all()
            return jsonify([serialize_position(p) for p in positions])
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/positions', methods=['POST'])
    @require_manage_positions
    def create_position():
        """Create a new position."""
        try:
            from flask_login import current_user
            data = request.get_json() or {}

            title = (data.get('title') or '').strip()
            is_active = data.get('is_active', True)
            assigned_employees, error_response, status_code = get_valid_assigned_employees(data)
            if error_response:
                return error_response, status_code
            if not assigned_employees:
                assigned_employees = default_assigned_employees()

            if not title:
                return jsonify({'success': False, 'message': 'Title is required'}), 400

            # Check for duplicate
            existing = Position.query.filter_by(title=title).first()
            if existing:
                return jsonify({'success': False, 'message': f'Position "{title}" already exists'}), 400

            position = Position(
                title=title,
                is_active=is_active,
                assigned_employee_id=assigned_employees[0].id if assigned_employees else None,
                created_by_id=current_user.id
            )
            position.assigned_employees = assigned_employees
            db.session.add(position)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Position "{title}" created',
                'position': {
                    'id': position.id,
                    'title': position.title,
                    'is_active': position.is_active,
                    'assigned_employee_id': position.assigned_employee_id,
                    'assigned_employee_ids': [employee.id for employee in assigned_employees]
                }
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/positions/<int:position_id>', methods=['GET'])
    def get_position(position_id):
        """Get a specific position"""
        try:
            position = Position.query.get_or_404(position_id)
            serialized = serialize_position(position)
            return jsonify({
                'id': position.id,
                'title': position.title,
                'is_active': position.is_active,
                'assigned_employee_id': serialized['assigned_employee_id'],
                'assigned_employee_ids': serialized['assigned_employee_ids'],
                'assigned_employee': serialized['assigned_employee'],
                'assigned_employees': serialized['assigned_employees'],
                'created_at': position.created_at.isoformat() if position.created_at else None,
                'updated_at': position.updated_at.isoformat() if position.updated_at else None
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 404

    @app.route('/api/positions/<int:position_id>', methods=['PUT'])
    @require_manage_positions
    def update_position(position_id):
        """Update a position."""
        try:
            position = Position.query.get_or_404(position_id)
            data = request.get_json() or {}
            original_title = position.title
            new_assigned_employees = None

            if 'title' in data:
                new_title = (data.get('title') or '').strip()
                if not new_title:
                    return jsonify({'success': False, 'message': 'Title cannot be empty'}), 400

                # Check for duplicate (excluding current position)
                existing = Position.query.filter(
                    Position.title == new_title,
                    Position.id != position_id
                ).first()
                if existing:
                    return jsonify({'success': False, 'message': f'Position "{new_title}" already exists'}), 400

                position.title = new_title

            if 'is_active' in data:
                position.is_active = data.get('is_active', True)

            if 'assigned_employee_id' in data or 'assigned_employee_ids' in data:
                assigned_employees, error_response, status_code = get_valid_assigned_employees(data)
                if error_response:
                    return error_response, status_code
                position.assigned_employee_id = assigned_employees[0].id if assigned_employees else None
                position.assigned_employees = assigned_employees
                new_assigned_employees = assigned_employees

            if position.title != original_title:
                Applicant.query.filter_by(job_position=original_title).update(
                    {'job_position': position.title},
                    synchronize_session=False
                )

            if new_assigned_employees:
                Applicant.query.filter_by(job_position=position.title).update(
                    {'employee_id': new_assigned_employees[0].id},
                    synchronize_session=False
                )

            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Position updated',
                'position': {
                    'id': position.id,
                    'title': position.title,
                    'is_active': position.is_active,
                    'assigned_employee_id': position.assigned_employee_id,
                    'assigned_employee_ids': [employee.id for employee in position.assigned_employees]
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/positions/<int:position_id>', methods=['DELETE'])
    @require_manage_positions
    def delete_position(position_id):
        """Delete a position."""
        try:
            position = Position.query.get_or_404(position_id)
            title = position.title

            applicant_count = Applicant.query.filter_by(job_position=title).count()
            current_role = current_user.role_obj.name if current_user.role_obj else None
            if applicant_count > 0 and current_role != 'SUPER_ADMIN':
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete position with {applicant_count} applicants. Deactivate instead.'
                }), 400

            if applicant_count > 0:
                Applicant.query.filter_by(job_position=title).update(
                    {
                        'job_position': 'Position Deleted',
                        'employee_id': None
                    },
                    synchronize_session=False
                )

            position.assigned_employees = []
            db.session.delete(position)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Position "{title}" deleted'
                    + (f' and {applicant_count} applicant(s) were unassigned.' if applicant_count else '')
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

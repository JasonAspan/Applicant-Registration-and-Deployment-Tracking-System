import io

import pytest


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{tmp_path / "test.db"}')

    from ats_app import create_app

    app = create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home')
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(username, role_name):
    from models import Employee, Role, db
    from time_utils import ph_now

    if Employee.query.filter_by(username=username).first():
        username = f'{username}_{Employee.query.count() + 1}'

    role = Role.query.filter_by(name=role_name).first()
    user = Employee(
        username=username,
        email=f'{username}@example.test',
        role_id=role.id,
        is_active=True,
        email_verified=True,
        session_started_at=ph_now(),
        last_seen_at=ph_now(),
    )
    user.set_password('Password123')
    db.session.add(user)
    db.session.commit()
    return user


def login(client, user):
    with client.session_transaction() as session:
        session['_user_id'] = str(user.id)
        session['_fresh'] = True


def set_permission_override(user, permission_key, is_allowed):
    from models import Permission, UserPermission, db

    permission = Permission.query.filter_by(key=permission_key).one()
    override = UserPermission.query.filter_by(user_id=user.id, permission_id=permission.id).first()
    if override:
        override.is_allowed = is_allowed
    else:
        db.session.add(UserPermission(
            user_id=user.id,
            permission_id=permission.id,
            is_allowed=is_allowed,
            reason='Test override',
        ))
    db.session.commit()


def test_employee_registration_sends_verification_email(app, client, monkeypatch):
    sent_to = []

    def fake_send_email_verification(employee):
        sent_to.append(employee.email)

    monkeypatch.setattr('routes_employee.send_email_verification', fake_send_email_verification)

    response = client.post('/employee-register.html', data={
        'username': 'new_employee',
        'password': 'Password123',
        'email': 'new_employee@cavesmanpower.com',
    })

    assert response.status_code == 302
    assert sent_to == ['new_employee@cavesmanpower.com']

    with app.app_context():
        from models import Employee

        user = Employee.query.filter_by(username='new_employee').one()
        assert user.email_verified is False
        assert user.email_verification_sent_at is not None


def test_login_requires_email_mfa_code(app, client, monkeypatch):
    sent_codes = []

    def fake_send_mfa_code(employee, code):
        sent_codes.append((employee.email, code))

    monkeypatch.setattr('routes_auth.send_mfa_code', fake_send_mfa_code)

    with app.app_context():
        user = create_user('mfa_user', 'LEVEL_1_USER')
        user_id = user.id

    login_response = client.post('/employee-login.html', data={
        'username': 'mfa_user',
        'password': 'Password123',
    })

    assert login_response.status_code == 302
    assert login_response.headers['Location'].endswith('/employee-mfa.html')
    assert len(sent_codes) == 1

    with client.session_transaction() as session:
        assert '_user_id' not in session
        assert session['pending_mfa_user_id'] == user_id

    bad_response = client.post('/employee-mfa.html', data={'code': '000000'})
    assert bad_response.status_code == 200

    good_response = client.post('/employee-mfa.html', data={'code': sent_codes[0][1]})
    assert good_response.status_code == 302
    assert good_response.headers['Location'].endswith('/dashboard.html')

    with client.session_transaction() as session:
        assert session['_user_id'] == str(user_id)
        assert 'pending_mfa_user_id' not in session


def test_superadmin_login_skips_mfa(app, client, monkeypatch):
    def fail_send_mfa_code(employee, code):
        raise AssertionError('SUPER_ADMIN should not receive MFA challenge')

    monkeypatch.setattr('routes_auth.send_mfa_code', fail_send_mfa_code)

    with app.app_context():
        admin = create_user('mfa_superadmin', 'SUPER_ADMIN')
        admin_id = admin.id

    response = client.post('/employee-login.html', data={
        'username': 'mfa_superadmin',
        'password': 'Password123',
    })

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard.html')

    with client.session_transaction() as session:
        assert session['_user_id'] == str(admin_id)
        assert 'pending_mfa_user_id' not in session


def test_api_404_errors_are_json(app, client):
    with app.app_context():
        admin = create_user('superadmin_test', 'SUPER_ADMIN')
        login(client, admin)

    response = client.get('/api/users/999999/profile')

    assert response.status_code == 404
    assert response.is_json
    assert 'error' in response.get_json()


def test_cv_upload_over_5mb_is_rejected(app, client):
    response = client.post(
        '/applicant-register.html',
        data={
            'first_name': 'Large',
            'last_name': 'Upload',
            'age': '25',
            'birth_date': '2001-01-01',
            'gender': 'Other',
            'contact_number': '1234567890',
            'email': 'large-upload@example.test',
            'job_position': 'Any',
            'cv': (io.BytesIO(b'%PDF' + (b'x' * (5 * 1024 * 1024))), 'large.pdf'),
        },
        content_type='multipart/form-data',
    )

    assert response.status_code == 413
    assert b'Maximum size is 5MB' in response.data


def test_applicant_registration_rejects_duplicate_identity(app, client):
    with app.app_context():
        from models import Applicant, Position, db

        assignee = create_user('duplicate_identity_assignee', 'LEVEL_1_USER')
        position = Position(
            title='Duplicate Identity Tester',
            is_active=True,
            assigned_employee_id=assignee.id,
        )
        position.assigned_employees.append(assignee)
        db.session.add(position)
        db.session.commit()

    application = {
        'first_name': 'Maria',
        'last_name': 'Santos',
        'middle_initial': 'D',
        'suffix': '',
        'age': '27',
        'birth_date': '1999-04-12',
        'gender': 'Female',
        'contact_number': '0912345678',
        'email': 'maria.santos@example.test',
        'job_position': 'Duplicate Identity Tester',
    }

    first_response = client.post('/applicant-register.html', data=application)
    assert first_response.status_code == 302

    duplicate = {
        **application,
        'first_name': '  maria ',
        'last_name': ' SANTOS ',
        'middle_initial': ' d ',
        'email': 'maria.santos.second@example.test',
    }
    duplicate_response = client.post('/applicant-register.html', data=duplicate)

    assert duplicate_response.status_code == 200
    assert b'already exists for this applicant name, contact number, and birth date' in duplicate_response.data
    with app.app_context():
        assert Applicant.query.filter_by(job_position='Duplicate Identity Tester').count() == 1


def test_applicant_registration_allows_same_name_with_different_identity_details(app, client):
    with app.app_context():
        from models import Applicant, Position, db

        assignee = create_user('same_name_assignee', 'LEVEL_1_USER')
        position = Position(
            title='Same Name Coincidence Tester',
            is_active=True,
            assigned_employee_id=assignee.id,
        )
        position.assigned_employees.append(assignee)
        db.session.add(position)
        db.session.commit()

    base_application = {
        'first_name': 'Juan',
        'last_name': 'Reyes',
        'middle_initial': '',
        'suffix': '',
        'age': '31',
        'birth_date': '1995-08-20',
        'gender': 'Male',
        'contact_number': '0911111111',
        'email': 'juan.reyes@example.test',
        'job_position': 'Same Name Coincidence Tester',
    }
    same_name_different_person = {
        **base_application,
        'birth_date': '1996-08-20',
        'contact_number': '0922222222',
        'email': 'juan.reyes.other@example.test',
    }

    assert client.post('/applicant-register.html', data=base_application).status_code == 302
    assert client.post('/applicant-register.html', data=same_name_different_person).status_code == 302

    with app.app_context():
        assert Applicant.query.filter_by(job_position='Same Name Coincidence Tester').count() == 2


def test_access_admin_panel_permission_controls_menu_and_page(app, client):
    with app.app_context():
        admin = create_user('panel_admin', 'ADMIN')
        set_permission_override(admin, 'access_admin_panel', True)
        set_permission_override(admin, 'manage_users', False)
        login(client, admin)

    dashboard_response = client.get('/dashboard.html')
    assert dashboard_response.status_code == 200
    assert b'Admin Panel' in dashboard_response.data

    panel_response = client.get('/admin-panel.html')
    assert panel_response.status_code == 200


def test_user_permission_overrides_block_applicant_actions(app, client):
    from models import Applicant, db
    from time_utils import ph_now

    with app.app_context():
        user = create_user('limited_admin', 'ADMIN')
        set_permission_override(user, 'delete_applicant', False)
        set_permission_override(user, 'export_applicant_cv', False)
        set_permission_override(user, 'export_applicant_excel', False)
        applicant = Applicant(
            first_name='Permission',
            last_name='Check',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='permission-check@example.test',
            job_position='Developer',
            employee_id=user.id,
            cv_filename='resume.pdf',
            cv_content_type='application/pdf',
            cv_data=b'%PDF test',
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        login(client, user)

    delete_response = client.post('/applicants/batch-delete', data={'applicant_ids': str(applicant_id)})
    assert delete_response.status_code == 302

    cv_response = client.get(f'/applicants/{applicant_id}/cv')
    assert cv_response.status_code == 403

    excel_response = client.post('/applicants/export-excel', data={'applicant_ids': str(applicant_id)})
    assert excel_response.status_code == 302


def test_user_delete_forgets_identity_and_requires_registration(app, client):
    from models import Employee, db

    with app.app_context():
        admin = create_user('superadmin_test', 'SUPER_ADMIN')
        target = create_user('target_user', 'LEVEL_1_USER')
        target_email = target.email
        login(client, admin)
        target_id = target.id

    delete_response = client.delete(f'/api/users/{target_id}/permanent')
    assert delete_response.status_code == 200

    with app.app_context():
        deleted_user = Employee.query.get(target_id)
        assert deleted_user.is_deleted is True
        assert deleted_user.is_active is False
        assert deleted_user.username != 'target_user'
        assert deleted_user.email != target_email

    list_response = client.get('/api/users?per_page=100')
    assert list_response.status_code == 200
    assert target_id not in [user['id'] for user in list_response.get_json()['users']]

    restore_response = client.post(f'/api/users/{target_id}/restore')
    assert restore_response.status_code == 410

    with app.app_context():
        duplicate = Employee(
            username='target_user',
            email=target_email,
            role_id=deleted_user.role_id,
            is_active=True,
            email_verified=False,
        )
        duplicate.set_password('Password123')
        db.session.add(duplicate)
        db.session.commit()
        assert duplicate.id != target_id


def test_superadmin_applicant_delete_is_restorable(app, client):
    from models import Applicant, db
    from time_utils import ph_now

    with app.app_context():
        admin = create_user('superadmin_test', 'SUPER_ADMIN')
        applicant = Applicant(
            first_name='Soft',
            last_name='Delete',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='soft-delete@example.test',
            job_position='Developer',
            employee_id=admin.id,
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        login(client, admin)

    delete_response = client.post('/applicants/batch-delete', data={'applicant_ids': str(applicant_id)})
    assert delete_response.status_code == 302

    deleted_response = client.get('/api/applicants/deleted')
    assert deleted_response.status_code == 200
    assert applicant_id in [item['id'] for item in deleted_response.get_json()['applicants']]

    restore_response = client.post(f'/api/applicants/{applicant_id}/restore')
    assert restore_response.status_code == 200

    with app.app_context():
        restored = Applicant.query.get(applicant_id)
        assert restored.is_deleted is False


def test_applicant_status_requires_remark_owner_and_resets_on_undo(app, client):
    from models import Applicant, Position, db
    from time_utils import ph_now

    with app.app_context():
        first_user = create_user('status_owner', 'LEVEL_1_USER')
        second_user = create_user('status_peer', 'LEVEL_1_USER')
        position = Position(title='Status Tester', is_active=True)
        position.assigned_employees.append(first_user)
        position.assigned_employees.append(second_user)
        db.session.add(position)
        db.session.flush()
        applicant = Applicant(
            first_name='Status',
            last_name='Flow',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='status-flow@example.test',
            job_position=position.title,
            employee_id=first_user.id,
            status='OPEN',
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        first_user_id = first_user.id

        login(client, first_user)

    remark_response = client.post(f'/applicants/{applicant_id}/remark')
    assert remark_response.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.remarked_by_id == first_user_id
        assert applicant.status == 'Lined-up'

        second_user = create_user('status_peer_login', 'LEVEL_1_USER')
        position = Position.query.filter_by(title='Status Tester').one()
        position.assigned_employees.append(second_user)
        db.session.commit()
        login(client, second_user)

    second_remark_response = client.post(f'/applicants/{applicant_id}/remark')
    assert second_remark_response.status_code == 302

    second_status_response = client.post(
        f'/applicants/{applicant_id}/status',
        data={'status': 'Selected'},
    )
    assert second_status_response.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.status == 'Lined-up'

        from models import Employee

        owner = db.session.get(Employee, first_user_id)
        login(client, owner)

    owner_status_response = client.post(
        f'/applicants/{applicant_id}/status',
        data={'status': 'Selected'},
    )
    assert owner_status_response.status_code == 302

    undo_response = client.post(f'/applicants/{applicant_id}/remark/undo')
    assert undo_response.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.remarked_by_id is None
        assert applicant.status == 'OPEN'


def test_remarked_applicant_cannot_be_forwarded_until_remark_removed(app, client):
    from models import Announcement, Applicant, ApplicantForward, Employee, db
    from time_utils import ph_now

    with app.app_context():
        admin = create_user('forward_admin', 'ADMIN')
        target = create_user('forward_target', 'LEVEL_1_USER')
        applicant = Applicant(
            first_name='Forward',
            last_name='Locked',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='forward-locked@example.test',
            job_position='Developer',
            employee_id=admin.id,
            status='OPEN',
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        admin_id = admin.id
        target_id = target.id
        login(client, admin)

    remark_response = client.post(f'/applicants/{applicant_id}/remark')
    assert remark_response.status_code == 302

    blocked_forward = client.post(
        '/applicants/forward',
        data={'applicant_ids': str(applicant_id), 'target_user_id': str(target_id)},
    )
    assert blocked_forward.status_code == 302

    with app.app_context():
        assert ApplicantForward.query.filter_by(applicant_id=applicant_id, to_employee_id=target_id).count() == 0

    undo_response = client.post(f'/applicants/{applicant_id}/remark/undo')
    assert undo_response.status_code == 302

    allowed_forward = client.post(
        '/applicants/forward',
        data={'applicant_ids': str(applicant_id), 'target_user_id': str(target_id)},
    )
    assert allowed_forward.status_code == 302

    with app.app_context():
        assert ApplicantForward.query.filter_by(applicant_id=applicant_id, to_employee_id=target_id).count() == 1
        notification = Announcement.query.filter_by(recipient_employee_id=target_id).one()
        assert notification.title == 'Applicant Forwarded'
        assert notification.message == 'forward_admin forwarded you an Applicant.'

        login(client, db.session.get(Employee, target_id))

    notifications_response = client.get('/api/announcements')
    assert notifications_response.status_code == 200
    notifications_payload = notifications_response.get_json()
    forward_notifications = [
        item for item in notifications_payload['announcements']
        if item['title'] == 'Applicant Forwarded'
    ]
    assert forward_notifications
    assert forward_notifications[0]['message'] == 'forward_admin forwarded you an Applicant.'
    assert forward_notifications[0]['recipient_id'] == target_id

    with app.app_context():
        login(client, db.session.get(Employee, admin_id))

    duplicate_forward = client.post(
        '/applicants/forward',
        data={'applicant_ids': str(applicant_id), 'target_user_id': str(target_id)},
    )
    assert duplicate_forward.status_code == 302

    with app.app_context():
        assert ApplicantForward.query.filter_by(applicant_id=applicant_id, to_employee_id=target_id).count() == 1
        assert Announcement.query.filter_by(recipient_employee_id=target_id).count() == 2


def test_admin_can_undo_other_users_remark_but_peer_cannot(app, client):
    from models import Applicant, Position, db
    from time_utils import ph_now

    with app.app_context():
        owner = create_user('remark_owner_admin_test', 'LEVEL_1_USER')
        peer = create_user('remark_peer_admin_test', 'LEVEL_1_USER')
        admin = create_user('remark_admin_test', 'ADMIN')
        position = Position(title='Admin Undo Tester', is_active=True)
        position.assigned_employees.append(owner)
        position.assigned_employees.append(peer)
        db.session.add(position)
        db.session.flush()
        applicant = Applicant(
            first_name='Admin',
            last_name='Undo',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='admin-undo@example.test',
            job_position=position.title,
            employee_id=owner.id,
            status='OPEN',
            remarked_by_id=owner.id,
            remarked_at=ph_now(),
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        peer_id = peer.id
        admin_id = admin.id

        login(client, peer)

    peer_undo = client.post(f'/applicants/{applicant_id}/remark/undo')
    assert peer_undo.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.remarked_by_id != peer_id
        assert applicant.remarked_by_id is not None

        from models import Employee

        login(client, db.session.get(Employee, admin_id))

    admin_undo = client.post(f'/applicants/{applicant_id}/remark/undo')
    assert admin_undo.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.remarked_by_id is None
        assert applicant.status == 'OPEN'


def test_profile_analytics_layout_is_role_gated(app, client):
    roles = [
        ('profile_level1', 'LEVEL_1_USER', True),
        ('profile_level2', 'LEVEL_2_USER', True),
        ('profile_admin', 'ADMIN', True),
        ('profile_superadmin', 'SUPER_ADMIN', True),
    ]

    for username, role_name, should_show_analytics in roles:
        with app.app_context():
            user = create_user(username, role_name)
            login(client, user)

        response = client.get('/profile.html')
        assert response.status_code == 200
        assert (b'data-profile-analytics' in response.data) is should_show_analytics


def test_level_user_profiles_hide_movement_analytics_but_keep_position_status(app, client):
    for username, role_name in [('profile_no_movement_l1', 'LEVEL_1_USER'), ('profile_no_movement_l2', 'LEVEL_2_USER')]:
        with app.app_context():
            user = create_user(username, role_name)
            login(client, user)

        response = client.get('/profile.html')
        assert response.status_code == 200
        assert b'Applicants by Position and Status' in response.data
        assert b'Applicant Movement' not in response.data
        assert b'profileMovementChart' not in response.data


def test_profile_todo_crud_for_admin_and_level_users(app, client):
    with app.app_context():
        user = create_user('profile_todo_level1', 'LEVEL_1_USER')
        login(client, user)

    add_response = client.post('/profile.html', data={
        'profile_action': 'todo',
        'todo_action': 'add',
        'todo_text': 'Call applicant',
    })
    assert add_response.status_code == 302

    profile_response = client.get('/profile.html')
    assert profile_response.status_code == 200
    assert b'To-do (1)' in profile_response.data
    assert b'Call applicant' in profile_response.data

    with app.app_context():
        from models import ProfileTodo

        todo = ProfileTodo.query.filter_by(text='Call applicant').one()
        todo_id = todo.id

    update_response = client.post('/profile.html', data={
        'profile_action': 'todo',
        'todo_action': 'update',
        'todo_id': str(todo_id),
        'todo_text': 'Call applicant again',
    })
    assert update_response.status_code == 302

    toggle_response = client.post('/profile.html', data={
        'profile_action': 'todo',
        'todo_action': 'toggle',
        'todo_id': str(todo_id),
    })
    assert toggle_response.status_code == 302

    with app.app_context():
        from models import ProfileTodo, db

        todo = db.session.get(ProfileTodo, todo_id)
        assert todo.text == 'Call applicant again'
        assert todo.is_done is True

    delete_response = client.post('/profile.html', data={
        'profile_action': 'todo',
        'todo_action': 'delete',
        'todo_id': str(todo_id),
    })
    assert delete_response.status_code == 302

    with app.app_context():
        from models import ProfileTodo, db

        assert db.session.get(ProfileTodo, todo_id) is None

        admin = create_user('profile_todo_admin', 'ADMIN')
        login(client, admin)

    admin_add_response = client.post('/profile.html', data={
        'profile_action': 'todo',
        'todo_action': 'add',
        'todo_text': 'Review team queue',
    })
    assert admin_add_response.status_code == 302
    admin_profile = client.get('/profile.html')
    assert admin_profile.status_code == 200
    assert b'To-do (1)' in admin_profile.data
    assert b'Review team queue' in admin_profile.data


def test_admin_profile_analytics_aggregates_level_users_not_admin_dashboard(app, client):
    from models import Applicant, Position, db
    from time_utils import ph_now

    with app.app_context():
        admin = create_user('profile_aggregate_admin', 'ADMIN')
        level_user = create_user('profile_aggregate_level1', 'LEVEL_1_USER')
        level_position = Position(title='Aggregate Level Position', is_active=True)
        level_position.assigned_employees.append(level_user)
        db.session.add(level_position)
        db.session.flush()
        level_applicant = Applicant(
            first_name='Level',
            last_name='Aggregate',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='level-aggregate@example.test',
            job_position=level_position.title,
            employee_id=level_user.id,
            status='Selected',
            remarked_by_id=level_user.id,
            remarked_at=ph_now(),
        )
        admin_only_applicant = Applicant(
            first_name='Admin',
            last_name='DashboardOnly',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='admin-dashboard-only@example.test',
            job_position='Admin Only Position',
            employee_id=admin.id,
            status='Deployed',
            remarked_by_id=admin.id,
            remarked_at=ph_now(),
        )
        db.session.add_all([level_applicant, admin_only_applicant])
        db.session.commit()
        login(client, admin)

    response = client.get('/profile.html')
    assert response.status_code == 200
    assert b'Level 1/2 Profile Analytics' in response.data
    assert b'profile_aggregate_level1' in response.data
    assert b'Admin Only Position' not in response.data


def test_profile_analytics_counts_respect_level_user_visibility(app, client):
    from models import Applicant, ApplicantForward, Position, db
    from time_utils import ph_now

    with app.app_context():
        user = create_user('profile_visibility_user', 'LEVEL_1_USER')
        owner = create_user('profile_visibility_owner', 'LEVEL_1_USER')
        position_visible = Position(title='Analytics Visible Position', is_active=True)
        position_hidden = Position(title='Analytics Hidden Position', is_active=True)
        position_visible.assigned_employees.append(user)
        db.session.add_all([position_visible, position_hidden])
        db.session.flush()

        visible_by_position = Applicant(
            first_name='Visible',
            last_name='Position',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='visible-position@example.test',
            job_position=position_visible.title,
            employee_id=owner.id,
            status='Lined-up',
            remarked_by_id=owner.id,
            remarked_at=ph_now(),
        )
        visible_by_forward = Applicant(
            first_name='Visible',
            last_name='Forward',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='visible-forward@example.test',
            job_position='Forwarded Analytics Position',
            employee_id=owner.id,
            status='Selected',
            remarked_by_id=owner.id,
            remarked_at=ph_now(),
        )
        hidden = Applicant(
            first_name='Hidden',
            last_name='Applicant',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='hidden-analytics@example.test',
            job_position=position_hidden.title,
            employee_id=owner.id,
            status='Deployed',
            remarked_by_id=owner.id,
            remarked_at=ph_now(),
        )
        db.session.add_all([visible_by_position, visible_by_forward, hidden])
        db.session.flush()
        db.session.add(ApplicantForward(
            applicant_id=visible_by_forward.id,
            from_employee_id=owner.id,
            to_employee_id=user.id,
        ))
        db.session.commit()
        login(client, user)

    response = client.get('/profile.html')
    assert response.status_code == 200
    assert b'Analytics Visible Position' in response.data
    assert b'Forwarded Analytics Position' in response.data
    assert b'Analytics Hidden Position' not in response.data
    assert b'Overall Applicant' in response.data
    assert b'>2</strong>' in response.data


def test_profile_analytics_export_restrictions_and_filters(app, client):
    from datetime import datetime

    from models import Applicant, Employee, Position, Role, db

    with app.app_context():
        admin = create_user('profile_export_admin', 'ADMIN')
        blocked_role = Role(name='PROFILE_EXPORT_BLOCKED', description='Blocked from profile analytics export')
        db.session.add(blocked_role)
        db.session.flush()
        blocked_user = Employee(
            username='profile_export_blocked',
            email='profile_export_blocked@example.test',
            role_id=blocked_role.id,
            is_active=True,
        )
        blocked_user.set_password('Password123')
        db.session.add(blocked_user)
        user = create_user('profile_export_level1', 'LEVEL_1_USER')
        position = Position(title='Export Analytics Position', is_active=True)
        position.assigned_employees.append(user)
        db.session.add(position)
        db.session.flush()
        selected = Applicant(
            first_name='Selected',
            last_name='Export',
            age=30,
            birth_date=datetime(1990, 1, 1),
            gender='Other',
            contact_number='1234567890',
            email='selected-export@example.test',
            job_position=position.title,
            employee_id=user.id,
            status='Selected',
            remarked_by_id=user.id,
            remarked_at=datetime(2026, 5, 10, 9, 0),
            applied_at=datetime(2026, 5, 10, 9, 0),
        )
        lined_up = Applicant(
            first_name='Lined',
            last_name='Export',
            age=30,
            birth_date=datetime(1990, 1, 1),
            gender='Other',
            contact_number='1234567890',
            email='lined-export@example.test',
            job_position=position.title,
            employee_id=user.id,
            status='Lined-up',
            remarked_by_id=user.id,
            remarked_at=datetime(2026, 5, 9, 9, 0),
            applied_at=datetime(2026, 5, 9, 9, 0),
        )
        db.session.add_all([selected, lined_up])
        db.session.commit()

        login(client, blocked_user)

    restricted_response = client.get('/profile/analytics/export')
    assert restricted_response.status_code in {302, 403}
    assert not restricted_response.data.startswith(b'%PDF')

    with app.app_context():
        from models import Employee

        login(client, Employee.query.filter_by(username='profile_export_admin').one())

    admin_response = client.get('/profile/analytics/export?status=Selected&date_from=2026-05-10&date_to=2026-05-10')
    assert admin_response.status_code == 200
    assert admin_response.headers['Content-Type'].startswith('application/pdf')
    admin_pdf_text = admin_response.data.decode('latin-1')
    assert 'Selected Export' in admin_pdf_text
    assert 'profile_export_level1' in admin_pdf_text
    assert 'Lined Export' not in admin_pdf_text

    with app.app_context():
        from models import Employee

        login(client, Employee.query.filter_by(username='profile_export_level1').one())

    export_response = client.get('/profile/analytics/export?status=Selected&date_from=2026-05-10&date_to=2026-05-10')
    assert export_response.status_code == 200
    assert export_response.headers['Content-Type'].startswith('application/pdf')
    assert 'profile_analytics_profile_export_level1_' in export_response.headers['Content-Disposition']
    assert '.pdf' in export_response.headers['Content-Disposition']
    assert export_response.data.startswith(b'%PDF-1.4')
    pdf_text = export_response.data.decode('latin-1')
    assert 'Selected Export' in pdf_text
    assert 'Selected' in pdf_text
    assert 'Lined Export' not in pdf_text


def test_profile_analytics_team_can_be_saved_without_schema_change(app, client):
    with app.app_context():
        user = create_user('profile_team_level1', 'LEVEL_1_USER')
        login(client, user)

    response = client.post('/profile.html', data={'profile_action': 'team', 'team': 'team: Australia'})
    assert response.status_code == 302

    profile_response = client.get('/profile.html')
    assert profile_response.status_code == 200
    assert b'team: Australia' in profile_response.data


def test_announcements_keep_latest_five_and_track_user_reads(app, client):
    with app.app_context():
        admin = create_user('announcement_admin', 'SUPER_ADMIN')
        reader = create_user('announcement_reader', 'LEVEL_1_USER')
        login(client, admin)
        reader_id = reader.id

    for index in range(6):
        response = client.post(
            '/api/announcements',
            json={
                'title': f'Announcement {index}',
                'message': f'Message {index}',
            },
        )
        assert response.status_code == 201

    admin_list = client.get('/api/announcements')
    assert admin_list.status_code == 200
    admin_payload = admin_list.get_json()
    assert len(admin_payload['announcements']) == 5
    assert [item['title'] for item in admin_payload['announcements']] == [
        'Announcement 5',
        'Announcement 4',
        'Announcement 3',
        'Announcement 2',
        'Announcement 1',
    ]

    with app.app_context():
        from models import Announcement, Employee, db

        assert Announcement.query.filter(Announcement.recipient_employee_id.is_(None)).count() == 5
        login(client, db.session.get(Employee, reader_id))

    reader_list = client.get('/api/announcements')
    reader_payload = reader_list.get_json()
    assert reader_payload['unread_count'] == 5

    first_id = reader_payload['announcements'][0]['id']
    read_response = client.post(f'/api/announcements/{first_id}/read')
    assert read_response.status_code == 200

    updated_reader_list = client.get('/api/announcements')
    updated_payload = updated_reader_list.get_json()
    assert updated_payload['unread_count'] == 4
    assert updated_payload['announcements'][0]['is_read'] is True


def test_only_superadmin_can_compose_announcements(app, client):
    with app.app_context():
        admin = create_user('announcement_regular_admin', 'ADMIN')
        set_permission_override(admin, 'access_admin_panel', True)
        login(client, admin)

    blocked_response = client.post(
        '/api/announcements',
        json={'title': 'Admin notice', 'message': 'Should be blocked'},
    )
    assert blocked_response.status_code == 403

    admin_panel = client.get('/admin-panel.html')
    assert admin_panel.status_code == 200
    assert b'Only SUPERADMIN accounts can compose announcements.' in admin_panel.data
    assert b'id="createAnnouncementForm"' not in admin_panel.data

    with app.app_context():
        superadmin = create_user('announcement_superadmin_only', 'SUPER_ADMIN')
        login(client, superadmin)

    allowed_panel = client.get('/admin-panel.html')
    assert allowed_panel.status_code == 200
    assert b'Compose Announcement' in allowed_panel.data
    assert b'id="createAnnouncementForm"' in allowed_panel.data


def test_marking_applicant_deployed_captures_recruiter(app, client):
    from models import Applicant, Position, db
    from time_utils import ph_now

    with app.app_context():
        user = create_user('deploy_recruiter', 'LEVEL_1_USER')
        position = Position(title='Deploy Tester', is_active=True)
        position.assigned_employees.append(user)
        db.session.add(position)
        db.session.flush()
        applicant = Applicant(
            first_name='Deploy',
            last_name='Candidate',
            age=30,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='deploy-candidate@example.test',
            job_position=position.title,
            employee_id=user.id,
            status='OPEN',
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        user_id = user.id
        login(client, user)

    client.post(f'/applicants/{applicant_id}/remark')
    response = client.post(f'/applicants/{applicant_id}/status', data={'status': 'Deployed'})
    assert response.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.status == 'Deployed'
        assert applicant.deployed_by_id == user_id
        assert applicant.deployed_at is not None


def test_level_3_user_can_view_and_manage_deployed_applicants(app, client):
    from models import Applicant, ApplicantDocument, db
    from time_utils import ph_now

    with app.app_context():
        recruiter = create_user('deploy_original_recruiter', 'LEVEL_1_USER')
        level3 = create_user('deploy_level3', 'LEVEL_3_USER')
        applicant = Applicant(
            first_name='Deployed',
            last_name='Worker',
            age=28,
            birth_date=ph_now(),
            gender='Other',
            contact_number='1234567890',
            email='deployed-worker@example.test',
            job_position='Welder',
            employee_id=recruiter.id,
            status='Deployed',
            deployed_by_id=recruiter.id,
            deployed_at=ph_now(),
        )
        db.session.add(applicant)
        db.session.commit()
        applicant_id = applicant.id
        login(client, level3)

    page_response = client.get('/deployed-applicants.html')
    assert page_response.status_code == 200
    assert b'Deployed Worker' in page_response.data
    assert b'deploy_original_recruiter' in page_response.data

    update_response = client.post(
        f'/deployed-applicants/{applicant_id}/update',
        data={
            'employer_name': 'Acme Corp',
            'deployment_country': 'Qatar',
            'contract_start_date': '2026-01-01',
            'contract_end_date': '2026-12-31',
            'deployment_status': 'Deployed',
            'deployment_remarks': 'On track',
        },
    )
    assert update_response.status_code == 302

    with app.app_context():
        applicant = Applicant.query.get(applicant_id)
        assert applicant.employer_name == 'Acme Corp'
        assert applicant.deployment_country == 'Qatar'

    upload_response = client.post(
        f'/deployed-applicants/{applicant_id}/documents/upload',
        data={'documents': (io.BytesIO(b'%PDF test document'), 'passport.pdf')},
        content_type='multipart/form-data',
    )
    assert upload_response.status_code == 302

    with app.app_context():
        document = ApplicantDocument.query.filter_by(applicant_id=applicant_id).one()
        document_id = document.id

    download_response = client.get(f'/deployed-applicants/{applicant_id}/documents/{document_id}/download')
    assert download_response.status_code == 200
    assert download_response.data == b'%PDF test document'


def test_level_1_and_level_2_users_denied_deployed_applicants_page(app, client):
    with app.app_context():
        level1 = create_user('deploy_denied_level1', 'LEVEL_1_USER')
        login(client, level1)

    response = client.get('/deployed-applicants.html')
    assert response.status_code == 302

    with app.app_context():
        level2 = create_user('deploy_denied_level2', 'LEVEL_2_USER')
        login(client, level2)

    response = client.get('/deployed-applicants.html')
    assert response.status_code == 302

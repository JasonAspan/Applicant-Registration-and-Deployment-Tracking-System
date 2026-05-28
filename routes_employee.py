from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import login_required, login_user, logout_user, current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime, time
from werkzeug.utils import secure_filename
from xml.sax.saxutils import escape as xml_escape
import json
import os

from models import Announcement, Applicant, ApplicantDashboardDeletion, ApplicantForward, Employee, Position, ProfileTodo, Role, db
from auth_rbac import require_permission, has_permission, get_user_permissions
from email_verification import send_email_verification
from time_utils import ph_now

APPLICANT_REMARK_STATUSES = ('Lined-up', 'Short-listed', 'Selected', 'Deployed')
APPLICANT_OPEN_STATUS = 'OPEN'
PROFILE_ANALYTICS_ROLES = {'LEVEL_1_USER', 'LEVEL_2_USER'}
PROFILE_ANALYTICS_ADMIN_ROLES = {'ADMIN', 'SUPER_ADMIN'}
PROFILE_ANALYTICS_LAYOUT_ROLES = PROFILE_ANALYTICS_ROLES | PROFILE_ANALYTICS_ADMIN_ROLES
PROFILE_TODO_ROLES = {'LEVEL_1_USER', 'LEVEL_2_USER', 'ADMIN'}
PROFILE_STATUS_LABELS = ('Pending', 'Lined-up', 'Shortlisted', 'Selected', 'Deployed')
ALLOWED_EMPLOYEE_EMAIL_DOMAIN = '@cavesmanpower.com'
PDF_STATUS_COLORS = {
    'Pending': (100, 116, 139),
    'Lined-up': (37, 99, 235),
    'Shortlisted': (124, 58, 237),
    'Selected': (22, 163, 74),
    'Deployed': (220, 38, 38),
}


def register_employee_routes(app):
    def profile_teams_path():
        os.makedirs(current_app.instance_path, exist_ok=True)
        return os.path.join(current_app.instance_path, 'profile_teams.json')

    def load_profile_teams():
        try:
            with open(profile_teams_path(), 'r', encoding='utf-8') as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}

    def save_profile_team(user_id, team):
        teams = load_profile_teams()
        key = str(user_id)
        clean_team = (team or '').strip()[:80]
        if clean_team:
            teams[key] = clean_team
        else:
            teams.pop(key, None)
        with open(profile_teams_path(), 'w', encoding='utf-8') as handle:
            json.dump(teams, handle, indent=2, sort_keys=True)

    def profile_team_for(user_id):
        return load_profile_teams().get(str(user_id), '')

    def profile_todos_for(user_id):
        return ProfileTodo.query.filter_by(employee_id=user_id).order_by(
            ProfileTodo.is_done.asc(),
            ProfileTodo.created_at.asc(),
            ProfileTodo.id.asc(),
        ).all()

    def handle_profile_todo_action(role_name):
        if role_name not in PROFILE_TODO_ROLES:
            flash('To-do list is available for Level 1, Level 2, and Admin users only.', 'error')
            return redirect(url_for('profile'))

        action = request.form.get('todo_action')
        todo_id = request.form.get('todo_id', type=int)
        todo = None
        if todo_id:
            todo = ProfileTodo.query.filter_by(id=todo_id, employee_id=current_user.id).first_or_404()

        if action == 'add':
            text = (request.form.get('todo_text') or '').strip()
            if not text:
                flash('Enter a to-do item.', 'error')
                return redirect(url_for('profile'))
            if len(text) > 255:
                flash('To-do item must be 255 characters or fewer.', 'error')
                return redirect(url_for('profile'))
            db.session.add(ProfileTodo(employee_id=current_user.id, text=text))
            db.session.commit()
            flash('To-do added.', 'success')
            return redirect(url_for('profile'))

        if action == 'update' and todo:
            text = (request.form.get('todo_text') or '').strip()
            if not text:
                flash('Enter a to-do item.', 'error')
                return redirect(url_for('profile'))
            if len(text) > 255:
                flash('To-do item must be 255 characters or fewer.', 'error')
                return redirect(url_for('profile'))
            todo.text = text
            todo.updated_at = ph_now()
            db.session.commit()
            flash('To-do updated.', 'success')
            return redirect(url_for('profile'))

        if action == 'toggle' and todo:
            todo.is_done = not todo.is_done
            todo.updated_at = ph_now()
            db.session.commit()
            return redirect(url_for('profile'))

        if action == 'delete' and todo:
            db.session.delete(todo)
            db.session.commit()
            flash('To-do deleted.', 'success')
            return redirect(url_for('profile'))

        flash('Invalid to-do action.', 'error')
        return redirect(url_for('profile'))

    def pdf_escape(value):
        return str(value or '').replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    def build_profile_analytics_pdf(analytics, filters, role_name, team_label):
        width = 842
        height = 595
        margin = 42
        contents = []

        def text(x, y, value, size=10, font='F1', color=(31, 41, 55)):
            r, g, b = [component / 255 for component in color]
            contents.append(f'{r:.3f} {g:.3f} {b:.3f} rg BT /{font} {size} Tf {x} {y} Td ({pdf_escape(value)}) Tj ET')

        def line(x1, y1, x2, y2, color=(226, 232, 240), width_value=1):
            r, g, b = [component / 255 for component in color]
            contents.append(f'{r:.3f} {g:.3f} {b:.3f} RG {width_value} w {x1} {y1} m {x2} {y2} l S')

        def rect(x, y, w, h, color=(44, 82, 130)):
            r, g, b = [component / 255 for component in color]
            contents.append(f'{r:.3f} {g:.3f} {b:.3f} rg {x} {y} {w} {h} re f')

        text(margin, height - 44, 'Profile Analytics Report', 18, 'F2', (31, 41, 55))
        text(margin, height - 64, f'User: {current_user.username} | Role: {role_name} | Team: {team_label or "Unassigned"}', 10)
        text(margin, height - 80, f'Generated: {ph_now().strftime("%m/%d/%Y %I:%M %p")} | Status: {filters.get("status") or "All Statuses"} | From: {filters.get("date_from") or "All"} | To: {filters.get("date_to") or "All"}', 9, color=(74, 85, 104))
        line(margin, height - 92, width - margin, height - 92)

        summary_labels = [
            ('Overall Applicant', analytics['counts']['overall']),
            ('Lined-up', analytics['counts']['Lined-up']),
            ('Shortlisted', analytics['counts']['Shortlisted']),
            ('Selected', analytics['counts']['Selected']),
            ('Deployed', analytics['counts']['Deployed']),
        ]
        card_w = 142
        for index, (label, count) in enumerate(summary_labels):
            x = margin + index * (card_w + 8)
            rect(x, height - 142, card_w, 38, (248, 250, 252))
            text(x + 8, height - 118, label, 8, color=(74, 85, 104))
            text(x + 8, height - 136, count, 16, 'F2', (31, 41, 55))

        chart_top = height - 182
        text(margin, chart_top, f'Graphical Analytics: {analytics.get("bar_chart_title", "Applicants by Position and Status")}', 12, 'F2')
        y = chart_top - 18
        max_count = max(analytics['max_position_count'], 1)
        for item in analytics['position_chart'][:6]:
            text(margin, y + 4, item['position'][:24], 8, color=(45, 55, 72))
            x = margin + 150
            for status in PROFILE_STATUS_LABELS:
                count = item['counts'].get(status, 0)
                bar_w = max(1, (count / max_count) * 92) if count else 1
                rect(x, y, bar_w, 10, PDF_STATUS_COLORS[status])
                if count:
                    text(x + bar_w + 3, y + 2, count, 7, color=(45, 55, 72))
                x += 112
            y -= 18
        if not analytics['position_chart']:
            text(margin, y, 'No applicant data for the selected filters.', 9, color=(113, 128, 150))

        line_top = 245
        text(margin, line_top, f'Graphical Analytics: {analytics.get("movement_title", "Applicant Movement")}', 12, 'F2')
        origin_x = margin
        origin_y = 120
        chart_w = 330
        chart_h = 100
        line(origin_x, origin_y, origin_x + chart_w, origin_y)
        line(origin_x, origin_y, origin_x, origin_y + chart_h)
        movement = analytics['movement_chart']
        max_line = max([row['total'] for row in movement] or [1])
        previous = None
        for index, row in enumerate(movement[:12]):
            x = origin_x + (chart_w / max(len(movement[:12]) - 1, 1)) * index
            y_point = origin_y + (row['total'] / max_line) * chart_h
            rect(x - 2, y_point - 2, 4, 4, (44, 82, 130))
            if previous:
                line(previous[0], previous[1], x, y_point, (44, 82, 130), 1.5)
            previous = (x, y_point)
            text(x - 12, origin_y - 14, row['date'][5:], 7, color=(74, 85, 104))
        if not movement:
            text(origin_x + 8, origin_y + 45, 'No movement data.', 9, color=(113, 128, 150))

        table_x = 420
        table_y = 238
        text(table_x, table_y, 'Data Export', 12, 'F2')
        headers = ['Applicant', 'Position', 'Status', 'Applied']
        col_widths = [120, 90, 70, 76]
        y = table_y - 18
        x = table_x
        for header, col_w in zip(headers, col_widths):
            text(x, y, header, 8, 'F2')
            x += col_w
        y -= 12
        for row in analytics['rows'][:12]:
            x = table_x
            values = [row['name'][:22], row['job_position'][:16], row['status'], row['applied_date'][:16]]
            for value, col_w in zip(values, col_widths):
                text(x, y, value, 7, color=(45, 55, 72))
                x += col_w
            y -= 12
            if y < 35:
                break

        stream = '\n'.join(contents).encode('latin-1', errors='replace')
        objects = [
            b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>'.encode('ascii'),
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
            b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream',
        ]
        pdf = bytearray(b'%PDF-1.4\n')
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f'{index} 0 obj\n'.encode('ascii'))
            pdf.extend(obj)
            pdf.extend(b'\nendobj\n')
        xref = len(pdf)
        pdf.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode('ascii'))
        for offset in offsets[1:]:
            pdf.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
        pdf.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode('ascii'))
        return BytesIO(bytes(pdf))

    def dashboard_filters():
        return {
            'q': (request.values.get('q') or '').strip(),
            'job_position': (request.values.get('job_position') or '').strip(),
            'status': (request.values.get('status') or '').strip(),
            'sort': (request.values.get('sort') or 'applied_desc').strip(),
            'date_from': (request.values.get('date_from') or '').strip(),
            'date_to': (request.values.get('date_to') or '').strip(),
        }

    def selected_applicant_ids():
        try:
            return [int(x) for x in request.form.getlist('applicant_ids')]
        except Exception:
            return []

    def parse_filter_date(value: str):
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except Exception:
            return None

    def normalized_status_expression(status):
        if status in {'Pending', 'OPEN'}:
            return or_(
                Applicant.remarked_by_id.is_(None),
                Applicant.status.in_(['OPEN', 'pending', 'Pending']),
            )
        if status in {'Shortlisted', 'Short-listed'}:
            return Applicant.status.in_(['Shortlisted', 'Short-listed'])
        return Applicant.status == status

    def display_applicant_status(applicant):
        if not applicant.remarked_by_id or applicant.status in ('OPEN', 'pending', 'Pending', None):
            return 'Pending'
        if applicant.status == 'Short-listed':
            return 'Shortlisted'
        return applicant.status

    def profile_analytics_filters():
        status = (request.args.get('status') or '').strip()
        if status not in PROFILE_STATUS_LABELS:
            status = ''
        return {
            'status': status,
            'date_from': (request.args.get('date_from') or '').strip(),
            'date_to': (request.args.get('date_to') or '').strip(),
        }

    def apply_profile_analytics_filters(query, filters, include_status=True):
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')
        df = parse_filter_date(date_from) if date_from else None
        dt = parse_filter_date(date_to) if date_to else None

        if df:
            query = query.filter(Applicant.applied_at >= datetime.combine(df, time.min))
        if dt:
            query = query.filter(Applicant.applied_at <= datetime.combine(dt, time.max))
        if include_status and filters.get('status'):
            query = query.filter(normalized_status_expression(filters['status']))
        return query

    def profile_analytics_payload(filters, user=None):
        user = user or current_user
        base_query = user_visible_applicants_query(user)
        filtered_query = apply_profile_analytics_filters(base_query, filters)
        date_filtered_query = apply_profile_analytics_filters(base_query, filters, include_status=False)

        counts = {'overall': filtered_query.count()}
        for status in PROFILE_STATUS_LABELS:
            status_query = filtered_query if filters.get('status') else date_filtered_query
            counts[status] = status_query.filter(normalized_status_expression(status)).count()

        applicants = filtered_query.order_by(Applicant.applied_at.asc(), Applicant.id.asc()).all()
        position_map = {}
        movement_map = {}
        for applicant in applicants:
            status = display_applicant_status(applicant)
            position = applicant.job_position or 'Unassigned'
            if position not in position_map:
                position_map[position] = {label: 0 for label in PROFILE_STATUS_LABELS}
            position_map[position][status] = position_map[position].get(status, 0) + 1

            date_key = applicant.applied_at.strftime('%Y-%m-%d') if applicant.applied_at else 'No date'
            if date_key not in movement_map:
                movement_map[date_key] = {label: 0 for label in PROFILE_STATUS_LABELS}
            movement_map[date_key][status] = movement_map[date_key].get(status, 0) + 1

        max_position_count = max(
            [count for status_counts in position_map.values() for count in status_counts.values()] or [1]
        )
        max_movement_count = max(
            [sum(status_counts.values()) for status_counts in movement_map.values()] or [1]
        )

        rows = [
            {
                'name': applicant.full_name,
                'email': applicant.email,
                'contact_number': applicant.contact_number,
                'job_position': applicant.job_position,
                'status': display_applicant_status(applicant),
                'applied_date': applicant.applied_at.strftime('%m/%d/%Y %I:%M %p') if applicant.applied_at else '',
            }
            for applicant in applicants
        ]

        return {
            'mode': 'applicant',
            'bar_chart_title': 'Applicants by Position and Status',
            'movement_title': 'Applicant Movement',
            'filters': filters,
            'status_options': PROFILE_STATUS_LABELS,
            'counts': counts,
            'position_chart': [
                {'position': position, 'counts': counts_by_status}
                for position, counts_by_status in sorted(position_map.items())
            ],
            'movement_chart': [
                {
                    'date': date_key,
                    'total': sum(counts_by_status.values()),
                    'counts': counts_by_status,
                }
                for date_key, counts_by_status in sorted(movement_map.items())
            ],
            'max_position_count': max_position_count,
            'max_movement_count': max_movement_count,
            'rows': rows,
        }

    def aggregate_level_user_profile_analytics(filters):
        level_users = Employee.query.join(Role).filter(
            Employee.is_active == True,
            Employee.is_deleted == False,
            Role.name.in_(list(PROFILE_ANALYTICS_ROLES)),
        ).order_by(Employee.username.asc()).all()
        counts = {'overall': 0}
        for status in PROFILE_STATUS_LABELS:
            counts[status] = 0
        position_chart = []
        movement_map = {}
        rows = []

        for user in level_users:
            payload = profile_analytics_payload(filters, user=user)
            counts['overall'] += payload['counts']['overall']
            for status in PROFILE_STATUS_LABELS:
                counts[status] += payload['counts'][status]
            position_chart.append({
                'position': f'{user.username} ({user.role_obj.name.replace("_", " ").title() if user.role_obj else "User"})',
                'counts': {status: payload['counts'][status] for status in PROFILE_STATUS_LABELS},
            })
            for movement in payload['movement_chart']:
                date_key = movement['date']
                if date_key not in movement_map:
                    movement_map[date_key] = {label: 0 for label in PROFILE_STATUS_LABELS}
                for status in PROFILE_STATUS_LABELS:
                    movement_map[date_key][status] += movement['counts'].get(status, 0)
            for row in payload['rows']:
                row = dict(row)
                row['job_position'] = f'{user.username}: {row["job_position"]}'
                rows.append(row)

        max_position_count = max(
            [count for item in position_chart for count in item['counts'].values()] or [1]
        )
        max_movement_count = max(
            [sum(status_counts.values()) for status_counts in movement_map.values()] or [1]
        )

        return {
            'mode': 'level_user_profiles',
            'bar_chart_title': 'Level 1/2 Users by Applicant Status',
            'movement_title': 'Level 1/2 Applicant Movement',
            'filters': filters,
            'status_options': PROFILE_STATUS_LABELS,
            'counts': counts,
            'position_chart': position_chart,
            'movement_chart': [
                {
                    'date': date_key,
                    'total': sum(counts_by_status.values()),
                    'counts': counts_by_status,
                }
                for date_key, counts_by_status in sorted(movement_map.items())
            ],
            'max_position_count': max_position_count,
            'max_movement_count': max_movement_count,
            'rows': rows,
            'source_users_count': len(level_users),
        }

    def filtered_applicants_query(filters):
        query = visible_applicants_query()
        q = filters.get('q', '')
        job_position = filters.get('job_position', '')
        status = filters.get('status', '')
        sort = filters.get('sort', 'applied_desc')
        date_from = filters.get('date_from', '')
        date_to = filters.get('date_to', '')

        if q:
            like = f'%{q}%'
            query = query.filter(
                or_(
                    Applicant.first_name.ilike(like),
                    Applicant.middle_initial.ilike(like),
                    Applicant.last_name.ilike(like),
                    Applicant.email.ilike(like),
                    Applicant.contact_number.ilike(like),
                    Applicant.job_position.ilike(like),
                )
            )

        if job_position:
            query = query.filter(Applicant.job_position == job_position)

        if status:
            query = query.filter(normalized_status_expression(status))

        df = parse_filter_date(date_from) if date_from else None
        dt = parse_filter_date(date_to) if date_to else None
        if df:
            query = query.filter(Applicant.applied_at >= datetime.combine(df, time.min))
        if dt:
            query = query.filter(Applicant.applied_at <= datetime.combine(dt, time.max))

        if sort == 'applied_asc':
            return query.order_by(Applicant.applied_at.asc())
        if sort == 'name_asc':
            return query.order_by(Applicant.last_name.asc(), Applicant.first_name.asc(), Applicant.applied_at.desc())
        if sort == 'name_desc':
            return query.order_by(Applicant.last_name.desc(), Applicant.first_name.desc(), Applicant.applied_at.desc())
        return query.order_by(Applicant.applied_at.desc())

    def xlsx_cell(col_index, row_index, value):
        column = ''
        col = col_index
        while col:
            col, rem = divmod(col - 1, 26)
            column = chr(65 + rem) + column
        text = '' if value is None else str(value)
        return f'<c r="{column}{row_index}" t="inlineStr"><is><t>{xml_escape(text)}</t></is></c>'

    def build_xlsx(headers, rows):
        sheet_rows = []
        for row_index, row in enumerate([headers, *rows], start=1):
            cells = ''.join(xlsx_cell(col_index, row_index, value) for col_index, value in enumerate(row, start=1))
            sheet_rows.append(f'<row r="{row_index}">{cells}</row>')

        sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <cols>
    <col min="1" max="1" width="22" customWidth="1"/>
    <col min="2" max="2" width="30" customWidth="1"/>
    <col min="3" max="5" width="24" customWidth="1"/>
    <col min="6" max="9" width="16" customWidth="1"/>
  </cols>
  <sheetData>{''.join(sheet_rows)}</sheetData>
</worksheet>'''
        workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Applicants" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
        rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        workbook_rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>'''
        content_types_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>'''

        output = BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as xlsx:
            xlsx.writestr('[Content_Types].xml', content_types_xml)
            xlsx.writestr('_rels/.rels', rels_xml)
            xlsx.writestr('xl/workbook.xml', workbook_xml)
            xlsx.writestr('xl/_rels/workbook.xml.rels', workbook_rels_xml)
            xlsx.writestr('xl/worksheets/sheet1.xml', sheet_xml)
        output.seek(0)
        return output

    def current_user_role_name():
        if not current_user.is_authenticated or not current_user.role_id:
            return None
        role = Role.query.get(current_user.role_id)
        return role.name if role else None

    def user_role_name(user):
        if not user or not user.role_id:
            return None
        if getattr(user, 'role_obj', None):
            return user.role_obj.name
        role = Role.query.get(user.role_id)
        return role.name if role else None

    def can_view_all_applicants():
        return current_user_role_name() in {'SUPER_ADMIN', 'ADMIN'}

    def is_super_admin():
        return current_user_role_name() == 'SUPER_ADMIN'

    def assigned_position_titles():
        if not current_user.is_authenticated:
            return []
        return [
            position.title for position in current_user.assigned_positions
            .filter(Position.is_active == True)
            .order_by(Position.title.asc())
            .all()
        ]

    def assigned_position_titles_for_user(user):
        if not user:
            return []
        return [
            position.title for position in user.assigned_positions
            .filter(Position.is_active == True)
            .order_by(Position.title.asc())
            .all()
        ]

    def user_accessible_applicants_query(user, include_admin_all=False):
        role_name = user_role_name(user)
        if include_admin_all and role_name in {'SUPER_ADMIN', 'ADMIN'}:
            return Applicant.query.filter(Applicant.is_deleted == False)

        titles = assigned_position_titles_for_user(user)
        forwarded_ids = db.session.query(ApplicantForward.applicant_id).filter(
            ApplicantForward.to_employee_id == user.id
        )
        visibility_filter = or_(
            Applicant.employee_id == user.id,
            Applicant.id.in_(forwarded_ids),
        )
        if titles:
            visibility_filter = or_(visibility_filter, Applicant.job_position.in_(titles))
        return Applicant.query.filter(Applicant.is_deleted == False).filter(visibility_filter)

    def user_visible_applicants_query(user, include_admin_all=False):
        query = user_accessible_applicants_query(user, include_admin_all=include_admin_all)
        if include_admin_all and user_role_name(user) == 'SUPER_ADMIN':
            return query

        hidden_ids = db.session.query(ApplicantDashboardDeletion.applicant_id).filter(
            ApplicantDashboardDeletion.employee_id == user.id
        )
        return query.filter(~Applicant.id.in_(hidden_ids))

    def accessible_applicants_query():
        return user_accessible_applicants_query(current_user, include_admin_all=True)

    def visible_applicants_query():
        return user_visible_applicants_query(current_user, include_admin_all=True)

    @app.route('/employee')
    @app.route('/employee/')
    def employee_home():
        return render_template('employee_home.html')

    @app.route('/employee-register.html', methods=['GET', 'POST'])
    def employee_register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            email = (request.form.get('email') or '').strip()

            if not email:
                flash('Email is required for account verification.', 'error')
                return render_template('employee_register.html')

            if not email.lower().endswith(ALLOWED_EMPLOYEE_EMAIL_DOMAIN):
                flash('Only @cavesmanpower.com email addresses can register.', 'error')
                return render_template('employee_register.html')

            if Employee.query.filter_by(username=username, is_deleted=False).first():
                flash('Username already exists.', 'error')
                return render_template('employee_register.html')

            if Employee.query.filter_by(email=email, is_deleted=False).first():
                flash('Email already exists.', 'error')
                return render_template('employee_register.html')

            # Assign default LEVEL_1_USER role for RBAC
            from models import Role
            default_role = Role.query.filter_by(name='LEVEL_1_USER').first()
            role_id = default_role.id if default_role else None

            employee = Employee(
                username=username,
                email=email,
                role_id=role_id,
                is_active=True,
                email_verified=not current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True),
                email_verified_at=ph_now() if not current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True) else None,
                email_verification_sent_at=ph_now() if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True) else None
            )
            employee.set_password(password)
            try:
                db.session.add(employee)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('Registration failed (duplicate username/email).', 'error')
                return render_template('employee_register.html')

            if current_app.config.get('EMAIL_VERIFICATION_REQUIRED', True):
                try:
                    send_email_verification(employee)
                except Exception:
                    current_app.logger.exception('Failed to send verification email')
                    employee.email_verification_sent_at = None
                    db.session.commit()
                    flash('Account created, but the verification email service is unavailable. Please contact an administrator.', 'warning')
                    return redirect(url_for('employee_login'))

                flash('kindly check your email for verification', 'success')
                return redirect(url_for('employee_login'))

            flash('Account created successfully. You may now log in.', 'success')
            return redirect(url_for('employee_login'))

        return render_template('employee_register.html')

    # employee_login moved to routes_auth.py for RBAC enforcement

    @app.route('/profile.html', methods=['GET', 'POST'])
    @login_required
    def profile():
        role_name = current_user_role_name() or 'UNASSIGNED'
        if request.method == 'POST':
            if request.form.get('profile_action') == 'todo':
                return handle_profile_todo_action(role_name)

            if request.form.get('profile_action') == 'team':
                save_profile_team(current_user.id, request.form.get('team'))
                flash('Team updated.', 'success')
                return redirect(url_for('profile'))

            pic = request.files.get('profile_picture')
            if not pic or not pic.filename:
                flash('Please choose an image file.', 'error')
                return redirect(url_for('profile'))

            filename = secure_filename(pic.filename)
            content_type = (pic.mimetype or '').lower()
            allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
            if content_type not in allowed_types:
                flash('Profile picture must be JPG, PNG, WEBP, or GIF.', 'error')
                return redirect(url_for('profile'))

            data = pic.read()
            if not data:
                flash('Empty upload.', 'error')
                return redirect(url_for('profile'))

            if len(data) > 2 * 1024 * 1024:
                flash('Image too large (max 2MB).', 'error')
                return redirect(url_for('profile'))

            current_user.profile_filename = filename
            current_user.profile_content_type = content_type
            current_user.profile_data = data
            db.session.commit()
            flash('Profile picture updated.', 'success')
            return redirect(url_for('profile'))

        role_labels = {
            'SUPER_ADMIN': 'Super Admin',
            'ADMIN': 'Admin',
            'LEVEL_2_USER': 'Level 2',
            'LEVEL_1_USER': 'Level 1',
            'UNASSIGNED': 'Unassigned',
        }
        role_descriptions = {
            'SUPER_ADMIN': 'Full system oversight, user control, permissions, positions, and applicant operations.',
            'ADMIN': 'Manages hiring operations, positions, applicant forwarding, exports, and user visibility.',
            'LEVEL_2_USER': 'Reviews assigned applicants, handles escalations, and exports applicant documents.',
            'LEVEL_1_USER': 'Handles assigned applicant queues, initial review, and applicant document exports.',
            'UNASSIGNED': 'This account needs a role before normal applicant workflow access is available.',
        }
        role_tasks = {
            'SUPER_ADMIN': ['Audit access changes', 'Review active sessions', 'Manage system roles'],
            'ADMIN': ['Review pending queues', 'Forward applicants', 'Monitor team workload'],
            'LEVEL_2_USER': ['Review escalated applicants', 'Export applicant files', 'Update review notes'],
            'LEVEL_1_USER': ['Check assigned applicants', 'Download CVs', 'Mark initial review progress'],
            'UNASSIGNED': ['Contact an administrator', 'Complete profile setup', 'Wait for role assignment'],
        }

        user_permissions = get_user_permissions(current_user)
        assigned_positions = sorted(
            {position.title for position in list(current_user.assigned_positions) + list(current_user.primary_assigned_positions)}
        )
        visible_query = visible_applicants_query()
        assigned_count = visible_query.count()
        pending_count = visible_query.filter(Applicant.remarked_by_id.is_(None)).count()
        reviewed_count = len(current_user.remarked_applicants)
        forwarded_count = ApplicantForward.query.filter_by(from_employee_id=current_user.id).count()
        is_profile_analytics_user = role_name in PROFILE_ANALYTICS_LAYOUT_ROLES
        has_profile_todos = role_name in PROFILE_TODO_ROLES
        if role_name in PROFILE_ANALYTICS_ROLES:
            analytics = profile_analytics_payload(profile_analytics_filters())
        elif role_name in PROFILE_ANALYTICS_ADMIN_ROLES:
            analytics = aggregate_level_user_profile_analytics(profile_analytics_filters())
        else:
            analytics = None
        team_label = profile_team_for(current_user.id)

        profile_items = [
            bool(current_user.username),
            bool(current_user.email),
            bool(current_user.profile_data),
            bool(current_user.role_id),
            bool(assigned_positions) or role_name in {'SUPER_ADMIN', 'ADMIN'},
        ]
        profile_completion = round((sum(1 for item in profile_items if item) / len(profile_items)) * 100)

        mock_activity = [
            {'label': 'Last login', 'value': current_user.last_login},
            {'label': 'Session started', 'value': current_user.session_started_at},
            {'label': 'Last seen', 'value': current_user.last_seen_at},
            {'label': 'Account created', 'value': current_user.created_at},
        ]

        return render_template(
            'profile.html',
            is_profile_page=True,
            role_name=role_name,
            role_label=role_labels.get(role_name, role_name.replace('_', ' ').title()),
            role_description=role_descriptions.get(role_name, 'Role-based access profile.'),
            role_tasks=role_tasks.get(role_name, []),
            permission_keys=user_permissions['permissions'],
            assigned_positions=assigned_positions,
            profile_completion=profile_completion,
            profile_stats={
                'assigned_count': assigned_count,
                'pending_count': pending_count,
                'reviewed_count': reviewed_count,
                'forwarded_count': forwarded_count,
            },
            mock_activity=mock_activity,
            is_profile_analytics_user=is_profile_analytics_user,
            show_movement_analytics=role_name in PROFILE_ANALYTICS_ADMIN_ROLES,
            has_profile_todos=has_profile_todos,
            profile_todos=profile_todos_for(current_user.id) if has_profile_todos else [],
            analytics=analytics,
            team_label=team_label,
        )

    @app.route('/profile-picture')
    @login_required
    def profile_picture():
        if not current_user.profile_data:
            abort(404)
        return send_file(
            BytesIO(current_user.profile_data),
            mimetype=current_user.profile_content_type or 'application/octet-stream',
            as_attachment=False,
            download_name=current_user.profile_filename or 'profile',
        )

    @app.route('/profile/analytics/export')
    @login_required
    def export_profile_analytics():
        role_name = current_user_role_name()
        if role_name not in PROFILE_ANALYTICS_LAYOUT_ROLES:
            abort(403)

        filters = profile_analytics_filters()
        if role_name in PROFILE_ANALYTICS_ADMIN_ROLES:
            analytics = aggregate_level_user_profile_analytics(filters)
        else:
            analytics = profile_analytics_payload(filters)
        generated_at = ph_now()

        pdf = build_profile_analytics_pdf(analytics, filters, role_name, profile_team_for(current_user.id))
        username = secure_filename(current_user.username or 'user') or 'user'
        filename = f'profile_analytics_{username}_{generated_at.strftime("%Y%m%d")}.pdf'
        return send_file(
            pdf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename,
        )

    @app.route('/dashboard.html')
    @login_required
    def dashboard():
        if not has_permission(current_user, 'view_dashboard') or not has_permission(current_user, 'view_applicants'):
            flash('You do not have permission to view the dashboard.', 'error')
            return redirect(url_for('employee_home'))

        job_positions_query = visible_applicants_query().with_entities(Applicant.job_position)

        job_positions = [
            r[0] for r in job_positions_query
            .distinct()
            .order_by(Applicant.job_position.asc())
            .all()
            if r[0]
        ]

        filters = dashboard_filters()
        try:
            page = int(request.args.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        per_page = 15

        query = filtered_applicants_query(filters)
        can_forward_applicants = has_permission(current_user, 'forward_applicant')
        can_delete_applicants = has_permission(current_user, 'delete_applicant')
        can_export_applicant_cv = has_permission(current_user, 'export_applicant_cv')
        can_export_applicant_excel = has_permission(current_user, 'export_applicant_excel')
        forward_users = []
        if can_forward_applicants:
            forward_users_query = Employee.query.filter(
                Employee.is_active == True,
                Employee.is_deleted == False,
                Employee.id != current_user.id,
            )
            if current_user_role_name() in {'LEVEL_1_USER', 'LEVEL_2_USER'}:
                forward_users_query = forward_users_query.filter(
                    Employee.role_obj.has(Role.name.in_(['LEVEL_1_USER', 'LEVEL_2_USER']))
                )
            forward_users = forward_users_query.order_by(Employee.username.asc()).all()

        total_count = query.count()
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        # Ensure page is within valid range
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages

        applicants = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Always ensure vars passed (template safe)
        total_pages = total_pages or 1
        total_count = total_count or 0
        
        return render_template(
            'dashboard.html',
            applicants=applicants,
            job_positions=job_positions,
            filters=filters,
            page=page,
            total_pages=total_pages,
            total_count=total_count,
            is_profile_page=False,
            can_forward_applicants=can_forward_applicants,
            can_delete_applicants=can_delete_applicants,
            can_export_applicant_cv=can_export_applicant_cv,
            can_export_applicant_excel=can_export_applicant_excel,
            forward_users=forward_users,
        )

    @app.route('/applicants/<int:applicant_id>/cv')
    @login_required
    def download_applicant_cv(applicant_id):
        if not has_permission(current_user, 'export_applicant_cv'):
            abort(403)

        applicant = visible_applicants_query().filter(Applicant.id == applicant_id).first_or_404()
        if not applicant.cv_data:
            abort(404)
        filename = applicant.cv_filename or f'applicant_{applicant_id}.pdf'
        return send_file(
            BytesIO(applicant.cv_data),
            mimetype=applicant.cv_content_type or 'application/pdf',
            as_attachment=True,
            download_name=filename,
        )

    @app.route('/applicants/<int:applicant_id>/remark', methods=['POST'])
    @login_required
    def remark_applicant(applicant_id):
        applicant = visible_applicants_query().filter(Applicant.id == applicant_id).first_or_404()

        if applicant.remarked_by_id and applicant.remarked_by_id != current_user.id:
            owner = applicant.remarked_by.username if applicant.remarked_by else 'another user'
            flash(f'This applicant is already remarked by {owner}.', 'error')
            return redirect(request.referrer or url_for('dashboard'))

        if not applicant.remarked_by_id:
            applicant.remarked_by_id = current_user.id
            applicant.remarked_at = ph_now()
            if applicant.status not in APPLICANT_REMARK_STATUSES:
                applicant.status = APPLICANT_REMARK_STATUSES[0]
            db.session.commit()
            flash('Applicant remark added.', 'success')
        else:
            flash('You already remarked this applicant.', 'info')

        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/applicants/<int:applicant_id>/remark/undo', methods=['POST'])
    @login_required
    def undo_applicant_remark(applicant_id):
        applicant = visible_applicants_query().filter(Applicant.id == applicant_id).first_or_404()

        if not applicant.remarked_by_id:
            flash('This applicant has no remark to undo.', 'info')
            return redirect(request.referrer or url_for('dashboard'))

        if applicant.remarked_by_id != current_user.id and current_user_role_name() not in {'SUPER_ADMIN', 'ADMIN'}:
            flash('Only the user who added the remark, ADMIN, or SUPERADMIN can undo it.', 'error')
            return redirect(request.referrer or url_for('dashboard'))

        applicant.remarked_by_id = None
        applicant.remarked_at = None
        applicant.status = APPLICANT_OPEN_STATUS
        db.session.commit()
        flash('Applicant remark undone.', 'success')

        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/applicants/<int:applicant_id>/status', methods=['POST'])
    @login_required
    def update_applicant_status(applicant_id):
        applicant = visible_applicants_query().filter(Applicant.id == applicant_id).first_or_404()
        status = (request.form.get('status') or '').strip()

        if status not in APPLICANT_REMARK_STATUSES:
            flash('Select a valid applicant status.', 'error')
            return redirect(request.referrer or url_for('dashboard'))

        if not applicant.remarked_by_id:
            flash('Add a remark before changing status.', 'error')
            return redirect(request.referrer or url_for('dashboard'))

        if applicant.remarked_by_id != current_user.id and not is_super_admin():
            owner = applicant.remarked_by.username if applicant.remarked_by else 'another user'
            flash(f'This applicant is already remarked by {owner}.', 'error')
            return redirect(request.referrer or url_for('dashboard'))

        applicant.status = status
        db.session.commit()
        flash('Applicant status updated.', 'success')
        return redirect(request.referrer or url_for('dashboard'))

    @app.route('/applicants/batch-delete', methods=['POST'])
    @login_required
    def batch_delete_applicants():
        if not has_permission(current_user, 'delete_applicant'):
            flash('You do not have permission to delete applicants.', 'error')
            return redirect(url_for('dashboard'))

        applicant_ids = selected_applicant_ids()

        if not applicant_ids:
            flash('Please select applicant to delete.', 'error')
            return redirect(url_for('dashboard'))

        query = accessible_applicants_query().filter(Applicant.id.in_(applicant_ids))

        if is_super_admin():
            deleted = query.update(
                {
                    'is_deleted': True,
                    'deleted_at': ph_now(),
                    'deleted_by_id': current_user.id,
                },
                synchronize_session=False
            )
            db.session.commit()
            flash(f'Deleted {deleted} applicant(s) across all dashboards. They can be restored by SUPERADMIN.', 'success')
            return redirect(url_for('dashboard'))

        accessible_ids = [row[0] for row in query.with_entities(Applicant.id).all()]
        if not accessible_ids:
            flash('No matching applicants found.', 'error')
            return redirect(url_for('dashboard'))

        existing_hidden_ids = {
            row[0] for row in db.session.query(ApplicantDashboardDeletion.applicant_id)
            .filter(
                ApplicantDashboardDeletion.employee_id == current_user.id,
                ApplicantDashboardDeletion.applicant_id.in_(accessible_ids),
            )
            .all()
        }
        hidden_count = 0
        for applicant_id in accessible_ids:
            if applicant_id in existing_hidden_ids:
                continue
            db.session.add(ApplicantDashboardDeletion(
                applicant_id=applicant_id,
                employee_id=current_user.id,
            ))
            hidden_count += 1

        db.session.commit()
        flash(f'Removed {hidden_count} applicant(s) from your dashboard.', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/applicants/forward', methods=['POST'])
    @login_required
    def forward_applicants():
        if not has_permission(current_user, 'forward_applicant'):
            flash('You do not have permission to forward applicants.', 'error')
            return redirect(url_for('dashboard'))

        ids = request.form.getlist('applicant_ids')
        try:
            applicant_ids = [int(x) for x in ids]
        except Exception:
            applicant_ids = []

        target_user_id = request.form.get('target_user_id', type=int)
        target_user = Employee.query.filter_by(id=target_user_id, is_active=True).first() if target_user_id else None

        if not applicant_ids:
            flash('Select applicants to forward.', 'error')
            return redirect(url_for('dashboard'))
        if not target_user or target_user.id == current_user.id:
            flash('Select a valid user to forward to.', 'error')
            return redirect(url_for('dashboard'))

        accessible_ids = [
            row[0] for row in accessible_applicants_query()
            .filter(Applicant.id.in_(applicant_ids))
            .with_entities(Applicant.id)
            .all()
        ]

        if not accessible_ids:
            flash('No matching applicants found.', 'error')
            return redirect(url_for('dashboard'))

        remarked_count = accessible_applicants_query().filter(
            Applicant.id.in_(accessible_ids),
            Applicant.remarked_by_id.isnot(None),
        ).count()
        if remarked_count:
            flash('Remove remarks before forwarding selected applicants.', 'error')
            return redirect(url_for('dashboard'))

        existing_forward_ids = {
            row[0] for row in db.session.query(ApplicantForward.applicant_id)
            .filter(
                ApplicantForward.to_employee_id == target_user.id,
                ApplicantForward.applicant_id.in_(accessible_ids),
            )
            .all()
        }

        forwarded_count = 0
        for applicant_id in accessible_ids:
            if applicant_id in existing_forward_ids:
                continue
            db.session.add(ApplicantForward(
                applicant_id=applicant_id,
                from_employee_id=current_user.id,
                to_employee_id=target_user.id,
            ))
            forwarded_count += 1

        if forwarded_count:
            ApplicantDashboardDeletion.query.filter(
                ApplicantDashboardDeletion.employee_id == target_user.id,
                ApplicantDashboardDeletion.applicant_id.in_(accessible_ids),
            ).delete(synchronize_session=False)

        notification_count = len(accessible_ids)
        notification_message = (
            f'{current_user.username} forwarded you an Applicant.'
            if notification_count == 1
            else f'{current_user.username} forwarded you {notification_count} Applicants.'
        )
        db.session.add(Announcement(
            title='Applicant Forwarded',
            message=notification_message,
            created_by_id=current_user.id,
            recipient_employee_id=target_user.id,
        ))

        db.session.commit()
        flash(f'Forwarded {forwarded_count} applicant(s) to {target_user.username}.', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/api/applicants/deleted', methods=['GET'])
    @login_required
    def api_deleted_applicants():
        if not is_super_admin():
            return {'error': 'Only SUPERADMIN can view deleted applicants'}, 403

        applicants = Applicant.query.filter(Applicant.is_deleted == True).order_by(Applicant.deleted_at.desc()).all()
        return {
            'applicants': [{
                'id': applicant.id,
                'full_name': applicant.full_name,
                'email': applicant.email,
                'job_position': applicant.job_position,
                'deleted_at': applicant.deleted_at.isoformat() if applicant.deleted_at else None,
                'deleted_by': applicant.deleted_by.username if applicant.deleted_by else None,
            } for applicant in applicants]
        }

    @app.route('/api/applicants/<int:applicant_id>/restore', methods=['POST'])
    @login_required
    def api_restore_applicant(applicant_id):
        if not is_super_admin():
            return {'error': 'Only SUPERADMIN can restore applicants'}, 403

        applicant = Applicant.query.filter_by(id=applicant_id, is_deleted=True).first_or_404()
        applicant.is_deleted = False
        applicant.deleted_at = None
        applicant.deleted_by_id = None
        db.session.commit()
        return {'message': 'Applicant restored successfully'}

    @app.route('/applicants/batch-export-cv', methods=['POST'])
    @login_required
    def batch_export_cvs():
        if not has_permission(current_user, 'export_applicant_cv'):
            flash('You do not have permission to export applicant CVs.', 'error')
            return redirect(url_for('dashboard'))

        applicant_ids = selected_applicant_ids()

        if not applicant_ids:
            flash('Please select applicant to export CV.', 'error')
            return redirect(url_for('dashboard'))

        applicants = visible_applicants_query().filter(Applicant.id.in_(applicant_ids)).order_by(Applicant.applied_at.desc()).all()
        buf = BytesIO()
        exported = 0

        with ZipFile(buf, mode='w', compression=ZIP_DEFLATED) as zf:
            for a in applicants:
                if not a.cv_data:
                    continue
                base = secure_filename(a.cv_filename or f'applicant_{a.id}.pdf')
                if not base.lower().endswith('.pdf'):
                    base = base + '.pdf'
                zf.writestr(base, a.cv_data)
                exported += 1

        if exported == 0:
            flash('No CV PDFs found for selected applicants.', 'error')
            return redirect(url_for('dashboard'))

        buf.seek(0)
        filename = f'cvs_{ph_now().strftime("%Y%m%d_%H%M%S")}.zip'
        return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=filename)

    @app.route('/applicants/export-excel', methods=['POST'])
    @login_required
    def export_applicants_excel():
        if not has_permission(current_user, 'export_applicant_excel'):
            flash('You do not have permission to export applicants to Excel.', 'error')
            return redirect(url_for('dashboard'))

        applicant_ids = selected_applicant_ids()
        if not applicant_ids:
            flash('Please select applicant to export Excel.', 'error')
            return redirect(url_for('dashboard'))

        applicants = visible_applicants_query().filter(Applicant.id.in_(applicant_ids)).order_by(Applicant.applied_at.desc()).all()
        headers = [
            'Timestamp',
            'Fullname',
            'Position',
            'E-mail',
            'Contact number',
            'Age',
            'Birth date',
            'Gender',
            'Status',
        ]
        rows = []
        for applicant in applicants:
            remark_owner = applicant.remarked_by.username if applicant.remarked_by else None
            rows.append([
                applicant.applied_at.strftime('%m/%d/%Y %I:%M %p') if applicant.applied_at else '',
                applicant.full_name,
                applicant.job_position,
                applicant.email,
                applicant.contact_number,
                applicant.age or '',
                applicant.birth_date.strftime('%m/%d/%Y') if applicant.birth_date else '',
                applicant.gender or '',
                applicant.status if remark_owner else APPLICANT_OPEN_STATUS,
            ])

        workbook = build_xlsx(headers, rows)
        filename = f'applicants_{ph_now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return send_file(
            workbook,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename,
        )

    # logout moved to routes_auth.py for RBAC audit logging

    @app.route('/admin-panel.html')
    @login_required
    @require_permission('access_admin_panel')
    def admin_panel():
        """RBAC Admin Panel - requires access_admin_panel permission"""
        return render_template('admin_panel.html', is_admin_page=True)

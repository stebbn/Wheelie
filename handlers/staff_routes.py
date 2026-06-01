from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash

import modules.database as database
from modules.auth import role_required

staff_bp = Blueprint('staff', __name__, template_folder='templates')

@staff_bp.route('/staff')
@role_required('admin')
def staff_list():
    staff_members = database.get().get_all_staff()
    return render_template('staff.html', staff_members=staff_members, current_staff_id=session.get("staff_id"))


@staff_bp.route('/staff/new', methods=['GET', 'POST'])
@role_required('admin')
def new_staff():
    if request.method == 'POST':
        data = {
            'username': request.form.get('username'),
            'password_hash': generate_password_hash(request.form.get('password')),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'role': request.form.get('role'),
            'contact_number': request.form.get('contact_number')
        }
        sid = database.get().create_staff(data)
        database.get().log_action(session.get("staff_id"), "create", "staff", sid)
        return redirect(url_for('staff.staff_list'))

    return render_template('forms/staff_form.html', staff_member=None)


@staff_bp.route('/staff/<int:sid>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_staff(sid):
    staff_member = database.get().get_staff(sid)
    if not staff_member:
        return redirect(url_for('staff.staff_list'))

    if request.method == 'POST':
        status = request.form.get('status')
        if sid == session.get("staff_id") and status != "active":
            status = "active"

        data = {
            'username': request.form.get('username'),
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'role': request.form.get('role'),
            'contact_number': request.form.get('contact_number'),
            'status': status
        }
        database.get().update_staff(sid, data)

        if request.form.get('password'):
            database.get().update_staff_password(sid, generate_password_hash(request.form.get('password')))

        database.get().log_action(session.get("staff_id"), "update", "staff", sid)
        return redirect(url_for('staff.staff_list'))

    return render_template('forms/staff_form.html', staff_member=staff_member)

@staff_bp.route('/staff/<int:sid>/toggle', methods=['POST'])
@role_required('admin')
def toggle_staff(sid):
    staff_member = database.get().get_staff(sid)
    if not staff_member:
        return redirect(url_for('staff.staff_list'))

    next_status = "inactive" if staff_member["status"] == "active" else "active"
    if sid == session.get("staff_id") and next_status == "inactive":
        return redirect(url_for('staff.staff_list'))

    database.get().toggle_staff_status(sid, next_status)
    database.get().log_action(session.get("staff_id"), "update", "staff", sid)
    return redirect(url_for('staff.staff_list'))

import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from werkzeug.utils import secure_filename
import modules.database as database

from modules.auth import login_required
from modules.appFileHandler import resource_path

customers_bp = Blueprint('customers', __name__, template_folder='templates')

@customers_bp.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    customers_list = database.get().get_all_customers(search)
    return render_template('customers.html', customers=customers_list, search=search)

def _save_valid_id(file):
    if not file or not file.filename:
        return None
    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename)
    stored_name = f"{uuid.uuid4().hex}{ext}"

    id_path = f"{current_app.config["UPLOAD_FOLDER"]}/{stored_name}"

    file_path = resource_path(id_path)
    file.save(file_path)

    return id_path

@customers_bp.route('/customer/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if request.method == 'POST':
        valid_id_path = _save_valid_id(request.files.get("valid_id"))
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'contact_number': request.form.get('contact_number'),
            'email': request.form.get('email'),
            'staff_id': session.get("staff_id"),
            'valid_id': valid_id_path
        }
        cid = database.get().create_customer(data)
        database.get().log_action(session.get("staff_id"), "create", "customer", cid)
        return redirect(url_for('customers.customer_detail', cid=cid))
    return render_template('forms/customer_form.html', customer=None)

@customers_bp.route('/customer/<int:cid>', methods=['GET', 'POST'])
@login_required
def customer_detail(cid):
    customer = database.get().get_customer(cid)
    if not customer:
        return redirect(url_for('customers.customers'))
    if request.method == 'POST':
        valid_id_path = _save_valid_id(request.files.get("valid_id")) or (customer["valid_id"] if customer else None)
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'contact_number': request.form.get('contact_number'),
            'email': request.form.get('email'),
            'valid_id': valid_id_path
        }
        database.get().update_customer(cid, data)
        database.get().log_action(session.get("staff_id"), "update", "customer", cid)
        return redirect(url_for('customers.customer_detail', cid=cid))
    
    rentals = database.get().get_customer_rentals(cid)
    stats = database.get().get_customer_stats(cid)
    return render_template('customer_detail.html', customer=customer, rentals=rentals, stats=stats)

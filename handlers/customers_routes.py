from flask import Blueprint, render_template, request, redirect, url_for
import modules.database as database

customers_bp = Blueprint('customers', __name__, template_folder='templates')

@customers_bp.route('/customers')
def customers():
    search = request.args.get('search', '')
    customers_list = database.get().get_all_customers(search)
    return render_template('customers.html', customers=customers_list, search=search)

@customers_bp.route('/customer/new', methods=['GET', 'POST'])
def new_customer():
    if request.method == 'POST':
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'contact_number': request.form.get('contact_number'),
            'email': request.form.get('email') or None
        }
        cid = database.get().create_customer(data)
        return redirect(url_for('customers.customer_detail', cid=cid))
    return render_template('forms/customer_form.html', customer=None)

@customers_bp.route('/customer/<int:cid>', methods=['GET', 'POST'])
def customer_detail(cid):
    if request.method == 'POST':
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'contact_number': request.form.get('contact_number'),
            'email': request.form.get('email') or None
        }
        database.get().update_customer(cid, data)
        return redirect(url_for('customers.customer_detail', cid=cid))
    
    customer = database.get().get_customer(cid)
    rentals = database.get().get_customer_rentals(cid)
    stats = database.get().get_customer_stats(cid)
    return render_template('forms/customer_form.html', customer=customer, rentals=rentals, stats=stats)

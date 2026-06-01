from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import modules.database as database
from modules.auth import login_required

rentals_bp = Blueprint('rentals', __name__, template_folder='templates')

@rentals_bp.route('/rentals')
@login_required
def rentals():
    status = request.args.get('status', 'all')
    rentals_list = database.get().get_all_rentals(status)
    customers_list = database.get().get_all_customers()
    bikes = database.get().get_available_bikes()
    return render_template('rentals.html', rentals=rentals_list, filter_status=status, customers=customers_list, bikes=bikes)

@rentals_bp.route('/rental/new', methods=['GET', 'POST'])
@login_required
def new_rental():
    if request.method == 'POST':
        bike = database.get().get_bike(request.form.get('bike_id'))
        if not bike:
            return jsonify({'success': False, 'message': 'Bike not found.'}), 400
        data = {
            'customer_id': request.form.get('customer_id'),
            'bike_id': request.form.get('bike_id'),
            'staff_id': session.get("staff_id"),
            'rental_rate': bike["bike_rate"]
        }
        rid = database.get().create_rental(data)
        database.get().log_action(session.get("staff_id"), "create", "rental", rid)
       
        return jsonify({'success': True, 'message': 'Rental created successfully!', 'redirect_url': url_for('rentals.rental_detail', rid=rid)})
    
    customers_list = database.get().get_all_customers()
    bikes = database.get().get_available_bikes()
    return render_template('forms/rental_form.html', customers=customers_list, bikes=bikes, rental=None)

@rentals_bp.route('/rental/<int:rid>', methods=['GET', 'POST'])
@login_required
def rental_detail(rid):
    if request.method == 'POST':
        totals = database.get().return_rental(rid)
        if not totals:
            return redirect(url_for('rentals.rentals'))
        
        payment_data = {
            'rental_id': rid,
            'amount_paid': totals["total_amount"],
            'payment_method': request.form.get('payment_method')
        }
        payment_id = database.get().create_payment(payment_data)
        database.get().log_action(session.get("staff_id"), "return", "rental", rid)
        database.get().log_action(session.get("staff_id"), "create", "payment", payment_id)
        return redirect(url_for('rentals.rental_detail', rid=rid))

    rental = database.get().get_rental(rid)
    payment = database.get().get_payment_for_rental(rid)
    return render_template('rental_detail.html', rental=rental, payment=payment)

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import modules.database as database

rentals_bp = Blueprint('rentals', __name__, template_folder='templates')

@rentals_bp.route('/rentals')
def rentals():
    status = request.args.get('status', 'all')
    rentals_list = database.get().get_all_rentals(status)
    # Fetch data needed for the new rental modal form
    customers_list = database.get().get_all_customers()
    bikes = database.get().get_available_bikes()
    return render_template('rentals.html', rentals=rentals_list, filter_status=status, customers=customers_list, bikes=bikes)

@rentals_bp.route('/rental/new', methods=['GET', 'POST'])
def new_rental():
    if request.method == 'POST':
        data = {
            'customer_id': request.form.get('customer_id'),
            'bike_id': request.form.get('bike_id'),
            'staff_id': 1, 
            'rental_start': request.form.get('rental_start'),
            'rental_rate': request.form.get('rental_rate'),
            'notes': request.form.get('notes') or None
        }
        rid = database.get().create_rental(data)
       
        return jsonify({'success': True, 'message': 'Rental created successfully!', 'redirect_url': url_for('rentals.rental_detail', rid=rid)})
    
    customers_list = database.get().get_all_customers()
    bikes = database.get().get_available_bikes()
    return render_template('forms/rental_form.html', customers=customers_list, bikes=bikes, rental=None)

@rentals_bp.route('/rental/<int:rid>', methods=['GET', 'POST'])
def rental_detail(rid):
    if request.method == 'POST':
        rental_end = request.form.get('rental_end')
        total_amount = request.form.get('total_amount')
        database.get().return_rental(rid, rental_end, total_amount)
        
        # Record payment
        payment_data = {
            'rental_id': rid,
            'amount_paid': total_amount,
            'payment_method': request.form.get('payment_method')
        }
        database.get().create_payment(payment_data)
        return redirect(url_for('rentals.rentals'))
    
    rental = database.get().get_rental(rid)
    payment = database.get().get_payment_for_rental(rid)
    return render_template('rental_detail.html', rental=rental, payment=payment)

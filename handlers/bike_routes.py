from flask import Blueprint, render_template, request, redirect, url_for, session
import modules.database as database
from modules.auth import login_required

bikes_bp = Blueprint('bikes', __name__, template_folder='templates')

@bikes_bp.route('/bikes')
@login_required
def registry():
    search = request.args.get('search', '')
    status = request.args.get('status', 'all')
    all_bikes = database.get().get_all_bikes(search, status)
    next_bike_code = database.get().get_next_bike_code()
    return render_template('bike_registry.html', bikes=all_bikes, search=search, filter_status=status, next_bike_code=next_bike_code)

@bikes_bp.route('/bike/<int:bid>')
@login_required
def bike_detail(bid):
    bike = database.get().get_bike(bid)
    current_renter = None
    if bike and bike['status'] == 'rented':
        current_renter = database.get().get_current_renter_for_bike(bid)
    return render_template('bike_detail.html', bike=bike, current_renter=current_renter)

@bikes_bp.route('/bike/new', methods=['GET', 'POST'])
@login_required
def new_bike():
    next_bike_code = database.get().get_next_bike_code()
    if request.method == 'POST':
        data = {
            'bike_code': database.get().get_next_bike_code(),
            'brand': request.form.get('brand'),
            'model': request.form.get('model'),
            'size': request.form.get('size'),
            'color': request.form.get('color'),
            'bike_rate': request.form.get('bike_rate'),
            'type': request.form.get('type')
        }
        bid = database.get().create_bike(data)
        database.get().log_action(session.get("staff_id"), "create", "bike", bid)
        return redirect(url_for('bikes.bike_detail', bid=bid))
    return render_template('forms/bike_form.html', bike=None, next_bike_code=next_bike_code)

@bikes_bp.route('/bike/<int:bid>/edit', methods=['GET', 'POST'])
@login_required
def edit_bike(bid):
    bike = database.get().get_bike(bid)
    if bike and bike.get("status") in ("rented", "retired"):
        return redirect(url_for('bikes.bike_detail', bid=bid))
    if request.method == 'POST':
        data = {
            'bike_code': request.form.get('bike_code'),
            'brand': request.form.get('brand'),
            'model': request.form.get('model'),
            'color': request.form.get('color'),
            'bike_rate': request.form.get('bike_rate'),
            'type': request.form.get('type')
        }
        database.get().update_bike(bid, data)
        database.get().log_action(session.get("staff_id"), "update", "bike", bid)
        return redirect(url_for('bikes.bike_detail', bid=bid))
    return render_template('forms/bike_form.html', bike=bike)

@bikes_bp.route('/bike/<int:bid>/retire', methods=['POST'])
@login_required
def retire_bike(bid):
    success, message = database.get().retire_bike(bid)
    if success:
        database.get().log_action(session.get("staff_id"), "retire", "bike", bid)
    return redirect(url_for('bikes.bike_detail', bid=bid))
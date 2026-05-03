from flask import Blueprint, render_template, request, redirect, url_for
import modules.database as database

maintenance_bp = Blueprint('maintenance', __name__, template_folder='templates')

@maintenance_bp.route('/maintenance')
def maintenance():
    maintenance_list = database.get().get_all_maintenance()
    return render_template('maintenance.html', maintenance=maintenance_list)

@maintenance_bp.route('/maintenance/new', methods=['GET', 'POST'])
def new_maintenance():
    if request.method == 'POST':
        data = {
            'bike_id': request.form.get('bike_id'),
            'staff_id': 1,  # Default to admin user
            'maintenance_date': request.form.get('maintenance_date'),
            'maintenance_type': request.form.get('maintenance_type'),
            'description': request.form.get('description'),
            'outcome': request.form.get('outcome')
        }
        mid = database.get().create_maintenance(data)
        return redirect(url_for('maintenance.maintenance_detail', mid=mid))
    
    bikes = database.get().get_bikes_for_maintenance()
    return render_template('forms/maintenance_form.html', bikes=bikes, maintenance=None)

@maintenance_bp.route('/maintenance/<int:mid>', methods=['GET', 'POST'])
def maintenance_detail(mid):
    if request.method == 'POST':
        data = {
            'maintenance_type': request.form.get('maintenance_type'),
            'description': request.form.get('description'),
            'outcome': request.form.get('outcome')
        }
        database.get().update_maintenance(mid, data)
        return redirect(url_for('maintenance.maintenance'))

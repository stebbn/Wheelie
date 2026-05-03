from flask import Blueprint, render_template
import modules.database as database

payments_bp = Blueprint('payments', __name__, template_folder='templates')

@payments_bp.route('/payments')
def payments():
    payments_list = database.get().get_all_payments()
    return render_template('payments.html', payments=payments_list)

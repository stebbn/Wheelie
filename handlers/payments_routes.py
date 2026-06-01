from flask import Blueprint, render_template
import modules.database as database
from modules.auth import login_required

payments_bp = Blueprint('payments', __name__, template_folder='templates')

@payments_bp.route('/payments')
@login_required
def payments():
    payments_list = database.get().get_all_payments()
    return render_template('payments.html', payments=payments_list)

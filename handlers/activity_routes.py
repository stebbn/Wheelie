from flask import Blueprint, render_template

import modules.database as database
from modules.auth import role_required


activity_bp = Blueprint('activity', __name__, template_folder='templates')


@activity_bp.route('/activity-log')
@role_required('admin')
def activity_log():
    logs = database.get().get_activity_log()
    return render_template('activity_log.html', logs=logs)

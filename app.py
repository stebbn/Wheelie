import os
import webview

from flask import Flask, render_template, request, redirect, url_for, session

from screeninfo import get_monitors
import modules.database as database
from modules.auth import current_staff, login_required
from modules.appFileHandler import resource_path
from modules.utils import play_sound

from handlers.bike_routes import bikes_bp
from handlers.customers_routes import customers_bp
from handlers.rentals_routes import rentals_bp
from handlers.payments_routes import payments_bp
from handlers.staff_routes import staff_bp
from handlers.activity_routes import activity_bp

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000
app.secret_key = os.environ.get("SECRET_KEY", "wheelie-dev-secret")
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads", "ids")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

database.init()

app.register_blueprint(bikes_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(rentals_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(activity_bp)

def get_sidebar_state():
    return request.cookies.get('sidebarState') == 'expanded'

@app.context_processor
def inject_sidebar_state():
    return dict(sidebar_expanded=get_sidebar_state())

@app.context_processor
def inject_current_staff():
    staff = current_staff()
    return dict(current_staff=staff, is_admin=staff and staff.get("role") == "admin")

@app.route('/', methods=['GET', 'POST'])
def login():
    if session.get("staff_id"):
        return redirect(url_for('home'))
    if request.method == 'POST':
        form_username = request.form.get('username')
        form_password = request.form.get('password')

        user = database.get().get_staff_by_username(form_username)
        if user and database.get().verify_user(form_username, form_password):
            session.clear()
            session["staff_id"] = user["staff_id"]
            session["username"] = user["username"]
            session["first_name"] = user["first_name"]
            session["last_name"] = user["last_name"]
            session["role"] = user["role"]
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/home')
@login_required
def home():
    stats = database.get().get_dashboard_stats()
    return render_template('home.html', stats=stats)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':

    monitor = get_monitors()[0] 
    screen_width = monitor.width
    screen_height = monitor.height

    window_width = 1200
    window_height = 850

    x_pos = (screen_width - window_width) // 2
    y_pos = (screen_height - window_height) // 2

    def onLoaded():
        window.events.loaded -= onLoaded
        play_sound("sounds/bellring.wav", 0.1)

    window = webview.create_window('Wheelie', app, width=window_width, height=window_height, x=x_pos, y=y_pos, resizable=True)
    window.events.loaded += onLoaded
    webview.start(debug=False)
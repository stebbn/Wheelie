import webview
from flask import Flask, render_template, request, redirect, url_for

from screeninfo import get_monitors
import modules.database as database

from handlers.bike_routes import bikes_bp
from handlers.customers_routes import customers_bp
from handlers.rentals_routes import rentals_bp
from handlers.payments_routes import payments_bp
from handlers.maintenance_routes import maintenance_bp

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000

database.init()

app.register_blueprint(bikes_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(rentals_bp)
app.register_blueprint(payments_bp)
app.register_blueprint(maintenance_bp)

def get_sidebar_state():
    return request.cookies.get('sidebarState') == 'expanded'

@app.context_processor
def inject_sidebar_state():
    return dict(sidebar_expanded=get_sidebar_state())

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('home')) # bypass login muna

        form_username = request.form.get('username')
        form_password = request.form.get('password')

        if database.get().verify_user(form_username, form_password):
            print("Login successful!")
            return redirect(url_for('home'))
        else:
            print("Login failed: Incorrect username or password.")
            return render_template('login.html', error="Invalid credentials")

    return render_template('login.html')

@app.route('/home')
def home():
    stats = database.get().get_dashboard_stats()
    return render_template('home.html', stats=stats)

if __name__ == '__main__':

    monitor = get_monitors()[0] 
    screen_width = monitor.width
    screen_height = monitor.height

    window_width = 1200
    window_height = 850

    x_pos = (screen_width - window_width) // 2
    y_pos = (screen_height - window_height) // 2

    window = webview.create_window('Wheelie', app, width=window_width, height=window_height, x=x_pos, y=y_pos, resizable=True)
    webview.start()
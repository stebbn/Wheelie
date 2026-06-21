# Wheelie 

A Bike rental management system.

## Features

* **Interactive Dashboard:** View real-time statistics including active rentals, overdue rentals, available bikes, and today's revenue.


* **Fleet Management (Bikes):** Maintain a bike registry where you can add, edit, or retire bikes. Track details such as the bike code, brand, model, type, color, and hourly rate.


* **Customer Database:** Add new customers with their names, contact numbers, emails, and optional uploaded valid IDs. View customer-specific statistics like total rentals and total amount spent.


* **Rental Operations:** Process new rentals by assigning a customer to an available bike and setting a planned return date. Process returns to automatically calculate the amount due based on the hourly rate.


* **Payment Processing:** Record payments and assign payment methods, including cash, GCash, or card.


* **Staff Management:** Add and manage staff accounts with specific roles (`admin` or `cashier`) and active/inactive statuses.


* **Activity Logging:** Administrators can monitor an activity log that records timestamps, staff names, roles, actions taken, and target tables.


* **Desktop Integration:** The application runs in a dedicated desktop window utilizing `pywebview`


## Tech Stack & Requirements

The project relies on the following Python packages:

* **Flask**: Serves the backend and HTML templates.

* **webview**: Renders the web application as a standalone desktop window.

* **screeninfo**: Used to center the application window on the user's monitor.

* **werkzeug**: Handles security and password hashing.

* **SQLite3**: Powers the local database (`data/database.db`).



## 🔑 Default Credentials

Upon initializing the system, you can log in using the default administrator account:

* **Username:** `admin`

* **Password:** `123`
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

import modules.appFileHandler as appFileHandler

DB_PATH = appFileHandler.resource_path("modules/database.db")
db = None

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._create_tables()
        self._mockstaff()

    def _mockstaff(self):
        user = self.conn.execute("SELECT * FROM staff WHERE username = ?", ('admin',)).fetchone()
        if not user:
            password_hash = generate_password_hash('123')
            self.conn.execute(
                """INSERT INTO staff (username, password_hash, first_name, last_name, role, contact_number, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ('admin', password_hash, 'Admin', 'User', 'admin', '09123456789', 'active')
            )
            self.conn.commit()

    def _create_tables(self):
        
        self.conn.executescript(""" 
        CREATE TABLE IF NOT EXISTS staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN('admin','cashier','mechanic')),
            contact_number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','inactive')),
            created_at DATETIME NOT NULL DEFAULT(datetime('now','localtime'))
        );
                                
        CREATE TABLE IF NOT EXISTS customer (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            email TEXT UNIQUE,
            date_registered DATE NOT NULL DEFAULT(date('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS bike (
            bike_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bike_code TEXT NOT NULL UNIQUE,
            brand TEXT NOT NULL, model TEXT NOT NULL,
            size TEXT NOT NULL CHECK(size IN('small','medium','large')),
            color TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
                CHECK(status IN('available','rented','under_maintenance')),
            date_added DATE NOT NULL DEFAULT(date('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS rental (
            rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customer(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            bike_id INTEGER NOT NULL REFERENCES bike(bike_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            staff_id INTEGER NOT NULL REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            rental_start DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            rental_end DATETIME,
            rental_rate DECIMAL(8,2) NOT NULL,
            total_amount DECIMAL(8,2),
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','returned','overdue'))
        );
        CREATE TABLE IF NOT EXISTS payment (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rental_id INTEGER NOT NULL UNIQUE REFERENCES rental(rental_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            payment_date DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            amount_paid DECIMAL(8,2) NOT NULL,
            payment_method TEXT NOT NULL CHECK(payment_method IN('cash','gcash','card')),
            payment_status TEXT NOT NULL DEFAULT 'paid' CHECK(payment_status IN('paid','pending','refunded'))
        );
        CREATE TABLE IF NOT EXISTS maintenance (
            maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bike_id INTEGER NOT NULL REFERENCES bike(bike_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            staff_id INTEGER NOT NULL REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            maintenance_date DATE NOT NULL DEFAULT(date('now','localtime')),
            maintenance_type TEXT NOT NULL CHECK(maintenance_type IN('routine','repair','inspection')),
            description TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN('resolved','parts_needed','retired'))
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            timestamp DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            action TEXT NOT NULL, target_table TEXT, target_id INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_rental_customer ON rental(customer_id);
        CREATE INDEX IF NOT EXISTS idx_rental_bike ON rental(bike_id);
        CREATE INDEX IF NOT EXISTS idx_rental_status ON rental(status);
        CREATE INDEX IF NOT EXISTS idx_payment_rental ON payment(rental_id);
        CREATE INDEX IF NOT EXISTS idx_maint_bike ON maintenance(bike_id);
        CREATE INDEX IF NOT EXISTS idx_log_staff ON activity_log(staff_id);

        CREATE TRIGGER IF NOT EXISTS trg_rental_created AFTER INSERT ON rental
        BEGIN UPDATE bike SET status='rented' WHERE bike_id=NEW.bike_id; END;

        CREATE TRIGGER IF NOT EXISTS trg_rental_returned AFTER UPDATE OF status ON rental
        WHEN NEW.status='returned'
        BEGIN UPDATE bike SET status='available' WHERE bike_id=NEW.bike_id; END;

        CREATE TRIGGER IF NOT EXISTS trg_maint_started AFTER INSERT ON maintenance
        BEGIN UPDATE bike SET status='under_maintenance' WHERE bike_id=NEW.bike_id; END;

        CREATE TRIGGER IF NOT EXISTS trg_maint_resolved AFTER UPDATE OF outcome ON maintenance
        WHEN NEW.outcome='resolved'
        BEGIN UPDATE bike SET status='available' WHERE bike_id=NEW.bike_id; END;
        """)
        self.conn.commit()

    # Auth
    def get_staff_by_username(self, username):
        r = self.conn.execute("SELECT * FROM staff WHERE username=? AND status='active'", (username,)).fetchone()
        return dict(r) if r else None
    
    def verify_user(self, username, password):
        user = self.conn.execute('SELECT * FROM staff WHERE username = ?', (username,)).fetchone()

        if user and check_password_hash(user['password_hash'], password):
            return True
        else:
            return False

    # Staff
    def get_all_staff(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM staff ORDER BY last_name,first_name").fetchall()]

    def create_staff(self, d):
        self.conn.execute("INSERT INTO staff(username,password_hash,first_name,last_name,role,contact_number,status) VALUES(:username,:password_hash,:first_name,:last_name,:role,:contact_number,'active')", d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_staff(self, sid, d):
        d["staff_id"] = sid
        self.conn.execute("UPDATE staff SET username=:username,first_name=:first_name,last_name=:last_name,role=:role,contact_number=:contact_number,status=:status WHERE staff_id=:staff_id", d)
        self.conn.commit()

    def update_staff_password(self, sid, pw_hash):
        self.conn.execute("UPDATE staff SET password_hash=? WHERE staff_id=?", (pw_hash, sid))
        self.conn.commit()

    def toggle_staff_status(self, sid, status):
        self.conn.execute("UPDATE staff SET status=? WHERE staff_id=?", (status, sid))
        self.conn.commit()

    # Customers
    def get_all_customers(self, search=""):
        q = f"%{search}%"
        return [dict(r) for r in self.conn.execute("SELECT * FROM customer WHERE first_name LIKE ? OR last_name LIKE ? OR contact_number LIKE ? OR email LIKE ? ORDER BY last_name,first_name", (q,q,q,q)).fetchall()]

    def get_customer(self, cid):
        r = self.conn.execute("SELECT * FROM customer WHERE customer_id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def create_customer(self, d):
        self.conn.execute("INSERT INTO customer(first_name,last_name,contact_number,email) VALUES(:first_name,:last_name,:contact_number,:email)", d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_customer(self, cid, d):
        d["customer_id"] = cid
        self.conn.execute("UPDATE customer SET first_name=:first_name,last_name=:last_name,contact_number=:contact_number,email=:email WHERE customer_id=:customer_id", d)
        self.conn.commit()

    def get_customer_rentals(self, cid):
        return [dict(r) for r in self.conn.execute("SELECT r.*,b.bike_code,b.brand,b.model FROM rental r JOIN bike b ON r.bike_id=b.bike_id WHERE r.customer_id=? ORDER BY r.rental_start DESC LIMIT 10", (cid,)).fetchall()]

    def get_customer_stats(self, cid):
        r = self.conn.execute("SELECT COUNT(*) as total_rentals, COALESCE(SUM(total_amount),0) as total_spent FROM rental WHERE customer_id=? AND status='returned'", (cid,)).fetchone()
        return dict(r)

    # Bikes
    def get_all_bikes(self, search="", status="all"):
        q = f"%{search}%"
        if status != "all":
            return [dict(r) for r in self.conn.execute("SELECT * FROM bike WHERE (bike_code LIKE ? OR brand LIKE ? OR model LIKE ? OR color LIKE ?) AND status=? ORDER BY bike_code", (q,q,q,q,status)).fetchall()]
        return [dict(r) for r in self.conn.execute("SELECT * FROM bike WHERE bike_code LIKE ? OR brand LIKE ? OR model LIKE ? OR color LIKE ? ORDER BY bike_code", (q,q,q,q)).fetchall()]

    def get_bike(self, bid):
        r = self.conn.execute("SELECT * FROM bike WHERE bike_id=?", (bid,)).fetchone()
        return dict(r) if r else None

    def get_available_bikes(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM bike WHERE status='available' ORDER BY bike_code").fetchall()]

    def create_bike(self, d):
        self.conn.execute("INSERT INTO bike(bike_code,brand,model,size,color,status) VALUES(:bike_code,:brand,:model,:size,:color,'available')", d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_bike(self, bid, d):
        d["bike_id"] = bid
        self.conn.execute("UPDATE bike SET bike_code=:bike_code,brand=:brand,model=:model,size=:size,color=:color WHERE bike_id=:bike_id", d)
        self.conn.commit()

    def get_bike_stats(self):
        r = self.conn.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) as available, SUM(CASE WHEN status='rented' THEN 1 ELSE 0 END) as rented, SUM(CASE WHEN status='under_maintenance' THEN 1 ELSE 0 END) as maintenance FROM bike").fetchone()
        return dict(r)

    # Rentals
    def get_all_rentals(self, status="all"):
        base = "SELECT r.*,c.first_name||' '||c.last_name AS customer_name,b.bike_code,b.brand,b.model,s.first_name||' '||s.last_name AS staff_name FROM rental r JOIN customer c ON r.customer_id=c.customer_id JOIN bike b ON r.bike_id=b.bike_id JOIN staff s ON r.staff_id=s.staff_id"
        if status != "all":
            rows = self.conn.execute(base+" WHERE r.status=? ORDER BY r.rental_start DESC", (status,)).fetchall()
        else:
            rows = self.conn.execute(base+" ORDER BY r.rental_start DESC").fetchall()
        return [dict(r) for r in rows]

    def get_rental(self, rid):
        r = self.conn.execute("SELECT r.*,c.first_name||' '||c.last_name AS customer_name,b.bike_code,b.brand,b.model,b.size,s.first_name||' '||s.last_name AS staff_name FROM rental r JOIN customer c ON r.customer_id=c.customer_id JOIN bike b ON r.bike_id=b.bike_id JOIN staff s ON r.staff_id=s.staff_id WHERE r.rental_id=?", (rid,)).fetchone()
        return dict(r) if r else None

    def create_rental(self, d):
        self.conn.execute("INSERT INTO rental(customer_id,bike_id,staff_id,rental_start,rental_rate,notes,status) VALUES(:customer_id,:bike_id,:staff_id,:rental_start,:rental_rate,:notes,'active')", d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def return_rental(self, rid, rental_end, total_amount):
        self.conn.execute("UPDATE rental SET rental_end=?,total_amount=?,status='returned' WHERE rental_id=?", (rental_end, total_amount, rid))
        self.conn.commit()

    def get_active_rentals(self):
        return [dict(r) for r in self.conn.execute("SELECT r.*,c.first_name||' '||c.last_name AS customer_name,b.bike_code,b.brand,b.model FROM rental r JOIN customer c ON r.customer_id=c.customer_id JOIN bike b ON r.bike_id=b.bike_id WHERE r.status IN('active','overdue') ORDER BY r.rental_start").fetchall()]

    def get_dashboard_stats(self):
        r = self.conn.execute("SELECT (SELECT COUNT(*) FROM rental WHERE status='active') as active_rentals,(SELECT COUNT(*) FROM rental WHERE status='overdue') as overdue,(SELECT COUNT(*) FROM bike WHERE status='available') as bikes_available,(SELECT COALESCE(SUM(p.amount_paid),0) FROM payment p WHERE date(p.payment_date)=date('now','localtime')) as revenue_today").fetchone()
        return dict(r)

    # Payments
    def get_all_payments(self):
        return [dict(r) for r in self.conn.execute("SELECT p.*,c.first_name||' '||c.last_name AS customer_name,b.bike_code FROM payment p JOIN rental r ON p.rental_id=r.rental_id JOIN customer c ON r.customer_id=c.customer_id JOIN bike b ON r.bike_id=b.bike_id ORDER BY p.payment_date DESC").fetchall()]

    def create_payment(self, d):
        self.conn.execute("INSERT INTO payment(rental_id,amount_paid,payment_method,payment_status) VALUES(:rental_id,:amount_paid,:payment_method,'paid')", d)
        self.conn.commit()

    def get_payment_for_rental(self, rid):
        r = self.conn.execute("SELECT * FROM payment WHERE rental_id=?", (rid,)).fetchone()
        return dict(r) if r else None

    # Maintenance
    def get_all_maintenance(self):
        return [dict(r) for r in self.conn.execute("SELECT m.*,b.bike_code,b.brand,b.model,s.first_name||' '||s.last_name AS staff_name FROM maintenance m JOIN bike b ON m.bike_id=b.bike_id JOIN staff s ON m.staff_id=s.staff_id ORDER BY m.maintenance_date DESC").fetchall()]

    def create_maintenance(self, d):
        self.conn.execute("INSERT INTO maintenance(bike_id,staff_id,maintenance_date,maintenance_type,description,outcome) VALUES(:bike_id,:staff_id,:maintenance_date,:maintenance_type,:description,:outcome)", d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_maintenance(self, mid, d):
        d["maintenance_id"] = mid
        self.conn.execute("UPDATE maintenance SET maintenance_type=:maintenance_type,description=:description,outcome=:outcome WHERE maintenance_id=:maintenance_id", d)
        self.conn.commit()

    def get_bikes_for_maintenance(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM bike WHERE status != 'rented' ORDER BY bike_code").fetchall()]

    # Activity Log
    def log_action(self, staff_id, action, target_table=None, target_id=None):
        self.conn.execute("INSERT INTO activity_log(staff_id,action,target_table,target_id) VALUES(?,?,?,?)", (staff_id, action, target_table, target_id))
        self.conn.commit()

def init():
    global db
    db = Database()

def get():
    if not db: init()
    return db
    

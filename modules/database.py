import sqlite3
import math
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

import modules.appFileHandler as appFileHandler

DB_PATH = appFileHandler.resource_path("data/database.db")
db = None

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._create_tables()
        self._migrate_schema()
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
            role TEXT NOT NULL CHECK(role IN('admin','cashier')),
            contact_number TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','inactive')),
            created_at DATETIME NOT NULL DEFAULT(datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS customer (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL,
            contact_number TEXT NOT NULL,
            email TEXT UNIQUE,
            staff_id INTEGER REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE SET NULL,
            valid_id TEXT,
            date_registered DATE NOT NULL DEFAULT(date('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS bike (
            bike_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bike_code TEXT NOT NULL UNIQUE,
            brand TEXT NOT NULL, model TEXT NOT NULL,
            color TEXT NOT NULL,
            bike_rate DECIMAL(8,2) NOT NULL DEFAULT 0,
            type TEXT NOT NULL DEFAULT 'standard',
            status TEXT NOT NULL DEFAULT 'available' CHECK(status IN('available','rented','retired')),
            date_added DATE NOT NULL DEFAULT(date('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS rents (
            rental_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bike_id INTEGER NOT NULL,
            staff_id INTEGER REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE SET NULL,
            rental_start DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            FOREIGN KEY(customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
            FOREIGN KEY(bike_id) REFERENCES bike(bike_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS returns (
            return_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bike_id INTEGER NOT NULL,
            rental_end DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            total_amount DECIMAL(10,2) NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
            FOREIGN KEY(bike_id) REFERENCES bike(bike_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS payment (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bike_id INTEGER NOT NULL,
            rental_id INTEGER,
            payment_date DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            amount_paid DECIMAL(10,2) NOT NULL,
            payment_method TEXT NOT NULL CHECK(payment_method IN('cash', 'gcash', 'card')),
            payment_status TEXT NOT NULL DEFAULT 'paid' CHECK(payment_status IN('paid', 'pending')),
            FOREIGN KEY(customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
            FOREIGN KEY(bike_id) REFERENCES bike(bike_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
            timestamp DATETIME NOT NULL DEFAULT(datetime('now','localtime')),
            action TEXT NOT NULL, target_table TEXT, target_id INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_rents_customer ON rents(customer_id);
        CREATE INDEX IF NOT EXISTS idx_rents_bike ON rents(bike_id);
        CREATE INDEX IF NOT EXISTS idx_rents_staff ON rents(staff_id);
        CREATE INDEX IF NOT EXISTS idx_log_staff ON activity_log(staff_id);

        CREATE TRIGGER IF NOT EXISTS trg_rents_created AFTER INSERT ON rents
        BEGIN UPDATE bike SET status='rented' WHERE bike_id=NEW.bike_id; END;

        CREATE TRIGGER IF NOT EXISTS trg_returns_created AFTER INSERT ON returns
        BEGIN UPDATE bike SET status='available' WHERE bike_id=NEW.bike_id; END;

        """)
        self.conn.commit()

    # Line under are solely for migrating the old schema to the new one
    # ----------------------------------------------------------------------------------------------------------------------------------------------------
    def _column_exists(self, table, column):
        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column or (isinstance(row, dict) and row.get('name') == column) for row in rows)

    def _migrate_bike_status(self):
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.executescript(
            """
            CREATE TABLE bike_new (
                bike_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bike_code TEXT NOT NULL UNIQUE,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                color TEXT NOT NULL,
                bike_rate DECIMAL(8,2) NOT NULL DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'standard',
                status TEXT NOT NULL DEFAULT 'available' CHECK(status IN('available','rented','retired')),
                date_added DATE NOT NULL DEFAULT(date('now','localtime'))
            );
            INSERT INTO bike_new (
                bike_id, bike_code, brand, model, color, bike_rate, type, status, date_added
            )
            SELECT
                bike_id,
                bike_code,
                brand,
                model,
                color,
                COALESCE(bike_rate, 0),
                COALESCE(type, 'standard'),
                status,
                date_added
            FROM bike;
            DROP TABLE bike;
            ALTER TABLE bike_new RENAME TO bike;
            """
        )
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()
        self._create_tables()

    def _remove_bike_size_column(self):
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.executescript(
            """
            CREATE TABLE bike_new (
                bike_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bike_code TEXT NOT NULL UNIQUE,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                color TEXT NOT NULL,
                bike_rate DECIMAL(8,2) NOT NULL DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'standard',
                status TEXT NOT NULL DEFAULT 'available' CHECK(status IN('available','rented','retired')),
                date_added DATE NOT NULL DEFAULT(date('now','localtime'))
            );
            INSERT INTO bike_new (
                bike_id, bike_code, brand, model, color, bike_rate, type, status, date_added
            )
            SELECT
                bike_id,
                bike_code,
                brand,
                model,
                color,
                COALESCE(bike_rate, 0),
                COALESCE(type, 'standard'),
                status,
                date_added
            FROM bike;
            DROP TABLE bike;
            ALTER TABLE bike_new RENAME TO bike;
            """
        )
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    def _migrate_schema(self): 
        if not self._column_exists("customer", "staff_id"):
            self.conn.execute(
                "ALTER TABLE customer ADD COLUMN staff_id INTEGER REFERENCES staff(staff_id) ON UPDATE CASCADE ON DELETE SET NULL"
            )
        if not self._column_exists("customer", "valid_id"):
            self.conn.execute("ALTER TABLE customer ADD COLUMN valid_id TEXT")
        if not self._column_exists("bike", "bike_rate"):
            self.conn.execute("ALTER TABLE bike ADD COLUMN bike_rate DECIMAL(8,2) NOT NULL DEFAULT 0")
        if not self._column_exists("bike", "type"):
            self.conn.execute("ALTER TABLE bike ADD COLUMN type TEXT NOT NULL DEFAULT 'standard'")
     
        if self._column_exists("bike", "size"):
            self._remove_bike_size_column()
        
        self.conn.execute("UPDATE staff SET role='cashier' WHERE role='mechanic'")

        bike_row = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bike'").fetchone()
        if bike_row:
            self.conn.execute("UPDATE bike SET bike_rate=COALESCE(bike_rate, 0)")
            self.conn.execute("UPDATE bike SET type=COALESCE(type, 'standard')")
            self.conn.execute("UPDATE bike SET status='available' WHERE status='under_maintenance'")
            
        row = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rents'").fetchone()
        if row and not self._column_exists('rents', 'staff_id'):
            self.conn.execute("ALTER TABLE rents ADD COLUMN staff_id INTEGER")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_rents_staff ON rents(staff_id)")
        if row and not self._column_exists('rents', 'planned_return'):
            self.conn.execute("ALTER TABLE rents ADD COLUMN planned_return DATETIME")
        self.conn.commit()
    # ----------------------------------------------------------------------------------------------------------------------------------------------------

    # STAFF ----------------------------------------------------------------------------------------------------------------------------------------------

    def get_staff_by_username(self, username):
        r = self.conn.execute("SELECT * FROM staff WHERE username=? AND status='active'", (username,)).fetchone()
        return dict(r) if r else None
    
    def verify_user(self, username, password):
        user = self.conn.execute("SELECT * FROM staff WHERE username = ? AND status='active'", (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            return True
        else:
            return False

    def get_all_staff(self):
        query = "SELECT * FROM staff ORDER BY last_name, first_name"
        return [dict(r) for r in self.conn.execute(query).fetchall()]

    def get_staff(self, sid):
        r = self.conn.execute("SELECT * FROM staff WHERE staff_id=?", (sid,)).fetchone()
        return dict(r) if r else None

    def create_staff(self, d):
        query = """
            INSERT INTO staff (username, password_hash, first_name, last_name, role, contact_number, status) 
            VALUES (:username, :password_hash, :first_name, :last_name, :role, :contact_number, 'active')
        """
        self.conn.execute(query, d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_staff(self, sid, d):
        d["staff_id"] = sid
        query = """
            UPDATE staff 
            SET username = :username, 
                first_name = :first_name, 
                last_name = :last_name, 
                role = :role, 
                contact_number = :contact_number, 
                status = :status 
            WHERE staff_id = :staff_id
        """
        self.conn.execute(query, d)
        self.conn.commit()

    def update_staff_password(self, sid, pw_hash):
        self.conn.execute("UPDATE staff SET password_hash=? WHERE staff_id=?", (pw_hash, sid))
        self.conn.commit()

    def toggle_staff_status(self, sid, status):
        self.conn.execute("UPDATE staff SET status=? WHERE staff_id=?", (status, sid))
        self.conn.commit()

    # CUSTOMERS -----------------------------------------------------------------------------------------------------------------------------------------

    def get_all_customers(self, search=""):
        q = f"%{search}%"
        query = """
            SELECT * FROM customer 
            WHERE first_name LIKE ? 
               OR last_name LIKE ? 
               OR contact_number LIKE ? 
               OR email LIKE ? 
            ORDER BY last_name, first_name
        """
        return [dict(r) for r in self.conn.execute(query, (q, q, q, q)).fetchall()]

    def get_customer(self, cid):
        query = """
            SELECT c.*, s.first_name || ' ' || s.last_name AS staff_name, s.role AS staff_role
            FROM customer c
            LEFT JOIN staff s ON c.staff_id = s.staff_id
            WHERE c.customer_id = ?
        """
        r = self.conn.execute(query, (cid,)).fetchone()
        return dict(r) if r else None

    def create_customer(self, d):
        query = """
            INSERT INTO customer (first_name, last_name, contact_number, email, staff_id, valid_id)
            VALUES (:first_name, :last_name, :contact_number, :email, :staff_id, :valid_id)
        """
        self.conn.execute(query, d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_customer(self, cid, d):
        d["customer_id"] = cid
        query = """
            UPDATE customer 
            SET first_name = :first_name, 
                last_name = :last_name, 
                contact_number = :contact_number,
                email = :email, 
                valid_id = :valid_id 
            WHERE customer_id = :customer_id
        """
        self.conn.execute(query, d)
        self.conn.commit()

    def get_customer_rentals(self, cid):
        query = """
            SELECT 
                rents.rental_id, 
                rents.customer_id, 
                rents.bike_id, 
                rents.staff_id, 
                s.first_name || ' ' || s.last_name AS staff_name, 
                rents.rental_start,
                rents.planned_return,
                b.bike_code, 
                b.brand, 
                b.model, 
                b.bike_rate AS rental_rate,
                (SELECT rental_end FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS rental_end,
                (SELECT total_amount FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS total_amount
            FROM rents 
            LEFT JOIN staff s ON rents.staff_id = s.staff_id 
            JOIN bike b ON rents.bike_id = b.bike_id 
            WHERE rents.customer_id = ? 
            ORDER BY rents.rental_start DESC 
            LIMIT 10
        """
        rows = self.conn.execute(query, (cid,)).fetchall()

        result = []
        for r in rows:
            rr = dict(r)
            if rr['rental_end'] is not None:
                rr['status'] = 'returned'
            elif rr.get('planned_return') and datetime.now() > datetime.fromisoformat(rr['planned_return']):
                rr['status'] = 'overdue'
            else:
                rr['status'] = 'active'
            result.append(rr)
        return result

    def get_customer_stats(self, cid):
        query_rentals = """
            SELECT COUNT(*) FROM rents 
            WHERE EXISTS (
                SELECT 1 FROM returns 
                WHERE returns.customer_id = rents.customer_id 
                  AND returns.bike_id = rents.bike_id 
                  AND returns.rental_end >= rents.rental_start
            ) 
            AND rents.customer_id = ?
        """
        total_rentals = self.conn.execute(query_rentals, (cid,)).fetchone()[0]

        query_spent = """
            SELECT COALESCE(SUM((
                SELECT total_amount FROM returns 
                WHERE returns.customer_id = rents.customer_id 
                  AND returns.bike_id = rents.bike_id 
                  AND returns.rental_end >= rents.rental_start 
                ORDER BY returns.rental_end LIMIT 1
            )), 0) 
            FROM rents 
            WHERE rents.customer_id = ?
        """
        total_spent = self.conn.execute(query_spent, (cid,)).fetchone()[0]
        
        return {'total_rentals': total_rentals, 'total_spent': total_spent}

    # BIKES ----------------------------------------------------------------------------------------------------------------------------------------------
    
    def get_all_bikes(self, search="", status="all"):
        q = f"%{search}%"
        if status != "all":
            query = """
                SELECT * FROM bike 
                WHERE (bike_code LIKE ? OR brand LIKE ? OR model LIKE ? OR color LIKE ?) 
                  AND status = ? 
                ORDER BY bike_code
            """
            return [dict(r) for r in self.conn.execute(query, (q, q, q, q, status)).fetchall()]
            
        query = """
            SELECT * FROM bike 
            WHERE bike_code LIKE ? 
               OR brand LIKE ? 
               OR model LIKE ? 
               OR color LIKE ? 
            ORDER BY bike_code
        """
        return [dict(r) for r in self.conn.execute(query, (q, q, q, q)).fetchall()]

    def get_bike(self, bid):
        query = "SELECT * FROM bike WHERE bike_id = ?"
        r = self.conn.execute(query, (bid,)).fetchone()
        return dict(r) if r else None

    def get_next_bike_code(self):
        query = "SELECT bike_code FROM bike WHERE bike_code GLOB 'BK-[0-9]*' ORDER BY CAST(SUBSTR(bike_code, 4) AS INTEGER) DESC LIMIT 1"
        r = self.conn.execute(query).fetchone()
        if not r:
            return 'BK-001'
        last_code = r['bike_code']
        m = re.match(r'^BK-(\d+)$', last_code)
        if not m:
            return 'BK-001'
        next_num = int(m.group(1)) + 1
        width = max(len(m.group(1)), 3)
        return f"BK-{next_num:0{width}d}"

    def get_available_bikes(self):
        query = "SELECT * FROM bike WHERE status = 'available' ORDER BY bike_code"
        return [dict(r) for r in self.conn.execute(query).fetchall()]

    def create_bike(self, d):
        query = """
            INSERT INTO bike (bike_code, brand, model, color, bike_rate, type, status) 
            VALUES (:bike_code, :brand, :model, :color, :bike_rate, :type, 'available')
        """
        self.conn.execute(query, d)
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_bike(self, bid, d):
        d["bike_id"] = bid
        query = """
            UPDATE bike 
            SET bike_code = :bike_code, 
                brand = :brand, 
                model = :model, 
                color = :color, 
                bike_rate = :bike_rate, 
                type = :type 
            WHERE bike_id = :bike_id
        """
        self.conn.execute(query, d)
        self.conn.commit()

    def get_bike_stats(self):
        query = """
            SELECT 
                COUNT(*) as total, 
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available, 
                SUM(CASE WHEN status = 'rented' THEN 1 ELSE 0 END) as rented 
            FROM bike
        """
        r = self.conn.execute(query).fetchone()
        return dict(r)
    
    def retire_bike(self, bid):
        bike = self.get_bike(bid)
        if not bike:
            return False, 'Bike not found.'
        if bike['status'] == 'rented':
            return False, 'Cannot retire a bike that is currently rented.'
        if bike['status'] == 'retired':
            return False, 'Bike is already retired.'
        self.conn.execute("UPDATE bike SET status='retired' WHERE bike_id=?", (bid,))
        self.conn.commit()
        return True, 'Bike retired successfully.'

    def get_current_renter_for_bike(self, bid):
        query = """
            SELECT
                rents.rental_id,
                rents.rental_start,
                rents.planned_return,
                c.customer_id,
                c.first_name || ' ' || c.last_name AS customer_name
            FROM rents
            JOIN customer c ON rents.customer_id = c.customer_id
            WHERE rents.bike_id = ?
            AND NOT EXISTS (
                SELECT 1 FROM returns
                WHERE returns.customer_id = rents.customer_id
                    AND returns.bike_id = rents.bike_id
                    AND returns.rental_end >= rents.rental_start
            )
            ORDER BY rents.rental_start DESC
            LIMIT 1
        """
        r = self.conn.execute(query, (bid,)).fetchone()
        return dict(r) if r else None

    # RENTALS ----------------------------------------------------------------------------------------------------------------------------------------------

    def get_all_rentals(self, status="all"):
        query = """
            SELECT 
                rents.rental_id, 
                rents.customer_id, 
                c.first_name || ' ' || c.last_name AS customer_name, 
                rents.staff_id, 
                s.first_name || ' ' || s.last_name AS staff_name, 
                b.bike_code, 
                b.brand, 
                b.model, 
                b.bike_rate AS rental_rate, 
                rents.rental_start,
                rents.planned_return,
                (SELECT rental_end FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS rental_end,
                (SELECT total_amount FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS total_amount
            FROM rents 
            JOIN customer c ON rents.customer_id = c.customer_id 
            LEFT JOIN staff s ON rents.staff_id = s.staff_id 
            JOIN bike b ON rents.bike_id = b.bike_id 
            ORDER BY rents.rental_start DESC
        """
        rows = self.conn.execute(query).fetchall()

        result = []
        for r in rows:
            rr = dict(r)
            if rr['rental_end'] is not None:
                rr['status'] = 'returned'
            elif rr.get('planned_return') and datetime.now() > datetime.fromisoformat(rr['planned_return']):
                rr['status'] = 'overdue'
            else:
                rr['status'] = 'active'
            result.append(rr)

        if status != 'all':
            result = [r for r in result if r['status'] == status]
        return result

    def get_rental(self, rid):
        query = """
            SELECT 
                rents.rental_id, 
                rents.customer_id, 
                c.first_name || ' ' || c.last_name AS customer_name, 
                rents.staff_id, 
                s.first_name || ' ' || s.last_name AS staff_name, 
                b.bike_code, 
                b.brand, 
                b.model, 
                b.bike_rate AS rental_rate, 
                rents.rental_start,
                rents.planned_return,
                (SELECT rental_end FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS rental_end,
                (SELECT total_amount FROM returns 
                 WHERE customer_id = rents.customer_id 
                   AND bike_id = rents.bike_id 
                   AND rental_end >= rents.rental_start 
                 ORDER BY rental_end LIMIT 1) AS total_amount
            FROM rents 
            JOIN customer c ON rents.customer_id = c.customer_id 
            LEFT JOIN staff s ON rents.staff_id = s.staff_id 
            JOIN bike b ON rents.bike_id = b.bike_id 
            WHERE rents.rental_id = ?
        """
        r = self.conn.execute(query, (rid,)).fetchone()
        if not r:
            return None
        rr = dict(r)
        if rr['rental_end'] is not None:
            rr['status'] = 'returned'
        elif rr.get('planned_return') and datetime.now() > datetime.fromisoformat(rr['planned_return']):
            rr['status'] = 'overdue'
        else:
            rr['status'] = 'active'
        return rr

    def create_rental(self, d):
        if not d.get('rental_start'):
            d['rental_start'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        query = "INSERT INTO rents (customer_id, bike_id,   rental_start, staff_id, planned_return) VALUES (?, ?, ?, ?, ?)"
        self.conn.execute(query, (d.get('customer_id'), d.get('bike_id'), d.get('rental_start'), d.get('staff_id'), d.get('planned_return')))
        self.conn.commit()
        return self.conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    def return_rental(self, rid):
        r = self.conn.execute("SELECT rental_start, bike_id, customer_id, planned_return FROM rents WHERE rental_id = ?", (rid,)).fetchone()
        if not r:
            return None
        rental_start = datetime.fromisoformat(r['rental_start'])
        rental_end = datetime.now()
        bike = self.conn.execute("SELECT bike_rate FROM bike WHERE bike_id = ?", (r['bike_id'],)).fetchone()
        rate = float(bike['bike_rate']) if bike else 0

        planned_return = datetime.fromisoformat(r['planned_return']) if r['planned_return'] else None

        if planned_return and rental_end > planned_return:
            normal_hours = max(1, math.ceil((planned_return - rental_start).total_seconds() / 3600))
            overtime_hours = math.floor((rental_end - planned_return).total_seconds() / 3600)
            total_amount = round((normal_hours * rate) + (overtime_hours * rate * 1.2), 2)
        else:
            duration_hours = max(1, math.ceil((rental_end - rental_start).total_seconds() / 3600))
            total_amount = round(duration_hours * rate, 2)

        query = "INSERT INTO returns (customer_id, bike_id, rental_end, total_amount) VALUES (?, ?, ?, ?)"
        self.conn.execute(query, (r['customer_id'], r['bike_id'], rental_end.strftime('%Y-%m-%d %H:%M:%S'), total_amount))
        self.conn.commit()
        return {
            'rental_end': rental_end.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': total_amount,
        }


    def get_active_rentals(self):
        rows = self.get_all_rentals()
        return [r for r in rows if r['status'] in ('active','overdue')]

    def get_all_payments(self):
        query = """
            SELECT 
                p.*, 
                c.first_name || ' ' || c.last_name AS customer_name, 
                b.bike_code 
            FROM payment p 
            JOIN customer c ON p.customer_id = c.customer_id 
            JOIN bike b ON p.bike_id = b.bike_id 
            ORDER BY p.payment_date DESC
        """
        return [dict(r) for r in self.conn.execute(query).fetchall()]

    def create_payment(self, d):
        rental_id = d.get('rental_id') or d.get('rental')
        cust_id = d.get('customer_id')
        bike_id = d.get('bike_id')
        if rental_id and (not cust_id or not bike_id):
            r = self.conn.execute("SELECT customer_id, bike_id FROM rents WHERE rental_id = ?", (rental_id,)).fetchone()
            if r:
                cust_id = r['customer_id']
                bike_id = r['bike_id']

        if not cust_id or not bike_id:
            raise ValueError('customer_id and bike_id required')

        query = """
            INSERT INTO payment (customer_id, bike_id, rental_id, amount_paid, payment_method, payment_status) 
            VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (cust_id, bike_id, rental_id, d.get('amount_paid'), d.get('payment_method'), d.get('payment_status') or 'paid'))
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_payment_for_rental(self, rid):
        r = self.conn.execute("SELECT * FROM payment WHERE rental_id = ?", (rid,)).fetchone()
        return dict(r) if r else None

    # MISC ----------------------------------------------------------------------------------------------------------------------------------------------

    def get_activity_log(self, limit=200):
        query = """
            SELECT 
                l.*, 
                s.first_name || ' ' || s.last_name AS staff_name, 
                s.role AS staff_role 
            FROM activity_log l 
            JOIN staff s ON l.staff_id = s.staff_id 
            ORDER BY l.timestamp DESC 
            LIMIT ?
        """
        rows = self.conn.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def log_action(self, staff_id, action, target_table=None, target_id=None):
        query = "INSERT INTO activity_log (staff_id, action, target_table, target_id) VALUES (?, ?, ?, ?)"
        self.conn.execute(query, (staff_id, action, target_table, target_id))
        self.conn.commit()

    def get_dashboard_stats(self):
        query_active = """
            SELECT COUNT(*) FROM rents 
            WHERE NOT EXISTS (
                SELECT 1 FROM returns 
                WHERE returns.customer_id = rents.customer_id 
                  AND returns.bike_id = rents.bike_id 
                  AND returns.rental_end >= rents.rental_start
            )
        """
        active = self.conn.execute(query_active).fetchone()[0]
        
        query_overdue = """
            SELECT COUNT(*) FROM rents 
            WHERE NOT EXISTS (
                SELECT 1 FROM returns 
                WHERE returns.customer_id = rents.customer_id 
                  AND returns.bike_id = rents.bike_id 
                  AND returns.rental_end >= rents.rental_start
            ) 
            AND planned_return <= datetime('now', 'localtime')
        """
        overdue = self.conn.execute(query_overdue).fetchone()[0]
        
        bikes_available = self.conn.execute("SELECT COUNT(*) FROM bike WHERE status = 'available'").fetchone()[0]
        revenue_today = self.conn.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM payment WHERE date(payment_date) = date('now', 'localtime')").fetchone()[0]
        
        return {
            'active_rentals': active,
            'overdue': overdue,
            'bikes_available': bikes_available,
            'revenue_today': revenue_today,
        }

def init():
    global db
    db = Database()

def get():
    if not db: init()
    return db
    

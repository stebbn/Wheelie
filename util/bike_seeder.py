import sqlite3
import random
from datetime import datetime, timedelta

def seed_full_operations(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    brands = ["Giant", "Trek", "Specialized", "Cannondale", "Santa Cruz", "Scott", "Bianchi", "Cube", "Merida", "Kona"]
    models = ["Speedster", "Trail", "Allez", "Marlin", "Quick", "Rockhopper", "Domane", "Talon", "Big Nine", "Unit"]
    colors = ["Red", "Blue", "Matte Black", "Silver", "Neon Green", "White", "Orange", "Yellow"]
    maint_types = ["routine", "repair", "inspection"]
    outcomes = ["resolved", "parts_needed", "retired"]

    try:
        print("Seeding 100 bikes...")
        for i in range(1, 101):
            code = f"BK-{1000 + i}"
            cursor.execute("""
                INSERT OR IGNORE INTO bike (bike_code, brand, model, size, color)
                VALUES (?, ?, ?, ?, ?)""",
                (code, random.choice(brands), random.choice(models), 
                 random.choice(['small', 'medium', 'large']), random.choice(colors)))

        staff_ids = [row[0] for row in cursor.execute("SELECT staff_id FROM staff").fetchall()]
        customer_ids = [row[0] for row in cursor.execute("SELECT customer_id FROM customer").fetchall()]
        bike_ids = [row[0] for row in cursor.execute("SELECT bike_id FROM bike").fetchall()]

        if not staff_ids or not customer_ids:
            print("Error: Please seed Staff and Customers first!")
            return

 
        for _ in range(50):
            b_id = random.choice(bike_ids)
            s_id = random.choice(staff_ids)
            cursor.execute("""
                INSERT INTO maintenance (bike_id, staff_id, maintenance_type, description, outcome)
                VALUES (?, ?, ?, ?, ?)""",
                (b_id, s_id, random.choice(maint_types), "Scheduled checkup or part replacement.", random.choice(outcomes)))

        print("Seeding 200 rentals and payments...")
        for _ in range(200):
            b_id = random.choice(bike_ids)
            c_id = random.choice(customer_ids)
            s_id = random.choice(staff_ids)
            rate = random.choice([100.0, 150.0, 200.0, 350.0])
 
            current_status = 'returned' if random.random() < 0.7 else 'active'
            
            cursor.execute("""
                INSERT INTO rental (customer_id, bike_id, staff_id, rental_rate, status, total_amount)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (c_id, b_id, s_id, rate, current_status, rate if current_status == 'returned' else None))
            
            rental_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO payment (rental_id, amount_paid, payment_method, payment_status)
                VALUES (?, ?, ?, ?)""",
                (rental_id, rate, random.choice(['cash', 'gcash', 'card']), 'paid'))

        conn.commit()
        print("Successfully seeded Bikes, Maintenance, and Payments!")

    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_full_operations()
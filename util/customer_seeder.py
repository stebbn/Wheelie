import sqlite3
import random

def seed_large_dataset(db_path="data/database.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    first_names = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Matthew", "Lisa", "Anthony", "Betty", "Mark", "Margaret", "Donald", "Sandra", "Steven", "Ashley", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna", "Kenneth", "Michelle", "Kevin", "Dorothy", "Brian", "Carol", "George", "Amanda", "Timothy", "Melissa", "Ronald", "Deborah"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts"]
    domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "example.ph", "protonmail.com"]

    count = 0
    attempts = 0
 
    while count < 500:
        attempts += 1
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        
        suffix = random.randint(1000, 9999)
        email = f"{fname.lower()}.{lname.lower()}{suffix}@{random.choice(domains)}"
        phone = f"09{random.randint(10, 99)}{random.randint(1000000, 9999999)}"

        try:
            cursor.execute("""
                INSERT INTO customer (first_name, last_name, contact_number, email)
                VALUES (?, ?, ?, ?)""", (fname, lname, phone, email))
            count += 1
        except sqlite3.IntegrityError:
            continue
    
        if count % 100 == 0:
            print(f"Reached {count} customers...")

    conn.commit()
    print(f"Finished! Seeded {count} unique customers (took {attempts} attempts).")
    conn.close()

if __name__ == "__main__":
    seed_large_dataset()
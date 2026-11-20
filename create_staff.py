import os
import getpass

database_url = input("Paste Render DATABASE_URL: ").strip()

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

os.environ["DATABASE_URL"] = database_url

from app import app, db, Staff
from werkzeug.security import generate_password_hash

with app.app_context():
    name = input("Enter staff name: ").strip()
    username = input("Enter staff username: ").strip()
    password = getpass.getpass("Enter staff password: ")

    existing_staff = Staff.query.filter_by(username=username).first()

    if existing_staff:
        existing_staff.full_name = name
        existing_staff.password = generate_password_hash(password)
        print("Existing staff account updated!")
    else:
        staff = Staff(
            full_name=name,
            username=username,
            password=generate_password_hash(password)
        )
        db.session.add(staff)
        print("Staff account created!")

    db.session.commit()
    print("Database updated successfully!")
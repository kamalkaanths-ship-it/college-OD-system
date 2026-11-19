from app import app, db, Staff
from werkzeug.security import generate_password_hash

with app.app_context():

    name = input("Enter staff name: ")
    username = input("Enter staff username: ")
    password = input("Enter staff password: ")

    existing_staff = Staff.query.filter_by(username=username).first()

    if existing_staff:
        print("Username already exists!")

    else:
        staff = Staff(
            full_name=name,
            username=username,
            password=generate_password_hash(password)
        )

        db.session.add(staff)
        db.session.commit()

        print("Staff account created successfully!")
from app import app, db, ODApplication
from sqlalchemy import inspect

with app.app_context():

    table_name = ODApplication.__tablename__

    inspector = inspect(db.engine)
    existing_columns = {
        column['name']
        for column in inspector.get_columns(table_name)
    }

    with db.engine.begin() as connection:

        if 'submitted_at' not in existing_columns:
            connection.exec_driver_sql(
                f'ALTER TABLE "{table_name}" ADD COLUMN submitted_at DATETIME'
            )

        if 'staff_remarks' not in existing_columns:
            connection.exec_driver_sql(
                f'ALTER TABLE "{table_name}" ADD COLUMN staff_remarks TEXT'
            )

    print("Database updated successfully!")
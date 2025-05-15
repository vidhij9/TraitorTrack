import os
import sys
from app_clean import app, db
from models import User, Location, Bag, Link, Bill, BillBag, Scan

def recreate_tables():
    """
    Drop all tables and recreate them based on the current models.
    WARNING: This will delete all data in the database.
    """
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating all tables...")
        db.create_all()
        
        print("Database schema updated successfully.")

if __name__ == "__main__":
    # In the replit environment, we'll skip the confirmation
    print("Running in automatic mode. Recreating tables...")
    recreate_tables()
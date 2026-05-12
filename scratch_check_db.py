import os
import asyncio
import sys

# Add current directory to path so server module can be imported
sys.path.append(os.getcwd())

from server.db import get_db
from server.models import Study, User

def check_studies():
    db = get_db()
    if not db:
        print("No database connection available.")
        return

    try:
        users = db.query(User).all()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f" - User ID: {u.id}, Name: {u.name}, Email: {u.email}")
            
        studies = db.query(Study).all()
        print(f"\nFound {len(studies)} total studies in DB:")
        for s in studies:
            print(f" - ID: {s.id}, Title: {s.title}, UserID: {s.userId}, Status: {s.status}")
            
    except Exception as e:
        print(f"Error querying DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_studies()

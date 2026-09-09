from database import SessionLocal, Base, engine
import models
from seed import seed_database_if_empty

def reset():
    print("Resetting database to clean demo state...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()
    print("Clean demo seed restored!")

if __name__ == "__main__":
    reset()

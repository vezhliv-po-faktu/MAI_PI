from database import Base, engine, SessionLocal
from models import User
from sqlalchemy.exc import IntegrityError
from passlib.hash import bcrypt

def init():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(username="admin", hashed_password=bcrypt.hash("secret"))
            db.add(admin)
            db.commit()
            print("Admin user created")
    except IntegrityError:
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init()
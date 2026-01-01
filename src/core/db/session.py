# create an engine, sqlalchemy database url for sql lite can be picked from env, sessionlocal, get db function
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


load_dotenv()

# 1. connection string
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")


# 2. engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)


# 3. sessionlocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 4. get db function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

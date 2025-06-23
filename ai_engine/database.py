from sqlmodel import Session, SQLModel, create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/autoops")

engine = create_engine(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close() 

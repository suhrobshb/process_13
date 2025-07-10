from sqlmodel import Session, SQLModel, create_engine
import os
import logging
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/autoops")

# Database engine with connection pooling
if DATABASE_URL.startswith("postgresql"):
    # PostgreSQL with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # Number of connections to maintain in pool
        max_overflow=20,  # Additional connections if pool is exhausted
        pool_timeout=30,  # Timeout when getting connection from pool
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Validate connections before use
        echo=False  # Set to True for SQL debugging
    )
    logger.info("Database engine initialized with PostgreSQL connection pooling")
else:
    # SQLite fallback (for development/testing)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("Database engine initialized with SQLite")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@contextmanager
def get_session():
    """Get database session with proper error handling"""
    session = Session(engine)
    try:
        yield session
    except Exception as e:
        logger.error("Database session error: {}".format(e))
        session.rollback()
        raise
    finally:
        session.close()

def health_check():
    """Perform database health check"""
    try:
        with Session(engine) as session:
            # Simple query to test connection
            result = session.execute("SELECT 1")
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Database health check failed: {}".format(e))
        return {"status": "unhealthy", "error": str(e)} 

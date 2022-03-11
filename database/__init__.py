"""Module for organizing the database connections and operations"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from settings import DatabaseSettings
from .tables import TableBase

# Read the configuration of the service
_database_settings = DatabaseSettings()

# Create a new database engine
__db_engine = create_engine(
    _database_settings.dsn, pool_recycle=90
)

# Create a Database Session used later on in the api
DatabaseSession = sessionmaker(autocommit=False, autoflush=False, bind=__db_engine)


def get_database_session() -> DatabaseSession:
    """Get an opened Database session which can be used to query data

        :return: Database Session
        :rtype: DatabaseSession
        """
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close()
        

def engine() -> Engine:
    return __db_engine


def initialise_orm_models():
    """Initialize the ORM models and create the necessary metadata"""
    TableBase.metadata.create_all(bind=__db_engine)

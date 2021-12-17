"""Module for organizing the database connections and operations"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import ServiceSettings

# Read the configuration of the service
service_config = ServiceSettings()

# Create a new database engine
__db_engine = create_engine(
    service_config.database_dsn, pool_recycle=90
)

# Create a Database Session used later on in the api
DatabaseSession = sessionmaker(autocommit=False, autoflush=False, bind=__db_engine)
# Create a Base for new table declarations
TableBase = declarative_base()


def initialise_orm_models():
    """Initialize the ORM models and create the necessary metadata"""
    TableBase.metadata.create_all(bind=__db_engine)


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

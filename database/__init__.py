"""Module for organizing the database connections and operations"""
import logging
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils.functions import database_exists, create_database
from models import ServiceSettings
from .tables import TableBase
import imports

# Read the configuration of the service
service_config = ServiceSettings()

# Create a new database engine
__db_engine = create_engine(
    service_config.database_dsn, pool_recycle=90
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


def initialise_orm_models():
    """Initialize the ORM models and create the necessary metadata"""
    if not database_exists(service_config.database_dsn):
        try:
            create_database(service_config.database_dsn)
            # Bind all the tables and create those
            TableBase.metadata.create_all(bind=__db_engine)
            # Create a database session for importing the files
            db_session = next(get_database_session())
            # Since the database was just created import all the example files
            imports.csv.import_counties_from_file('./data/example-counties.csv', db_session)
            imports.csv.import_communes_from_file('./data/example-communes.csv', db_session)
            imports.csv.import_consumer_types_from_file(
                './data/example-consumer-types.csv',
                db_session
            )
            imports.csv.import_water_usages_from_file(
                './data/example-usage-amounts.csv',
                db_session
            )
        except (ProgrammingError, OperationalError):
            pass
    else:
        TableBase.metadata.create_all(bind=__db_engine)

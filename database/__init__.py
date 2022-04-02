import logging

import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm

import settings

_logger = logging.getLogger(__name__)
_settings = settings.DatabaseSettings()

_engine = sqlalchemy.engine.create_engine(
    _settings.dsn,
    pool_recycle=90
)

_database_session = sqlalchemy.orm.sessionmaker(_engine)


def session() -> sqlalchemy.orm.Session:
    """
    Get an opened session to the database
    
    :return: The opened database session
    :rtype: sqlalchemy.orm.Session
    """
    _logger.debug('Creating new database session')
    _session: sqlalchemy.orm.Session = _database_session()
    try:
        _logger.debug('Yielding the opened database session')
        yield _session
    finally:
        _logger.debug('Closing the database session')
        _session.close()
        _logger.debug('Closed the database session')


def engine() -> sqlalchemy.engine.Engine:
    """
    Get the database engine
    
    :return: The database engine used to connect to the database
    :rtype: sqlalchemy.engine.Engine
    """

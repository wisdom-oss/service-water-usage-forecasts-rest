import logging

import sqlalchemy.engine

import settings

_logger = logging.getLogger(__name__)

_settings = settings.DatabaseSettings()

engine = sqlalchemy.engine.create_engine(_settings.dsn, pool_recycle=90)

"""This file will bootstrap the service and announce it at the service registry"""
import asyncio
import logging
import sys

import sqlalchemy_utils as db_utils
import uvicorn as uvicorn
from pydantic import ValidationError

import database.tables
import tools
from settings import *

if __name__ == "__main__":
    # Read the service settings
    _service_settings = ServiceSettings()
    # Configure the logging module
    logging.basicConfig(
        format="%(levelname)-8s | %(asctime)s | %(name)-25s | %(message)s",
        level=tools.resolve_log_level(_service_settings.logging_level),
    )
    # Log a startup message
    logging.info("Starting the %s service", _service_settings.name)
    logging.debug("Reading the settings for the AMQP connection")
    try:
        _amqp_settings = AMQPSettings()
    except ValidationError:
        logging.critical(
            "Unable to read the AMQP related settings. Please refer to the "
            "documentation for further instructions: AMQP_SETTINGS_INVALID"
        )
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the AMQP connection: %s", _amqp_settings
    )
    logging.debug("Reading the settings for the service registry connection")
    try:
        _registry_settings = ServiceRegistrySettings()
    except ValidationError:
        logging.critical(
            "Unable to read the service registry related settings. Please refer to "
            "the documentation for further instructions: "
            "SERVICE_REGISTRY_SETTINGS_INVALID"
        )
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the service registry connection: %s",
        _registry_settings,
    )
    logging.debug("Reading the settings for the database connection")
    try:
        _database_settings = DatabaseSettings()
    except ValidationError:
        logging.critical(
            "Unable to read the database related settings. Please refer to "
            "the documentation for further instructions: "
            "DATABASE_SETTINGS_INVALID"
        )
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the database connection: %s",
        _database_settings,
    )
    logging.debug("Reading the settings for the authorization mechanism")
    try:
        _security_settings = SecuritySettings()
    except ValidationError:
        logging.critical("Unable to read the settings for the security settings")
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the security measures: %s",
        _security_settings,
    )
    # = Service Registry Connection =
    logging.info("Checking the connection to the service registry")
    _registry_available = asyncio.run(
        tools.is_host_available(
            host=_registry_settings.host, port=_registry_settings.port
        )
    )
    if not _registry_available:
        logging.critical(
            "The service registry is not reachable. Therefore, this service is unable to register "
            "itself at the service registry and it is not callable"
        )
        sys.exit(2)
    # = AMQP Message Broker =
    logging.info("Checking the connection to the message broker")
    _message_broker_available = asyncio.run(
        tools.is_host_available(
            host=_amqp_settings.dsn.host,
            port=int(_amqp_settings.dsn.port)
            if _amqp_settings.dsn.port is not None
            else 5672,
        )
    )
    if not _message_broker_available:
        logging.critical(
            "The message broker is not reachable. Therefore, this service is unable to transmit "
            "the forecast requests to the calculation service."
        )
        sys.exit(2)
    # = Database connection =
    logging.info("Checking the connection to the database server")
    _database_available = asyncio.run(
        tools.is_host_available(
            host=_database_settings.dsn.host,
            port=3306
            if _database_settings.dsn.port is None
            else int(_database_settings.dsn.port),
        )
    )
    if not _database_available:
        logging.critical(
            "The database server is not reachable. Therefore, this service is unable to get water "
            "usages from the database"
        )
        sys.exit(2)
    # = Database existence check =
    if not db_utils.database_exists(_database_settings.dsn):
        logging.warning(
            "The specified datasource does not exist. Trying to create the database "
            "and populating it with example data"
        )
        try:
            db_utils.create_database(_database_settings.dsn)
        except Exception as db_error:
            logging.critical(
                "Failed to create the database due to the following error: %s", db_error
            )
            sys.exit(3)
        # Create the table metadata
        logging.info("Created the specified datasource")
        database.tables.initialize_tables()
    else:
        logging.info("Found an existing datasource which will be used")
    # Starting the uvicorn server
    uvicorn.run(
        **{
            "app": "api:service",
            "host": "0.0.0.0",
            "port": _service_settings.http_port,
            "log_level": "warning",
            "workers": 1,
        }
    )

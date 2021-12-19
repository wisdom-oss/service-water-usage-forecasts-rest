"""Bootstrap script for this service"""
import asyncio
import logging
import os
import sys

import pydantic.error_wrappers
from hypercorn import Config
from hypercorn.asyncio import serve

import api
from models import ServiceSettings

# Protect the script during import
if __name__ == '__main__':
    # Print a basic welcome message
    print('WISdoM OSS - Water Usage Forecast REST Service is starting')

    # Create the logger format for this service
    __LOGGER_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(lineno)s - %(message)s'
    """Logger format used throughout this service"""

    # Resolve the logging level from the environment variables
    __logger_level_raw = os.getenv("LOG_LEVEL", default="INFO").upper()
    __logger_level = getattr(logging, __logger_level_raw)

    # Configure the root logger with the format and the level
    logging.basicConfig(
        format=__LOGGER_FORMAT,
        level=__logger_level,
        force=True
    )

    # Create a logger for this bootstrap process
    __logger = logging.getLogger('BOOTSTRAP')

    # Try reading the settings from the environment
    __logger.debug('Trying to read the configuration from the environment variables')
    try:
        service_config = ServiceSettings()
    except pydantic.error_wrappers.ValidationError as validation_error:
        __logger.error(
            'The settings could not be read from the environment variables. More information '
            'about this error:\n%s', validation_error
        )
        sys.exit(1)

    # Create a configuration for the http server hosting the application
    hypercorn_config = Config()
    # Set the bind host
    hypercorn_config.bind = ["0.0.0.0:5000"]
    # Set the number of workers
    hypercorn_config.workers = 8

    asyncio.run(serve(api.water_usage_forecasts_rest, hypercorn_config))

else:
    raise Exception("This script may not be imported by other scripts or modules")

"""Module in which the server is described and all ops of the server are commenced in"""
import json
import logging
import uuid
from multiprocessing import Barrier
from pathlib import Path
from time import sleep
from typing import Optional

from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from py_eureka_client.eureka_client import EurekaClient
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import database
import exceptions
import models.requests.enums
from exceptions import QueryDataError
from api.functions import district_in_spatial_unit, get_water_usage_data
from database.tables.operations import get_commune_names, get_county_names
from messaging import AMQPRPCClient
from models import ServiceSettings
from models.requests import ForecastRequest
from models.requests.enums import ConsumerGroup, ForecastType, SpatialUnit

water_usage_forecasts_rest = FastAPI()
"""Fast API Application for this service"""
# Create a logger for the api implementation
__logger = logging.getLogger('API')
# Read the service settings again
__settings = ServiceSettings()
# Create a private empty service registry client
__service_registry_client: Optional[EurekaClient] = None
# Create a private AMQPClient
__amqp_client: Optional[AMQPRPCClient] = None


# Create a handler for the startup process
@water_usage_forecasts_rest.on_event('startup')
async def startup():
    """Startup Event Handler

    This event handler will automatically register this service at the service registry,
    create the necessary databases and tables and will start a rpc client which will send
    messages to the forecasting module

    :return:
    """
    __logger.info("Registering the service at the service registry")
    # Allow writing to the global client
    global __service_registry_client, __amqp_client
    # Create a new service registry client
    __service_registry_client = EurekaClient(
        eureka_server=f'http://{__settings.service_registry_url}',
        app_name='water-usage-forecasts-rest',
        instance_port=5000,
        should_register=True,
        renewal_interval_in_secs=5,
        duration_in_secs=10
    )
    # Start the service registry client
    __service_registry_client.start()
    # Initialize the ORM models
    database.initialise_orm_models()
    # Create the client
    __amqp_client = AMQPRPCClient(
        amqp_url=__settings.amqp_url,
        exchange_name='weather-forecast-requests'
    )


# Handler for the shutdown process
@water_usage_forecasts_rest.on_event('shutdown')
async def shutdown():
    """Shutdown event handler

    This event handler will deregister the service from the service registry

    :return:
    """
    global __service_registry_client
    __service_registry_client.stop()


# Handler for validation errors, meaning the request was bad
@water_usage_forecasts_rest.exception_handler(RequestValidationError)
async def request_validation_error_handler(__request: Request, exc: RequestValidationError):
    """
    Error handler for request validation errors

    These errors will occur if the request data is not valid. This error handler just changes the
    status from 422 (Unprocessable Entity) to 400 (Bad Request)
    """
    return JSONResponse(
        status_code=400,
        content={
            "errors": exc.errors()
        }
    )


# Handler for errors in data which were validated later on
@water_usage_forecasts_rest.exception_handler(QueryDataError)
async def query_data_error_handler(_request: Request, exc: QueryDataError):
    """Error handler for querying data which is not available

    This error handler will return a status code 400 (Bad Request) alongside with some
    information on the reason for the error
    """
    return JSONResponse(
        status_code=400,
        content={
            "error":             exc.short_error,
            "error_description": exc.error_description
        }
    )


# Handler for errors in data which were validated later on
@water_usage_forecasts_rest.exception_handler(exceptions.DuplicateEntryError)
async def query_data_error_handler(_request: Request, exc: exceptions.DuplicateEntryError):
    """Error handler for querying data which is not available

    This error handler will return a status code 400 (Bad Request) alongside with some
    information on the reason for the error
    """
    return Response(
        status_code=409
    )


# Route for generating a new request
@water_usage_forecasts_rest.get(path='/{spatial_unit}/{district}/{forecast_type}')
async def run_prognosis(
        spatial_unit: SpatialUnit,
        district: str,
        forecast_type: ForecastType,
        consumer_group: ConsumerGroup = Query(ConsumerGroup.ALL, alias='consumerGroup'),
        db_connection: Session = Depends(database.get_database_session)
):
    """Run a new prognosis

    :param spatial_unit: Selected spatial unit
    :type spatial_unit: SpatialUnit
    :param district: The district in the selected spatial unit
    :type district: str
    :param forecast_type: The model which shall be used during broadcasting
    :type forecast_type: ForecastType
    :param consumer_group: The consumer group whose water usages shall be predicted, defaults to all
    :type consumer_group: ConsumerGroup
    :param db_connection: Connection to the database used to do some queries
    :type db_connection: Session
    """
    __logger.info(
        'Got new request for forecast:Forecast type: %s, Spatial Unit: %s, District: %s, '
        'Consumer Group(s): %s',
        forecast_type, spatial_unit, district, consumer_group
    )
    # Check if the district is in the spatial unit
    if not district_in_spatial_unit(district, spatial_unit, db_connection):
        raise QueryDataError(
            "district_not_found",
            "The district '{}' was not found in the spatial unit '{}'. Please check your "
            'query'.format(district, spatial_unit)
        )
    # Get the water usage data
    __water_usage_data = get_water_usage_data(district, spatial_unit, db_connection, consumer_group)
    _request = ForecastRequest(
        time_period_start=__water_usage_data.time_period_start,
        time_period_end=__water_usage_data.time_period_end,
        water_usage_amounts=__water_usage_data.water_usage_amounts,
        forecast_type=forecast_type,
        consumer_group=consumer_group
    )
    # Publish the request

    __msg_id, __msg_received = __amqp_client.publish_message(_request)

    if __msg_received.wait():
        return json.loads(__amqp_client.responses[__msg_id])
    else:
        return JSONResponse(
            status_code=504,
            content={
                "error":             "timeout",
                "error_description": "While waiting for the response the internal messaging timed "
                                     "out"
            }
        )

@water_usage_forecasts_rest.put(
    path='/import/{datatype}',
    status_code=201
)
async def put_new_datafile(
        datatype: models.requests.enums.ImportDataTypes,
        data: UploadFile = File(...),
        db_connection: Session = Depends(database.get_database_session)
):
    """Import a new set of data into the database

    :param db_connection:
    :param datatype: The type of data which shall be imported
    :param data: The file which shall be imported
    :return: If the request was a success it will send a 201 code back
    """
    print(data.filename)
    # Create a file id
    file_id: str = uuid.uuid4().hex
    # Write the uploaded file into ./tmp/file_id.csv
    tmp_folder = Path('./.tmp')
    # Create the folder and ignore if it already exists
    tmp_folder.mkdir(parents=True, exist_ok=True)
    _tmp_file_name = f'./.tmp/{file_id}.csv'
    with open(_tmp_file_name, 'wb+') as tmp_file:
        tmp_file.write(await data.read())
    # Now check the datatype which shall be uploaded
    if datatype == models.requests.enums.ImportDataTypes.COMMUNES:
        database.imports.csv.import_communes_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.COUNTIES:
        database.imports.csv.import_counties_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.CONSUMER_TYPES:
        database.imports.csv.import_consumer_types_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.USAGES:
        database.imports.csv.import_water_usages_from_file(_tmp_file_name, db_connection)
    else:
        return Response(status_code=status.HTTP_501_NOT_IMPLEMENTED)


# Route for getting information about the possible parameters
@water_usage_forecasts_rest.get('/')
async def get_available_parameters(db: Session = Depends(database.get_database_session)):
    """Get all possible parameters

    :param db:
    :return:
    """
    response = {
        "communes": get_commune_names(db),
        "counties": get_county_names(db),
        "consumerGroups": list(ConsumerGroup.__members__.values()),
        "forecastTypes": list(ForecastType.__members__.values())
    }
    return response

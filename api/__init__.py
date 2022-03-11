"""Module in which the server is described and all ops of the server are commenced in"""
import json
import logging
import re
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
import imports
import models.requests.enums
from exceptions import QueryDataError
from api.functions import district_in_spatial_unit, get_water_usage_data
from database.tables.operations import get_commune_names, get_county_names
from messaging import AMQPRPCClient
from models.requests import ForecastRequest
from models.requests.enums import ConsumerGroup, ForecastType, SpatialUnit
from settings import *

water_usage_forecasts_rest = FastAPI()
"""Fast API Application for this service"""
# Create a logger for the api implementation
__logger = logging.getLogger('HTTP')
# Read all settings
_service_settings = ServiceSettings()
_registry_settings = ServiceRegistrySettings()
_amqp_settings = AMQPSettings()
_security_settings = SecuritySettings()
# Create a private empty service registry client
_registry_client: Optional[EurekaClient] = None
# Create a private AMQPClient
_amqp_client: Optional[AMQPRPCClient] = None
_amqp_security_client: Optional[AMQPRPCClient] = None


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
    global _registry_client, _amqp_client, _amqp_security_client
    # Create a new service registry client
    _registry_client = EurekaClient(
        eureka_server=f'http://{_registry_settings.host}:{_registry_settings.port}',
        app_name=_service_settings.name,
        instance_port=_service_settings.http_port,
        should_register=True,
        renewal_interval_in_secs=5,
        duration_in_secs=10
    )
    # Start the service registry client
    _registry_client.start()
    # Initialize the ORM models
    database.initialise_orm_models()
    # Create the client
    _amqp_client = AMQPRPCClient(
        amqp_url=_amqp_settings.dsn,
        exchange_name=_amqp_settings.exchange
    )
    _amqp_security_client = AMQPRPCClient(
        amqp_url=_amqp_settings.dsn,
        exchange_name=_security_settings.authorization_exchange
    )


# Handler for the shutdown process
@water_usage_forecasts_rest.on_event('shutdown')
async def shutdown():
    """Shutdown event handler

    This event handler will un-register the service from the service registry

    :return:
    """
    global _registry_client
    _registry_client.stop()


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


# ==== AUTHORIZATION MIDDLEWARE ====
@water_usage_forecasts_rest.middleware('http')
async def authenticate_token_for_application(request: Request, next_action):
    """This middleware will validate the Authorization token present in the headers and reject
    the request if none is present
    
    :param request:
    :return: The response
    """
    global _amqp_security_client
    # Get the authorization headers value
    header = request.headers.get('Authorization', None)
    if header is None:
        return Response(
            status_code=status.HTTP_400_BAD_REQUEST
        )
    else:
        _matcher_string = r"[Bb]earer ([0-9a-fA-F]{8}\b-(?:[0-9a-fA-F]{4}\b-){3}[0-9a-fA-F]{12})"
        if match := re.match(_matcher_string, header):
            token = match.group(1)
            _validation_request = {
                "action": "validate_token",
                "token": token,
                "scopes": "water-usage:forecasts"
            }
            print(_validation_request)
            __msg_id, __msg_received = _amqp_security_client.publish_message(json.dumps(
                _validation_request, ensure_ascii=False))
            if __msg_received.wait():
                _validation_response = json.loads(_amqp_security_client.responses[__msg_id])
                if _validation_response["active"] is True:
                    response = await next_action(request)
                    return response
                else:
                    return Response(
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
        else:
            return Response(
                status_code=status.HTTP_400_BAD_REQUEST
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

    __msg_id, __msg_received = _amqp_client.publish_message(_request.json())

    if __msg_received.wait():
        return json.loads(_amqp_client.responses[__msg_id])
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
        imports.csv.import_communes_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.COUNTIES:
        imports.csv.import_counties_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.CONSUMER_TYPES:
        imports.csv.import_consumer_types_from_file(_tmp_file_name, db_connection)
    elif datatype == models.requests.enums.ImportDataTypes.USAGES:
        imports.csv.import_water_usages_from_file(_tmp_file_name, db_connection)
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

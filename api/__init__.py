"""Module in which the server is described and all ops of the server are commenced in"""
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from py_eureka_client.eureka_client import EurekaClient
from sqlalchemy.orm import Session
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import amqp_rpc_client

import database
import exceptions
import imports
import models.requests.enums
from api.functions import district_in_spatial_unit, get_water_usage_data
from database.tables.operations import get_commune_names, get_county_names
from exceptions import QueryDataError
from models.amqp import TokenIntrospectionRequest, ForecastRequest, WaterUsages
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
_amqp_client: Optional[amqp_rpc_client.Client] = None


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
    global _registry_client, _amqp_client
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
    _amqp_client = amqp_rpc_client.Client(
        _amqp_settings.dsn
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
    # Access the request headers
    headers = request.headers
    # Check if a request id is present in the request to identify the request in the logs
    _request_id = headers.get('X-Request-ID', uuid.uuid4().hex)
    _request_host = request.client.host
    _request_host_port = request.client.port
    # Log that we received a new request
    __logger.info('%s:%s - %s - Received new request for executing a water usage forecast',
                  _request_id, _request_host, _request_host_port)
    __logger.info('%s:%s - %s - Checking if the request is authorized and has the correct scope')
    # Get the value stored in the Authorization header
    _authorization_header_value: Optional[str] = headers.get('Authorization', None)
    # Check if the header was even present
    if _authorization_header_value is None:
        __logger.warning('%s:%s - %s - [R] The request did not contain the necessary credentials',
                         _request_id, _request_host, _request_host_port)
        return JSONResponse(
            status_code=400,
            content={
                "error": "missing_authorization_header"
            },
            headers={
                'WWW-Authenticate': 'Bearer error="invalid_request"'
            }
        )
    # Check if the Authorization scheme is bearer
    if ("Bearer" or "bearer") not in _authorization_header_value:
        __logger.error('%s:%s - %s - [R] The request contained an unsupported authorization scheme',
                       _request_id, _request_host, _request_host_port)
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_authorization_scheme"
            },
            headers={
                'WWW-Authenticate': 'Bearer error="invalid_request"'
            }
        )
    # Remove the "Bearer" scheme from the header value
    _user_token = _authorization_header_value.lower().replace('bearer', '').strip()
    # Check if the bearer token is formatted like UUID
    try:
        uuid.UUID(_user_token)
    except ValueError:
        __logger.error('%s:%s - %s - [R] The Bearer token was malformed')
        return JSONResponse(
            status_code=400,
            content={
                "error": "bearer_token_malformed"
            },
            headers={
                'WWW-Authenticate': 'Bearer error="invalid_request"'
            }
        )
    __logger.info('%s:%s - %s - Requesting an introspection from the authorization service')
    # Request an introspection of the token from the authorization service
    _introspection_request = TokenIntrospectionRequest(
        bearer_token=_user_token
    )
    # Transmit the request using the rpc client
    _introspection_id = _amqp_client.send(
        content=_introspection_request.json(by_alias=True),
        exchange=_security_settings.authorization_exchange
    )
    __logger.debug('%s:%s - %s - Transmitted the introspection request (id: %s',
                   _request_host, _request_host_port, _request_id, _introspection_id)
    __logger.info('%s:%s - %s - Awaiting the introspection result from the authorization service',
                  _request_host, _request_host_port, _request_id)
    _introspection_response_bytes = _amqp_client.await_response(_introspection_id, timeout=10.0)
    if _introspection_response_bytes is None:
        __logger.error('%s:%s - %s - [R] The authorization service did not return an response in '
                       'a appropriate amount of time',
                       _request_host, _request_host_port, _request_id)
        return JSONResponse(
            status_code=504,
            content={
                "error": "token_introspection_timeout"
            },
            headers={
                'Retry-After': '10'
            }
        )
    # Convert the introspection response into a dictionary
    _introspection_response: dict = json.loads(_introspection_response_bytes)
    # Check if the response contains the active key
    if 'active' not in _introspection_response:
        __logger.critical('%s:%s - %s - [R] The authorization service did not return a valid '
                          'response',
                          _request_host, _request_host_port, _request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "token_introspection_failure"
            },
            headers={
                'Retry-After': '15'
            }
        )
    # Check if the active key indicated true
    if _introspection_response.get('active') is False:
        __logger.error('%s:%s - %s - The authorization service marked the bearer token as inactive',
                       _request_host, _request_host_port, _request_id)
        # Check if a generic answer is returned
        if 'reason' not in _introspection_response:
            return JSONResponse(
                status_code=401,
                content={
                    "error": 'invalid_token'
                },
                headers={
                    'WWW-Authenticate': 'Bearer error="invalid_token"'
                }
            )
        if _introspection_response.get('reason') == 'token_error':
            return JSONResponse(
                status_code=401,
                content={
                    "error": 'invalid_token'
                },
                headers={
                    'WWW-Authenticate': 'Bearer error="invalid_token"'
                }
            )
        if _introspection_response.get('reason') == 'insufficient_scope':
            return JSONResponse(
                status_code=403,
                content={
                    "error": 'insufficient_scope'
                },
                headers={
                    'WWW-Authenticate': 'Bearer error="insufficient_scope"'
                }
            )
        return JSONResponse(
            status_code=401,
            content={
                "error": 'invalid_token'
            },
            headers={
                'WWW-Authenticate': 'Bearer error="invalid_token"'
            }
        )
    # Since the token was validated successfully and is allowed to access this resource the
    # request may be executed
    return await next_action(request)
    

# Route for generating a new request
@water_usage_forecasts_rest.get(path='/{spatial_unit}/{forecast_type}')
async def run_prognosis(
        spatial_unit: SpatialUnit,
        forecast_type: ForecastType,
        districts: list[str] = Query(default=..., alias='district'),
        consumer_group: ConsumerGroup = Query(ConsumerGroup.ALL, alias='consumerGroup'),
        db_connection: Session = Depends(database.get_database_session)
):
    """Run a new prognosis

    :param spatial_unit: Selected spatial unit
    :type spatial_unit: SpatialUnit
    :param districts: The district in the selected spatial unit
    :type districts: str
    :param forecast_type: The model which shall be used during broadcasting
    :type forecast_type: ForecastType
    :param consumer_group: The consumer group whose water usages shall be predicted, defaults to all
    :type consumer_group: ConsumerGroup
    :param db_connection: Connection to the database used to do some queries
    :type db_connection: Session
    """
    __logger.info(
        'Got new request for forecast:Forecast type: %s, Spatial Unit: %s, Districts: %s, '
        'Consumer Group(s): %s',
        forecast_type, spatial_unit, districts, consumer_group
    )
    response_list = []
    for district in districts:
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
            type=forecast_type,
            usage_data=__water_usage_data
        )
        # Publish the request
    
        __msg_id = _amqp_client.send(_request.json(), _amqp_settings.exchange)
    
        byte_response = _amqp_client.await_response(__msg_id, timeout=60)
        
        if byte_response is not None:
            response = json.loads(byte_response)
            response.update({'name': district})
            response.update({'consumerGroup': consumer_group.value})
            response_list.append(response)
        else:
            response_list.append(
                {
                    "name": district,
                    "error": "calculation_module_response_timeout"
                }
            )
    return response_list


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

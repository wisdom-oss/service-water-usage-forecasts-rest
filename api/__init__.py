import asyncio
import datetime
import email.utils
import hashlib
import json
import logging
import re
import sys
import time
import typing
import urllib.parse
import uuid

import amqp_rpc_client
import fastapi.middleware.gzip
import fastapi.exceptions
import py_eureka_client.eureka_client
import pydantic
import pytz
import sqlalchemy.orm
import sqlalchemy_utils as db_utils
import starlette
import starlette.requests
import starlette.responses
import ujson as ujson
from pydantic import ValidationError

import api.functions
import database
import database.tables
import enums
import models.amqp
import settings

# Create a new logger for the api
import tools

_logger = logging.getLogger(__name__)
# Read the settings needed for the api (in this case all)
_service_settings = settings.ServiceSettings()
_registry_settings = settings.ServiceRegistrySettings()
_amqp_settings = settings.AMQPSettings()
_security_settings = settings.SecuritySettings()

# Create a new FastAPI Application for the service
service = fastapi.FastAPI()
service.add_middleware(fastapi.middleware.gzip.GZipMiddleware)

# Prepare global instances of the service registry client and the amqp client
_registry_client: typing.Optional[py_eureka_client.eureka_client.EurekaClient] = None
_amqp_client: typing.Optional[amqp_rpc_client.Client] = None

# ==== API Methods below this line  ====

# ===== Event Handler ======


@service.on_event("startup")
async def _service_startup():
    """Handler for the service startup"""
    # Read the service settings
    _service_settings = settings.ServiceSettings()
    # Configure the logging module
    logging.basicConfig(
        format="%(levelname)-8s | %(asctime)s | %(name)-25s | %(message)s",
        level=tools.resolve_log_level(_service_settings.logging_level),
    )
    # Log a startup message
    logging.info("Starting the %s service", _service_settings.name)
    logging.debug("Reading the settings for the AMQP connection")
    try:
        _amqp_settings = settings.AMQPSettings()
    except ValidationError:
        logging.critical(
            "Unable to read the AMQP related settings. Please refer to the "
            "documentation for further instructions: AMQP_SETTINGS_INVALID"
        )
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the AMQP connection: %s", _amqp_settings
    )
    logging.debug("Reading the settings for the database connection")
    try:
        _database_settings = settings.DatabaseSettings()
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
        _security_settings = settings.SecuritySettings()
    except ValidationError:
        logging.critical("Unable to read the settings for the security settings")
        sys.exit(1)
    logging.debug(
        "Successfully read the settings for the security measures: %s",
        _security_settings,
    )
    # = Service Registry Connection =

    # = AMQP Message Broker =
    logging.info("Checking the connection to the message broker")
    _message_broker_available = await tools.is_host_available(
        host=_amqp_settings.dsn.host,
        port=int(_amqp_settings.dsn.port)
        if _amqp_settings.dsn.port is not None
        else 5672,
    )
    if not _message_broker_available:
        logging.critical(
            "The message broker is not reachable. Therefore, this service is unable to transmit "
            "the forecast requests to the calculation service."
        )
        sys.exit(2)
    # = Database connection =
    logging.info("Checking the connection to the database server")
    _database_available = await tools.is_host_available(
        host=_database_settings.dsn.host,
        port=3306
        if _database_settings.dsn.port is None
        else int(_database_settings.dsn.port),
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
    _logger.info("Starting the RESTful API")
    _logger.debug("Accessing the global service registry client and AMQP RPC client")
    # Access the global service registry client and amqp rpc client
    global _registry_client, _amqp_client
    # Initialize a new service registry client
    _registry_client = py_eureka_client.eureka_client.EurekaClient(
        eureka_server=f"http://{_registry_settings.host}:{_registry_settings.port}/",
        app_name=_service_settings.name,
        instance_port=5000,
        should_register=True,
        should_discover=False,
        renewal_interval_in_secs=30,
        duration_in_secs=30,
    )
    # Initialize a new AMQP Client
    _amqp_client = amqp_rpc_client.Client(amqp_dsn=_amqp_settings.dsn, mute_pika=True)
    # Start the service registry client and register the service
    _registry_client.start()
    # Initialize the database table mappings
    database.tables.initialize_tables()
    _logger.info(
        "Pre-Startup tasks finished. Settings instance status to active and allowing "
        "requests"
    )
    _registry_client.status_update(py_eureka_client.eureka_client.INSTANCE_STATUS_UP)
    _logger.info("Waiting for new requests...")


# ===== Middlewares ======
@service.middleware("http")
async def _caching_check(request: starlette.requests.Request, call_next):
    # Get the forecast parameters
    request_path = request.url.path
    raw_request_parameter = str(request.query_params)
    # Now parse the raw request parameters
    request_parameter = urllib.parse.parse_qs(raw_request_parameter)
    forecast_spatial_unit = request_path.split("/")[1]
    forecast_model = request_path.split("/")[2]
    forecast_districts = request_parameter.get("district", [])
    forecast_consumer_groups = request_parameter.get("consumerGroup", [])
    # Now sort the districts and consumer groups
    forecast_districts = sorted(forecast_districts)
    forecast_consumer_groups = sorted(forecast_consumer_groups)
    # Now put that all into a dict
    forecast_parameter = {
        "spatialUnit": forecast_spatial_unit,
        "forecastModel": forecast_model,
        "districts": forecast_districts,
        "consumerGroups": forecast_consumer_groups,
    }
    # Now jsonify the parameters
    forecast_parameter_json = json.dumps(
        forecast_parameter, ensure_ascii=False, sort_keys=False
    )
    # Now create the hashsum of the parameters
    forecast_request_hash = hashlib.md5(
        forecast_parameter_json.encode("utf-8")
    ).hexdigest()
    # Now get the time of the last update to any of the tables in the system
    last_database_update = functions.get_last_database_update(
        "water_usage", database.engine
    )
    # Now get the value of the "If-None-Match" and "If-Modified-Since" headers
    e_tag = request.headers.get("If-None-Match")
    data_last_modification = request.headers.get("If-Modified-Since")
    # Now parse the last_update to a python datetime object
    if data_last_modification is None:
        last_known_update = datetime.datetime.fromtimestamp(0, tz=pytz.UTC)
    else:
        last_known_update = email.utils.parsedate_to_datetime(data_last_modification)
    e_tag_matches_request = e_tag == forecast_request_hash
    database_updated = last_known_update < last_database_update
    if e_tag_matches_request and not database_updated:
        return starlette.responses.Response(
            status_code=304,
            headers={
                "ETag": forecast_request_hash,
                "Last-Modified": email.utils.format_datetime(last_database_update),
            },
        )
    request_response: starlette.responses.Response = await call_next(request)
    request_response.headers.append("ETag", forecast_request_hash)
    request_response.headers.append(
        "Last-Modified", email.utils.format_datetime(last_database_update)
    )
    return request_response


@service.middleware("http")
async def _token_check(request: starlette.requests.Request, call_next):
    """
    Intercept every request made to this service and check if the request contains a Bearer token
    and check if the bearer token has the correct scope for this service

    :param request: The incoming request
    :type request: starlette.requests.Request
    :param call_next: The next action which shall be called to generate the response
    :type call_next: callable
    :return: The response which has been generated
    :rtype: starlette.responses.Response
    """
    global _amqp_client
    # Access the headers of the incoming request
    headers = request.headers
    # Get the value of the Authorization header
    authorization_header: typing.Optional[str] = headers.get("Authorization")
    if authorization_header is None:
        # Since no authorization header was set return a response indicating this error
        return starlette.responses.Response(
            status_code=400,
            headers={"WWW-Authenticate": "Bearer error=invalid_request"},
        )
    # Strip any excess whitespaces from the header
    authorization_header = authorization_header.strip()
    # Since an Authorization header was found check if the header has a value
    if len(authorization_header) == 0:
        # Since the header has no value. Indicate that the request was invalid
        return starlette.responses.Response(
            status_code=400,
            headers={"WWW-Authenticate": "Bearer error=invalid_request"},
        )
    # Now check if the Authorization header either starts with "Bearer" or "bearer" or any lower
    # and uppercase variant
    if not re.match("Bearer", authorization_header, re.IGNORECASE):
        # Since the header contained an unsupported authorization scheme, inform the client of
        # this error
        return starlette.responses.Response(
            status_code=400,
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_request",'
                'error_description="Unsupported authorization scheme"'
            },
        )
    # Since the header contained Bearer as authorization method extract the Bearer token from the
    # header
    bearer_token = authorization_header.lower().replace("bearer", "").strip()
    # Now check if the bearer token is formatted like a UUID, which is the format issued by the
    # authorization service
    try:
        _ = uuid.UUID(bearer_token)
    except ValueError:
        # Since the bearer token could not be converted to an uuid return a error to the end user
        return starlette.responses.Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    # Since the bearer token passed all checks send a introspection request to determine if the
    # token has the correct scope for accessing this service
    introspection_request = models.amqp.TokenIntrospectionRequest(
        bearer_token=bearer_token
    )
    # Try sending the request and check for any errors which may occur
    try:
        _introspection_request_id = _amqp_client.send(
            introspection_request.json(by_alias=True),
            _security_settings.authorization_exchange,
        )
    except Exception:
        _logger.warning(
            "A error occurred while sending the token introspection request. Trying "
            "again with a new AMQP RPC Client"
        )
        _amqp_client = amqp_rpc_client.Client(
            amqp_dsn=_amqp_settings.dsn, mute_pika=True
        )
        _introspection_request_id = _amqp_client.send(
            introspection_request.json(by_alias=True),
            _security_settings.authorization_exchange,
        )
    # Wait a maximum amount of five seconds for the response
    raw_introspection_response = _amqp_client.await_response(
        _introspection_request_id, timeout=5
    )
    if raw_introspection_response is None:
        return starlette.responses.JSONResponse(
            status_code=503,
            content={
                "error": "token_introspection_timeout",
                "error_description": "The Bearer token included in the request could not be "
                "validated in a appropriate amount of time. Please try again "
                "later",
            },
            headers={"Retry-After": "30"},
        )
    # Since a response was returned try to parse it into a JSON object
    try:
        introspection_response: dict = json.loads(raw_introspection_response)
    except json.JSONDecodeError:
        return starlette.responses.JSONResponse(
            status_code=503,
            content={
                "error": "token_introspection_error",
                "error_description": "The token introspection could not be read successfully. The "
                "request is cancelled to secure the service",
            },
            headers={"Retry-After": "30"},
        )
    # Now check if the response indicates if the token is valid
    token_valid = introspection_response.get("active", None)
    if token_valid is None:
        return starlette.responses.JSONResponse(
            status_code=503,
            content={
                "error": "token_introspection_error",
                "error_description": "The token introspection could not be read successfully. The "
                "request is cancelled to secure the service",
            },
            headers={"Retry-After": "30"},
        )
    if token_valid is not True:
        return starlette.responses.Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    # Since the token is valid let the request continue and return the response
    request_response = await call_next(request)
    return request_response


# ===== Routes =====


@service.get(path="/{spatial_unit}/{forecast_model}")
async def forecast(
    spatial_unit: enums.SpatialUnit,
    forecast_model: enums.ForecastModel,
    districts: list[str] = fastapi.Query(default=..., alias="district"),
    consumer_groups: list[str] = fastapi.Query(default=None, alias="consumerGroup"),
):
    """
    Execute a new forecast

    :param spatial_unit: The spatial unit used for the request
    :type spatial_unit: enums.SpatialUnit
    :param forecast_model: The forecast model which shall be used
    :type forecast_model: enums.ForecastModel
    :param districts: The districts that shall be used for the forecasts
    :type districts: list[str]
    :param consumer_groups: Consumer Groups which shall be included in the forecasts. If no
        consumer group was transmitted the forecast will be executed for all consumer groups and
        values with no consumer groups
    :type consumer_groups: list[str], optional
    :param session: The session used to access the database
    :type session: sqlalchemy.orm.Session
    :return: A list with the results of the forecast
    :rtype: list[dict]
    """
    # Save the current time to add it to the response headers
    forecast_start = time.time()
    # Check if the spatial unit is for the municipalities or the districts
    try:
        forecast_query = models.amqp.ForecastQuery(
            granularity=spatial_unit,
            model=forecast_model,
            objects=districts,
            consumer_groups=consumer_groups,
        )
    except pydantic.ValidationError as e:
        print(e.json())
        return e.json()
    _query_id = _amqp_client.send(
        forecast_query.json(by_alias=True), _amqp_settings.exchange
    )
    query_wait_time_start = time.time()
    _query_response = _amqp_client.await_response(_query_id, timeout=90)
    query_wait_time_stop = time.time()
    if _query_response is None:
        return starlette.responses.Response(status_code=412)
    return starlette.responses.Response(
        status_code=200,
        headers={
            "X-Forecast-Duration": str(time.time() - forecast_start),
            "X-AMQP-WaitTime": str(query_wait_time_stop - query_wait_time_start),
        },
        content=_query_response,
        media_type="text/json",
    )

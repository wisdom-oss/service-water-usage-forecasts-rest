import datetime
import email.utils
import hashlib
import json
import logging
import re
import sys
import time
import typing
import uuid

import amqp_rpc_client
import fastapi.exceptions
import fastapi.middleware.gzip
import py_eureka_client.eureka_client
import pydantic
import pytz
import sqlalchemy_utils as db_utils
import starlette
import starlette.requests
import starlette.responses
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
async def etag_comparison(request: starlette.requests.Request, call_next):
    """
    A middleware which will hash the request path and all parameters transferred to this
    microservice and will check if the hash matches the one of the ETag which was sent to the
    microservice. Furthermore, it will take the generated hash and append it to the response to
    allow caching

    :param request: The incoming request
    :type request: starlette.requests.Request
    :param call_next: The next call after this middleware
    :type call_next: callable
    :return: The result of the next call after this middle ware
    :rtype: starlette.responses.Response
    """
    # Access all parameters used for creating the hash
    path = request.url.path
    query_parameter = dict(request.query_params)
    content_type = request.headers.get("Content-Type", "text/plain")

    if content_type == "application/json":
        try:
            body = json.loads(await request.body())
        except json.JSONDecodeError as error:
            body = (await request.body()).decode("utf-8")
    else:
        body = (await request.body()).decode("utf-8")

    # Now iterate through all query parameters and make sure they are sorted if they are lists
    for key, value in dict(query_parameter).items():
        # Now check if the value is a list
        if isinstance(value, list):
            query_parameter[key] = sorted(value)

    query_dict = {
        "request_path": path,
        "request_query_parameter": query_parameter,
        "request_body": body,
    }
    query_data = json.dumps(query_dict, ensure_ascii=False, sort_keys=True)
    # Now create a hashsum of the query data
    query_hash = hashlib.sha3_256(query_data.encode("utf-8"))
    # Now access the headers of the request and check for the If-None-Match Header
    if_none_match_value = request.headers.get("If-None-Match")
    if_modified_since_value = request.headers.get("If-Modified-Since")
    if if_modified_since_value is None:
        if_modified_since_value = datetime.datetime.fromtimestamp(0, tz=pytz.UTC)
    else:
        if_modified_since_value = email.utils.parsedate_to_datetime(
            if_modified_since_value
        )
    last_database_modification = functions.get_last_database_update(
        "water_usage", database.engine
    )
    data_has_changed = if_modified_since_value < last_database_modification
    if query_hash == if_none_match_value and not data_has_changed:
        return starlette.responses.Response(
            status_code=304, headers={"ETag": f'"{query_hash}"'}
        )
    else:
        response: starlette.responses.Response = await call_next(request)
        response.headers.append("ETag", f'"{query_hash}"')
        response.headers.append(
            "Last-Modified", email.utils.format_datetime(last_database_modification)
        )
        return response


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
        return fastapi.responses.UJSONResponse(
            status_code=400,
            headers={"WWW-Authenticate": 'Bearer error="invalid_request"'},
            content={
                "httpCode": 400,
                "httpError": "Bad Request",
                "error": _service_settings.name + ".MISSING_CREDENTIALS",
                "errorName": "Unauthorized Request",
                "errorDescription": "The request did not contain any valid authorization "
                "information",
            },
        )
    # Strip any excess whitespaces from the header
    authorization_header = authorization_header.strip()
    # Since an Authorization header was found check if the header has a value
    if len(authorization_header) == 0:
        # Since the header has no value. Indicate that the request was invalid
        return fastapi.responses.UJSONResponse(
            status_code=400,
            headers={"WWW-Authenticate": 'Bearer error="invalid_request"'},
            content={
                "httpCode": 400,
                "httpError": "Bad Request",
                "error": _service_settings.name + ".BAD_AUTHORIZATION_HEADER",
                "errorName": "Unauthorized Request",
                "errorDescription": "The request did contain an empty authorization header",
            },
        )
    # Now check if the Authorization header either starts with "Bearer" or "bearer" or any lower
    # and uppercase variant
    if not re.match("Bearer", authorization_header, re.IGNORECASE):
        # Since the header contained an unsupported authorization scheme, inform the client of
        # this error
        return fastapi.responses.UJSONResponse(
            status_code=400,
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_request",'
                'error_description="Unsupported authorization scheme"'
            },
            content={
                "httpCode": 400,
                "httpError": "Bad Request",
                "error": _service_settings.name + ".INVALID_AUTHORIZATION_SCHEME",
                "errorName": "Unauthorized Request",
                "errorDescription": "The request did contain an recognized authorization scheme",
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
        return fastapi.responses.UJSONResponse(
            status_code=400,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            content={
                "httpCode": 400,
                "httpError": "Bad Request",
                "error": _service_settings.name + ".INVALID_TOKEN_FORMAT",
                "errorName": "Unauthorized Request",
                "errorDescription": "The request did contain an correctly formatted bearer token",
            },
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
        return fastapi.responses.UJSONResponse(
            status_code=500,
            content={
                "httpCode": 500,
                "httpError": "Internal Server Error",
                "error": _service_settings.name + ".TOKEN_INTROSPECTION_TIMEOUT",
                "errorName": "Token Introspection Timeout",
                "errorDescription": "The token could not be validated in a appropriate amount of "
                "time",
            },
            headers={"Retry-After": "30"},
        )
    # Since a response was returned try to parse it into a JSON object
    try:
        introspection_response: dict = json.loads(raw_introspection_response)
    except json.JSONDecodeError:
        return fastapi.responses.UJSONResponse(
            status_code=500,
            content={
                "httpCode": 500,
                "httpError": "Internal Server Error",
                "error": _service_settings.name + ".TOKEN_INTROSPECTION_ERROR",
                "errorName": "Token Introspection Timeout",
                "errorDescription": "The token introspection did not return a valid response",
            },
        )
    # Now check if the response indicates if the token is valid
    token_valid = introspection_response.get("active", None)
    if token_valid is None:
        return fastapi.responses.UJSONResponse(
            status_code=500,
            content={
                "httpCode": 500,
                "httpError": "Internal Server Error",
                "error": _service_settings.name + ".TOKEN_INTROSPECTION_ERROR",
                "errorName": "Token Introspection Timeout",
                "errorDescription": "The token introspection did not return a valid response",
            },
            headers={"Retry-After": "30"},
        )
    if token_valid is not True:
        error_reason = introspection_response.get("reason", None)
        if error_reason is None:
            return fastapi.responses.UJSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
                content={
                    "httpCode": 401,
                    "httpError": "Unauthorized",
                    "error": _service_settings.name + ".UNAUTHORIZED_REQUEST",
                    "errorName": "Unauthorized Request",
                    "errorDescription": "The request did not contain any valid authorization "
                    "information",
                },
            )
        elif error_reason == "token_expired":
            return fastapi.responses.UJSONResponse(
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
                content={
                    "httpCode": 401,
                    "httpError": "Unauthorized",
                    "error": _service_settings.name + ".ACCESS_TOKEN_EXPIRED",
                    "errorName": "Unauthorized Request",
                    "errorDescription": "The request did not contain a active bearer token",
                },
            )

    # Since the token is valid let the request continue and return the response
    request_response = await call_next(request)
    return request_response


# ===== Routes =====


@service.get(path="/{forecast_model}")
async def forecast(
    forecast_model: enums.ForecastModel,
    keys: list[str] = fastapi.Query(default=..., alias="key"),
    consumer_groups: list[str] = fastapi.Query(default=None, alias="consumerGroup"),
):
    """
    Execute a new forecast

    :param forecast_model: The forecast model which shall be used
    :type forecast_model: enums.ForecastModel
    :param keys: The districts that shall be used for the forecasts
    :type keys: list[int]
    :param consumer_groups: Consumer Groups which shall be included in the forecasts. If no
        consumer group was transmitted the forecast will be executed for all consumer groups and
        values with no consumer groups
    :type consumer_groups: list[str], optional
    :return: A list with the results of the forecast
    :rtype: list[dict]
    """
    # Save the current time to add it to the response headers
    forecast_start = time.time()
    # Check if the spatial unit is for the municipalities or the districts
    try:
        forecast_query = models.amqp.ForecastQuery(
            model=forecast_model,
            keys=keys,
            consumer_groups=consumer_groups,
        )
    except pydantic.ValidationError as e:
        return fastapi.responses.UJSONResponse(
            status_code=400,
            content={
                "httpCode": 400,
                "httpError": "Bad Request",
                "error": _service_settings.name + ".FORECAST_QUERY_PARAMETER_ERROR",
                "errorName": "Forecast Query parameter error",
                "errorDescription": str(e.raw_errors[0].exc),
            },
        )
    _query_id = _amqp_client.send(
        forecast_query.json(by_alias=True), _amqp_settings.exchange
    )
    _query_response = _amqp_client.await_response(_query_id, timeout=120)
    if _query_response is None:
        return fastapi.responses.UJSONResponse(
            status_code=500,
            content={
                "httpCode": 500,
                "httpError": "Internal Server Error",
                "error": _service_settings.name + ".FORECAST_CALCULATION_TIMEOUT",
                "errorName": "Forecast calculation Timeout",
                "errorDescription": "The calculation of the forecasted data took too long",
            },
            headers={"Retry-After": "30"},
        )
    return starlette.responses.Response(
        status_code=200,
        content=_query_response,
        media_type="text/json",
    )

import datetime
import email.utils
import hashlib
import json
import logging
import re
import time
import typing
import urllib.parse
import uuid
import pytz

import amqp_rpc_client
import fastapi.exceptions
import py_eureka_client.eureka_client
import sqlalchemy.orm
import starlette
import starlette.requests
import starlette.responses

import api.functions
import database
import database.crud
import database.tables
import enums
import exceptions
import models.amqp
import settings

# Create a new logger for the api
_logger = logging.getLogger(__name__)
# Read the settings needed for the api (in this case all)
_service_settings = settings.ServiceSettings()
_registry_settings = settings.ServiceRegistrySettings()
_amqp_settings = settings.AMQPSettings()
_security_settings = settings.SecuritySettings()

# Create a new FastAPI Application for the service
service = fastapi.FastAPI()

# Prepare global instances of the service registry client and the amqp client
_registry_client: typing.Optional[py_eureka_client.eureka_client.EurekaClient] = None
_amqp_client: typing.Optional[amqp_rpc_client.Client] = None

# ==== API Methods below this line  ====

# ===== Event Handler ======


@service.on_event("startup")
def _service_startup():
    """Handler for the service startup"""
    _logger.info("Starting the RESTful API")
    _logger.debug("Accessing the global service registry client and AMQP RPC client")
    # Access the global service registry client and amqp rpc client
    global _registry_client, _amqp_client
    # Initialize a new service registry client
    _registry_client = py_eureka_client.eureka_client.EurekaClient(
        eureka_server=f"http://{_registry_settings.host}:{_registry_settings.port}/",
        app_name=_service_settings.name,
        instance_port=_service_settings.http_port,
        should_register=True,
        should_discover=False,
        renewal_interval_in_secs=1,
        duration_in_secs=30,
    )
    # Initialize a new AMQP Client
    _amqp_client = amqp_rpc_client.Client(amqp_dsn=_amqp_settings.dsn, mute_pika=True)
    # Start the service registry client and register the service
    _registry_client.start()
    # Initialize the database table mappings
    database.tables.initialize_mappings()
    _logger.info(
        "Pre-Startup tasks finished. Settings instance status to active and allowing "
        "requests"
    )
    _registry_client.status_update(py_eureka_client.eureka_client.INSTANCE_STATUS_UP)
    _logger.info('Waiting for new requests...')


@service.on_event("shutdown")
def _service_shutdown():
    """Handle the service shutdown"""
    # Inform the service registry that the service is going offline and stop the eureka client
    _registry_client.stop()


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
        "water_usage", database.engine()
    )
    # Make the database update time timezone aware
    last_database_update = pytz.UTC.localize(last_database_update)
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
    session: sqlalchemy.orm.Session = fastapi.Depends(database.session),
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
    # Create an empty list containing the forecast results
    forecast_results = []
    # Create a dictionary for collecting all sent forecast calculation requests
    calculation_requests = {}
    # Check if the spatial unit is for the municipalities or the districts
    if spatial_unit == enums.SpatialUnit.DISTRICTS:
        districts = [m.name for m in database.crud.get_municipals_in_districts(districts, session)]
        logging.debug('Found the following municipals: %s', districts)
    for district in districts:
        if database.crud.get_municipal(district, session) is None:
            # Since the municipal is not in the database add this as a hint to the responses
            forecast_results.append(
                {
                    "name": district,
                    "error": "no_such_municipal",
                }
            )
        else:
            # Now iterate through the consumer groups that were sent and filter those not in the
            # database
            if consumer_groups is None:
                consumer_groups = [
                    c.parameter for c in database.crud.get_consumer_groups(session)
                ]
            for consumer_group in consumer_groups:
                if database.crud.get_consumer_group(consumer_group, session) is None:
                    forecast_results.append(
                        {
                            "name": district,
                            "consumerGroup": consumer_group,
                            "error": "missing_consumer_group",
                        }
                    )
                else:
                    # Since the district and consumer group is in the database get the water
                    # usages for the consumer group
                    consumer_group_id = database.crud.get_consumer_group(
                        consumer_group, session
                    ).id
                    municipal_id = database.crud.get_municipal(district, session).id
                    try:
                        usage_data = functions.get_water_usage_data(
                            municipal_id, consumer_group_id, session
                        )

                    except exceptions.InsufficientDataError:
                        forecast_results.append(
                            {
                                "name": district,
                                "consumerGroup": consumer_group,
                                "error": "insufficient_data",
                            }
                        )
                        continue
                    # Now generate a new request
                    forecast_request = models.amqp.ForecastRequest(
                        usage_data=usage_data, type=forecast_model
                    )
                    # Now publish the forecast request
                    forecast_request_id = _amqp_client.send(
                        forecast_request.json(), _amqp_settings.exchange
                    )
                    # Store the forecast request id and the consumer group and district
                    forecast_data = {
                        "consumer_group": consumer_group,
                        "municipal": district,
                    }
                    calculation_requests.update({forecast_request_id: forecast_data})
                    _logger.info('[-->] Published Forecast Request:\n%s\n%s', forecast_request_id, forecast_data)
                    # Now check if any response has already been sent
                    for request_id, request_data in dict(calculation_requests).items():
                        byte_response = _amqp_client.get_response(request_id)
                        if byte_response is not None:
                            response: dict = json.loads(byte_response)
                            # Now add the name and the consumer group to the response
                            response.update(
                                {
                                    "name": request_data["municipal"],
                                    "consumerGroup": request_data["consumer_group"],
                                }
                            )
                            # Now add the response to the list of responses
                            forecast_results.append(response)
                            calculation_requests.pop(request_id)
    while len(calculation_requests) > 0:
        for request_id, request_data in dict(calculation_requests).items():
            byte_response = _amqp_client.await_response(request_id, timeout=5.0)
            if byte_response is not None:
                _logger.warning('Exceeded maximum waiting time for response to the following request: \n%s\n%s, ', request_id, request_data)
                response: dict = json.loads(byte_response)
                # Now add the name and the consumer group to the response
                response.update(
                    {
                        "name": request_data["municipal"],
                        "consumerGroup": request_data["consumer_group"],
                    }
                )
                # Now add the response to the list of responses
                forecast_results.append(response)
                calculation_requests.pop(request_id)
            else:
                forecast_results.append(
                    {
                        "name": request_data["municipal"],
                        "consumerGroup": request_data["consumer_group"],
                        "error": "calculation_module_timeout",
                    }
                )
    return starlette.responses.JSONResponse(
        status_code=200,
        headers={"X-Forecast-Duration": str(time.time() - forecast_start)},
        content=forecast_results,
    )

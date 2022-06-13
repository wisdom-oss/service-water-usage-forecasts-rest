"""Package containing the code which will be the API later on"""
import datetime
import email.utils
import hashlib
import http
import logging
import typing

import amqp_rpc_client
import fastapi
import pydantic
import pytz as pytz
import redis
import sqlalchemy.exc
import orjson
import starlette.responses

import api.handler
import configuration
import database
import enums
import exceptions
import models.amqp
import models.internal
import tools
from . import security

# %% Global Clients
_amqp_client: typing.Optional[amqp_rpc_client.Client] = None
_redis_client: typing.Union[None, redis.Redis] = None

# %% API Setup
service = fastapi.FastAPI()
service.add_exception_handler(exceptions.APIException, api.handler.handle_api_error)
service.add_exception_handler(
    fastapi.exceptions.RequestValidationError,
    api.handler.handle_request_validation_error,
)
service.add_exception_handler(sqlalchemy.exc.IntegrityError, api.handler.handle_integrity_error)

# %% Configurations
_security_configuration = configuration.SecurityConfiguration()
_amqp_configuration = configuration.AMQPConfiguration()
_redis_configuration = configuration.RedisConfiguration()
_service_configuration = configuration.ServiceConfiguration()


# %% Mappings for responses
__forecast_request_user: typing.Dict[str, models.internal.UserAccount] = {}
__awaiting_forecasts = []
__received_responses: typing.Dict[str, bytes] = {}


# %% Event Handlers
@service.on_event("startup")
def create_amqp_client():
    global _amqp_client, _security_configuration, _redis_client
    _amqp_client = amqp_rpc_client.Client(amqp_dsn=_amqp_configuration.dsn, mute_pika=True)
    if _security_configuration.scope_string_value is None:
        service_scope = models.internal.ServiceScope.parse_file("./configuration/scope.json")
        _security_configuration.scope_string_value = service_scope.value
    if _redis_configuration.use_redis:
        _redis_client = redis.Redis.from_url(_redis_configuration.dsn)


# %% Middlewares
@service.middleware("http")
async def etag_comparison(request: fastapi.Request, call_next):
    """
    A middleware which will hash the request path and all parameters transferred to this
    microservice and will check if the hash matches the one of the ETag which was sent to the
    microservice. Furthermore, it will take the generated hash and append it to the response to
    allow caching

    :param request: The incoming request
    :type request: fastapi.Request
    :param call_next: The next call after this middleware
    :type call_next: callable
    :return: The result of the next call after this middle ware
    :rtype: fastapi.Response
    """
    # Access all parameters used for creating the hash
    path = request.url.path
    query_parameter = dict(request.query_params)
    # Now iterate through all query parameters and make sure they are sorted if they are lists
    for key, value in dict(query_parameter).items():
        # Now check if the value is a list
        if isinstance(value, list):
            query_parameter[key] = sorted(value)
    query_dict = {
        "request_path": path,
        "request_query_parameter": query_parameter,
    }
    query_data = orjson.dumps(query_dict, option=orjson.OPT_SORT_KEYS)
    # Now create a hashsum of the query data
    query_hash = hashlib.sha3_256(query_data).hexdigest()
    # Create redis keys for later usage
    response_cache_key = _service_configuration.name + ".data." + query_hash
    response_change_cache_key = _service_configuration.name + ".last_change." + query_hash
    # Now access the headers of the request and check for the If-None-Match Header
    e_tag = request.headers.get("If-None-Match", None)
    last_known_update = request.headers.get("If-Modified-Since", _redis_client.get(response_change_cache_key))
    if last_known_update is None:
        last_known_update = datetime.datetime.fromtimestamp(0, tz=pytz.UTC)
    else:
        if type(last_known_update) is bytes:
            last_known_update = email.utils.parsedate_to_datetime(last_known_update.decode("utf-8"))
        else:
            last_known_update = email.utils.parsedate_to_datetime(last_known_update)
    # Get the last update of the schema from which the service gets its data from
    last_database_modification = tools.get_last_schema_update("water_usage", database.engine)
    data_changed = last_known_update < last_database_modification
    if data_changed:
        response: starlette.responses.StreamingResponse = await call_next(request)
        if response.status_code == 200:
            _redis_client.set(response_change_cache_key, email.utils.format_datetime(last_database_modification))
            response_content = [chunk async for chunk in response.body_iterator][0].decode("utf-8")
            _redis_client.set(response_cache_key, response_content)
            response.headers.append("ETag", f"{query_hash}")
            response.headers.append("Last-Modified", email.utils.format_datetime(last_database_modification))
            return fastapi.Response(
                content=response_content,
                headers={
                    "E-Tag": query_hash,
                    "Last-Modified": email.utils.format_datetime(last_database_modification),
                    "X-Delivered-By": "Calculation Module",
                    "X-Reason": "Database Content Changed",
                },
                media_type="text/json",
            )
        return response
    if _redis_client.get(response_cache_key) is None:
        response: starlette.responses.StreamingResponse = await call_next(request)
        if response.status_code == 200:
            _redis_client.set(response_change_cache_key, email.utils.format_datetime(last_database_modification))
            response_content = [chunk async for chunk in response.body_iterator][0].decode("utf-8")
            _redis_client.set(response_cache_key, response_content)
            response.headers.append("ETag", f"{query_hash}")
            response.headers.append("Last-Modified", email.utils.format_datetime(last_database_modification))
            return fastapi.Response(
                content=response_content,
                headers={
                    "E-Tag": query_hash,
                    "Last-Modified": email.utils.format_datetime(last_database_modification),
                    "X-Delivered-By": "Calculation Module",
                    "X-Reason": "No response in Redis",
                },
                media_type="text/json",
            )
        return response
    else:
        # Authorize the user before sending the response
        user: models.internal.UserAccount = fastapi.Security(
            security.is_authorized_user, scopes=[_security_configuration.scope_string_value]
        )
        return fastapi.Response(
            content=_redis_client.get(response_cache_key),
            headers={
                "E-Tag": query_hash,
                "Last-Modified": email.utils.format_datetime(last_database_modification),
                "X-Delivered-By": "Redis",
            },
            media_type="text/json",
        )


# %% Routes
@service.get("/{forecast_model}")
async def forecast(
    forecast_model: enums.ForecastModel,
    keys: list[str] = fastapi.Query(default=..., alias="key"),
    consumer_groups: list[str] = fastapi.Query(default=None, alias="consumerGroup"),
    user: models.internal.UserAccount = fastapi.Security(
        security.is_authorized_user, scopes=[_security_configuration.scope_string_value]
    ),
):
    logging.info(f"Got new request. Authorization info: {user}")
    try:
        calculation_request = models.amqp.CalculationRequest(
            model=forecast_model, keys=keys, consumer_groups=consumer_groups
        )
    except pydantic.ValidationError as e:
        raise exceptions.APIException(
            error_code="FORECAST_PARAMETER_ERROR",
            error_title="Forecast parameter error",
            error_description=f"The forecast parameters contained errors: {str(e)}",
        )
    logging.info("Sending calculation request to the calculation service")
    _forecast_id = _amqp_client.send(
        calculation_request.json(by_alias=True), _amqp_configuration.exchange, "forecast-requests"
    )
    logging.info("Awaiting the response for the forecast")
    _forecast = _amqp_client.await_response(_forecast_id, timeout=120.0)
    if _forecast is None:
        logging.warning(
            "Got no response in the last 120.0 seconds. Returning the forecast id to allow pull of result "
            "when the result was received"
        )
        raise exceptions.APIException(
            error_code="FORECAST_CALCULATION_TIMEOUT",
            error_title="Forecast calculation timeout",
            error_description="The calculation module did not send a response in the last two minutes",
            http_status=http.HTTPStatus.GATEWAY_TIMEOUT,
        )
    return fastapi.Response(
        content=_forecast,
        media_type="text/json",
        headers={"X-Forecast-ID": _forecast_id},
    )

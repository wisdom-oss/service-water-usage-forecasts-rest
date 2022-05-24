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
import ujson

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
    content_type = request.headers.get("Content-Type", "text/plain")
    if content_type == "application/json":
        try:
            body = ujson.loads(await request.body())
        except ValueError as error:
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
    query_data = ujson.dumps(query_dict, ensure_ascii=False, sort_keys=True)
    # Now create a hashsum of the query data
    query_hash = hashlib.sha3_256(query_data.encode("utf-8")).hexdigest()
    # Now access the headers of the request and check for the If-None-Match Header
    if_none_match_value = request.headers.get("If-None-Match", "")
    if_modified_since_value = request.headers.get("If-Modified-Since")
    if if_modified_since_value is None:
        if_modified_since_value = datetime.datetime.fromtimestamp(0, tz=pytz.UTC)
    else:
        if_modified_since_value = email.utils.parsedate_to_datetime(if_modified_since_value)
    # Get the last update of the schema from which the service gets its data from
    last_database_modification = tools.get_last_schema_update("water_usage", database.engine)
    data_changed = if_modified_since_value < last_database_modification
    if query_hash == if_none_match_value and not data_changed:
        return fastapi.Response(status_code=304, headers={"ETag": f"{query_hash}"})
    else:
        response: fastapi.Response = await call_next(request)
        response.headers.append("ETag", f"{query_hash}")
        response.headers.append("Last-Modified", email.utils.format_datetime(last_database_modification))
        return response


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
    _forecast_id = _amqp_client.send(calculation_request.json(by_alias=True), _amqp_configuration.exchange)
    # Wait a maximum amount of 120 seconds for the response
    logging.info("Awaiting the response for the forecast")
    _forecast = _amqp_client.await_response(_forecast_id, timeout=120.0)
    if _forecast is None:

        logging.warning(
            "Got no response in the last 120.0 seconds. Returning the forecast id to allow pull of result "
            "when the result was received"
        )
        if _redis_configuration.use_redis:
            _redis_client.lpush("water_usage_forecasts_awaiting", _forecast_id)
            _redis_client.set(f"forecast_user_{_forecast_id}", user.json(by_alias=True))
            message = {
                "forecastID": _forecast_id,
                "message": "The forecast calculation module did not return a response "
                "in the last two minutes. Use the forecast id to try and pull the "
                "response later on. If the result pull results in a 404 please ",
            }
            return fastapi.responses.UJSONResponse(
                content=message,
                media_type="text/json",
                status_code=http.HTTPStatus.ACCEPTED,
            )
        else:
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


if _redis_configuration.use_redis:

    @service.get("/result/{forecast_id}")
    async def get_forecast_result(
        forecast_id: str = fastapi.Path(default=...),
        user: models.internal.UserAccount = fastapi.Security(
            security.is_authorized_user, scopes=[_security_configuration.scope_string_value]
        ),
    ):
        # Get all awaited forecasts
        awaited_forecasts = [e.decode("utf-8") for e in _redis_client.lrange("water_usage_forecasts_awaiting", 0, -1)]
        if forecast_id not in awaited_forecasts:
            raise exceptions.APIException(
                error_code="NO_SUCH_FORECAST",
                error_title="Forecast not found",
                error_description="The specified forecast was not found in the list of awaited forecasts",
                http_status=http.HTTPStatus.NOT_FOUND,
            )
        _raw_forecast_user = _redis_client.get(f"forecast_user_{forecast_id}")
        if _raw_forecast_user is not None:
            _forecast_user = models.internal.UserAccount.parse_raw(_raw_forecast_user)
            if _forecast_user.id is not user.id:
                raise exceptions.APIException(
                    error_code="NOT_FORECAST_USER",
                    error_title="Forecast created by different user",
                    error_description="The forecast was created by a different user. Therefore you may not access this "
                    "forecast",
                    http_status=http.HTTPStatus.FORBIDDEN,
                )
        if _redis_client.get(f"forecast_result_{forecast_id}") is None:
            _forecast_result = _amqp_client.get_response(forecast_id)
            if _forecast_result is None:
                message = {
                    "forecastID": forecast_id,
                    "message": "There is no response to the requested forecast at the time",
                }
                return fastapi.responses.UJSONResponse(
                    content=message,
                    media_type="text/json",
                    status_code=http.HTTPStatus.TOO_EARLY,
                )
            else:
                _redis_client.set(f"forecast_result_{forecast_id}", _forecast_result)
        else:
            _forecast_result = _redis_client.get(f"forecast_result_{forecast_id}")
        return fastapi.Response(content=_forecast_result, media_type="text/json")

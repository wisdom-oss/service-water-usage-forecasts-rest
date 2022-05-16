import http
import logging
import typing

import amqp_rpc_client
import fastapi.security
import pydantic
import ujson

import enums
import exceptions
import models.internal
import configuration

# %% OAuth 2.0 Scheme Setup
__wisdom_central_auth = fastapi.security.OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    scheme_name="WISdoM Central Authorization",
    auto_error=False,
)

# %% Required Settings for the common packages
_service_settings = configuration.ServiceConfiguration()
_amqp_settings = configuration.AMQPConfiguration()


# %% Clients needed for the security
__amqp_client = amqp_rpc_client.Client(_amqp_settings.dsn, mute_pika=True, data_processing_wait_time=1)
__logger = logging.getLogger("security")


def is_authorized_user(
    scopes: fastapi.security.SecurityScopes,
    access_token: str = fastapi.Depends(__wisdom_central_auth),
) -> typing.Union[bool, models.internal.UserAccount]:
    """
    Check if the user calling this service is authorized.

    This security dependency needs to be used as fast api dependency in the methods

    :param scopes: The scopes this used needs to have to access this service
    :type scopes: list
    :param access_token: The access token used by the user to access the service
    :type access_token: str
    :return: Status of the authorization
    :rtype: bool
    :raises exceptions.APIException: The user is not authorized to access this service
    """
    # Prepare the request
    introspection_request = {
        "action": enums.AMQPAction.CHECK_TOKEN_SCOPE.value,
        "token": access_token,
        "scopes": scopes.scopes,
    }
    # Send the request and wait a max amount of 10 seconds until the response needs to be returned
    logging.debug("Created token introspection request: %s", introspection_request)
    introspection_id = __amqp_client.send(ujson.dumps(introspection_request), _amqp_settings.authorization_exchange)
    logging.debug("Sent token introspection request. Got new ID: %s", introspection_id)
    logging.debug("Waiting for introspection response")
    introspection_response_bytes = __amqp_client.await_response(introspection_id, 10)
    logging.debug("Got response for token introspection: %s", introspection_response_bytes)
    if introspection_response_bytes is None:
        raise exceptions.APIException(
            error_code="TOKEN_VALIDATION_TIMEOUT",
            error_title="Token Validation Timeout",
            error_description="The service could not validate the used access token in a timely manner",
            http_status=http.HTTPStatus.REQUEST_TIMEOUT,
        )
    # Try to read the response
    try:
        token = models.internal.TokenIntrospection.parse_raw(introspection_response_bytes)
        logging.debug("Successfully parsed the token introspection response into an object: %s", token)
    except pydantic.ValidationError as e:
        raise exceptions.APIException(
            error_code="INTROSPECTION_FAILURE",
            error_title="Token introspection failure",
            error_description=f"The token introspection failed due to an unrecognized response: {str(e)}",
        )
    if not token.active:
        if token.reason == enums.TokenIntrospectionFailure.INVALID_TOKEN:
            raise exceptions.APIException(
                error_code="INVALID_TOKEN",
                error_title="Invalid Bearer Token",
                error_description="The request did not contain the correct credentials to allow processing this "
                "request",
                http_status=http.HTTPStatus.UNAUTHORIZED,
            )
        elif token.reason == enums.TokenIntrospectionFailure.EXPIRED:
            raise exceptions.APIException(
                error_code="EXPIRED_TOKEN",
                error_title="Expired Bearer Token",
                error_description="The request did not contain a alive Bearer token",
                http_status=http.HTTPStatus.UNAUTHORIZED,
            )
        elif token.reason == enums.TokenIntrospectionFailure.TOKEN_USED_TOO_EARLY:
            raise exceptions.APIException(
                error_code="TOKEN_BEFORE_CREATION",
                error_title="Credentials used too early",
                error_description="The credentials used for this request are currently not valid",
                http_status=http.HTTPStatus.UNAUTHORIZED,
            )
        elif token.reason == enums.TokenIntrospectionFailure.NO_USER_ASSOCIATED:
            raise exceptions.APIException(
                error_code="USER_DELETED",
                error_title="User deleted",
                error_description="The account used to access this resource was deleted",
                http_status=http.HTTPStatus.UNAUTHORIZED,
            )
        elif token.reason == enums.TokenIntrospectionFailure.USER_DISABLED:
            raise exceptions.APIException(
                error_code="USER_DISABLED",
                error_title="User Disabled",
                error_description="The account used to access this resource is currently disabled",
                http_status=http.HTTPStatus.FORBIDDEN,
            )
        elif token.reason == enums.TokenIntrospectionFailure.MISSING_PRIVILEGES:
            raise exceptions.APIException(
                error_code="MISSING_PRIVILEGES",
                error_title="Missing Privileges",
                error_description="The account used to access this resource does not have the privileges to access "
                "this endpoint",
                http_status=http.HTTPStatus.FORBIDDEN,
            )
        else:
            raise exceptions.APIException(
                error_code="INACTIVE_TOKEN",
                error_title="Inactive Bearer Token",
                error_description="The token was rejected by the authorization system, but no error code was returned",
                http_status=http.HTTPStatus.UNAUTHORIZED,
            )
    if token.user is None:
        return True
    return token.user

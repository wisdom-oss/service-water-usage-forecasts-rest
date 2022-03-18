from pydantic import Field

from .. import BaseModel


class TokenIntrospectionRequest(BaseModel):
    action: str = Field(
        default='validate_token',
        alias='action'
    )
    
    bearer_token: str = Field(
        default=...,
        alias='token'
    )
    """The bearer token which shall be validated"""
    
    scopes: str = Field(
        default='water_usage:forecasts',
        alias='scopes'
    )
    """The scopes the token needs to access this resource"""
    
import typing

import pydantic
from sqlalchemy import sql

import database
import database.tables
import enums
from . import BaseModel as _BaseModel


class TokenIntrospectionRequest(_BaseModel):
    """
    The data model describing how a token introspection request will look like
    """

    action: str = pydantic.Field(default="validate_token", alias="action")
    """The action that shall be executed on the authorization server"""

    bearer_token: str = pydantic.Field(default=..., alias="token")
    """The Bearer token that has been extracted and now shall be validated"""

    scope: str = pydantic.Field(default=..., alias="scope")
    """The scope which needs to be in the tokens scope to pass the introspection"""


class CreateScopeRequest(_BaseModel):
    """
    The data model describing how a scope creation request will look like
    """

    action: str = pydantic.Field(default="add_scope")

    name: str = pydantic.Field(default=..., alias="name")
    """The name of the new scope"""

    description: str = pydantic.Field(default=..., alias="description")
    """The description of the new scope"""

    value: str = pydantic.Field(default=..., alias="value")
    """String which will identify the scope"""

    @pydantic.validator("value")
    def check_scope_value_for_whitespaces(cls, v: str):
        if " " in v:
            raise ValueError("The scope value may not contain any whitespaces")
        return v


class CheckScopeRequest(_BaseModel):
    action: str = pydantic.Field(default="check_scope", alias="action")

    value: str = pydantic.Field(default=..., alias="scope")
    """The value of the scope that shall tested for existence"""


class CalculationRequest(_BaseModel):
    """A model describing, how the incoming request shall look like"""

    model: enums.ForecastModel = pydantic.Field(default=..., alias="model")
    """The forecast model which shall be used to forecast the usage values"""

    keys: list[str] = pydantic.Field(default=..., alias="keys")
    """The municipal and district keys for which objects the forecast shall be executed"""

    consumer_groups: typing.Optional[list[str]] = pydantic.Field(default=None, alias="consumerGroups")
    """The consumer groups for which the forecast shall be calculated"""

    forecast_size: int = pydantic.Field(default=20, alias="forecastSize", gt=0)
    """The amount of years for which the forecast shall be calculated"""

    @pydantic.validator("keys")
    def check_keys(cls, v):
        """
        Check if the keys are of a valid length and are present in the database

        :param v: The values which are already present in the database
        :return: The object containing the keys
        """
        if v is None:
            raise ValueError("At least one key needs to be present in the list of keys")
        # Now check if the keys are present in the database
        shape_query = sql.select(
            [database.tables.shapes.c.key],
            database.tables.shapes.c.key.in_(v),
        )
        db_shapes = database.engine.execute(shape_query).all()
        unrecognized_keys = [k for k in v if (k,) not in db_shapes]
        if len(unrecognized_keys) > 0:
            raise ValueError(f"The following keys have not been recognized by the module: {unrecognized_keys}")
        return v

    @pydantic.validator("consumer_groups", always=True)
    def check_consumer_groups(cls, v):
        if v is None:
            consumer_group_pull_query = sql.select([database.tables.consumer_groups.c.parameter])
            results = database.engine.execute(consumer_group_pull_query).all()
            return [row[0] for row in results]
        else:
            consumer_group_query = sql.select(
                [database.tables.consumer_groups.c.parameter],
                database.tables.consumer_groups.c.parameter.in_(v),
            )
            results = database.engine.execute(consumer_group_query).all()
            found_objects = [row[0] for row in results]
            for obj in v:
                if obj not in found_objects:
                    raise ValueError(f"The consumer group {obj} was not found in the database")
            return v

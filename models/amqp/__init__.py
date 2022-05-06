import typing

import pydantic
from pydantic import Field
from sqlalchemy import sql

import database
import database.tables
import enums
from .. import BaseModel


class TokenIntrospectionRequest(BaseModel):
    action: str = Field(default="validate_token", alias="action")

    bearer_token: str = Field(default=..., alias="token")
    """The bearer token which shall be validated"""

    scopes: str = Field(default="water_usage:forecasts", alias="scope")
    """The scopes the token needs to access this resource"""


class WaterUsages(BaseModel):
    """A model for the current water usages"""

    start: int = pydantic.Field(default=..., alias="startYear")
    """
    Start Year

    The data contained in the ``usages`` list start in this year
    """

    end: int = pydantic.Field(default=..., alias="endYear")
    """
    End Year

    The data contained in the ``usages`` list ends in this year
    """

    usages: list[float] = pydantic.Field(default=..., alias="usageAmounts")
    """
    Water Usage Amounts

    Every entry in this list depicts the water usage of year between the ``start`` and ``end``
    attribute of this object. The list needs to be ordered by the corresponding years
    """

    @pydantic.root_validator
    def check_data_consistency(cls, values):
        """
        Check if the data is consistent between itself. Meaning for every year is a water usage
        amount in the list present and the values for start and end are not switched or equal
        """
        data_start = values.get("start")
        data_end = values.get("end")
        usage_values = values.get("usages")
        if data_start == data_end:
            raise ValueError("Unable to run successful forecast with one set of data")
        # Calculate the number of entries needed for a complete dataset
        needed_values = (data_end + 1) - data_start
        # Now check if the usage list has the same length
        if len(usage_values) != needed_values:
            raise ValueError(
                f"The usage values have {len(usage_values)} entries. Expected "
                f"{needed_values} from start and end parameter"
            )
        return values


class ForecastQuery(BaseModel):
    """A model describing, how the incoming request shall look like"""

    model: enums.ForecastModel = pydantic.Field(default=..., alias="model")
    """The forecast model which shall be used to forecast the usage values"""

    keys: list[str] = pydantic.Field(default=..., alias="keys")
    """The municipal and district keys for which objects the forecast shall be executed"""

    consumer_groups: typing.Optional[list[str]] = pydantic.Field(
        default=None, alias="consumerGroups"
    )
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
        # Split the keys into a district and a municipal list
        municipal_keys = [k for k in v if len(k) == 8]
        district_keys = [k for k in v if len(k) == 5]
        unknown_keys = [k for k in v if len(k) not in [5, 8]]
        # Now check if any unknown keys have been sent
        if len(unknown_keys) > 0:
            raise ValueError(
                f"The following keys have not been recognized by the module: {unknown_keys}"
            )
        # Now check if the keys are present in the database
        municipal_query = sql.select(
            [database.tables.municipals.c.key],
            database.tables.municipals.c.key.in_(municipal_keys),
        )
        db_municipals = database.engine.execute(municipal_query).all()
        unrecognized_keys = [k for k in municipal_keys if (k,) not in db_municipals]
        district_keys_query = sql.select(
            [database.tables.districts.c.key],
            database.tables.districts.c.key.in_(district_keys),
        )
        db_districts = database.engine.execute(district_keys_query).all()
        unrecognized_keys += [k for k in district_keys if (k,) not in db_districts]
        if len(unrecognized_keys) > 0:
            raise ValueError(
                f"The following keys have not been recognized by the module: {unrecognized_keys}"
            )
        return v

    @pydantic.validator("consumer_groups", always=True)
    def check_consumer_groups(cls, v):
        if v is None:
            consumer_group_pull_query = sql.select(
                [database.tables.consumer_groups.c.parameter]
            )
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
                    raise ValueError(
                        f"The consumer group {obj} was not found in the database"
                    )
            return v

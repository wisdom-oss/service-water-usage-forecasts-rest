import typing

import pydantic
from pydantic import Field

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


class ForecastRequest(BaseModel):
    type: enums.ForecastModel = pydantic.Field(
        default=..., alias="forecastType"
    )
    """
    Forecast Type

    The type of forecast which shall be executed
    """

    predicted_years: typing.Optional[int] = pydantic.Field(
        default=15, alias="predictedYears"
    )
    """
    Predicted Years

    The amount of years which shall be predicted with the supplied model
    """

    usage_data: WaterUsages = pydantic.Field(default=..., alias="usageData")
    """
    Actual water usage data

    This object contains the current water usages and the range of years for the current water
    usages
    """

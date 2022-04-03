"""Response models"""
from typing import List

from pydantic import BaseModel, Field

from models.requests import ConsumerGroup, ForecastType


class ReferenceData(BaseModel):
    """Reference time data"""

    time_period_start: int = Field(default=..., alias="start")
    """Start of the time period the reference values are from"""

    time_period_end: int = Field(default=..., alias="end")
    """End of the time period the reference values are from"""
    water_usage_amounts: List[float] = Field(default=..., alias="usageAmounts")
    """Water usage amounts in the given time period"""


class ForecastResponse(BaseModel):
    """Response for a successful forecast"""

    forecast_type: ForecastType = Field(..., alias="forecastType")
    consumer_group: ConsumerGroup = Field(default=..., alias="consumerGroup")
    reference_data: ReferenceData = Field(default=..., alias="reference")

from pydantic import BaseModel, Field

from models.requests import ConsumerGroup, ForecastType


class ForecastResponse(BaseModel):
    forecast_type: ForecastType = Field(
        ...,
        alias='forecastType'
    )
    consumer_group: ConsumerGroup = Field(
        default=...,
        alias='consumerGroup'
    )

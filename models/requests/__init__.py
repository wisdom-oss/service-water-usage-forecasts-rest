from typing import List

from pydantic import BaseModel, Field, root_validator

from models.requests.enums import ConsumerGroup, ForecastType


class RealData(BaseModel):
    """
    Data model for the incoming real water usage data.
    """
    time_period_start: int = Field(
        default=...,
        alias='timePeriodStart'
    )
    time_period_end: int = Field(
        default=...,
        alias='timePeriodEnd'
    )
    water_usage_amounts: List[float] = Field(
        default=...,
        alias='waterUsageAmounts'
    )

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True

    @root_validator
    def check_data_consistency(cls, values):
        time_period_start = values.get("time_period_start")
        time_period_end = values.get("time_period_end")
        water_usage_amounts = values.get("water_usage_amounts")
        if time_period_start >= time_period_end:
            raise ValueError(
                'The start of the time period may not be after the end of the time '
                'period'
            )
        expected_values_in_list = (time_period_end + 1) - time_period_start
        value_discrepancy = expected_values_in_list - len(water_usage_amounts)
        if value_discrepancy > 0:
            raise ValueError(f'The Water usage amounts list is missing {value_discrepancy} entries')
        if value_discrepancy < 0:
            raise ValueError(
                f'The Water usage amounts list has {abs(value_discrepancy)} entries '
                f'too much'
            )
        return values


class ForecastRequest(RealData):
    forecast_type: ForecastType = Field(
        default=...,
        alias='forecastType'
    )
    consumer_group: List[ConsumerGroup] = Field(
        default=...,
        alias='consumerGroup'
    )

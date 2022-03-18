"""Models for the incoming requests"""
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
        """Configuration for the RealData model"""
        allow_population_by_field_name = True
        allow_population_by_alias = True

    @root_validator
    def check_data_consistency(cls, values):
        """Pydantic validator which will check for the consistency between the given time period
        and the supplied usage amounts

        :param values:
        :return:
        """
        time_period_start = values.get("time_period_start")
        time_period_end = values.get("time_period_end")
        water_usage_amounts = values.get("water_usage_amounts")
        print(time_period_start, time_period_end, water_usage_amounts, len(water_usage_amounts))
        if time_period_start >= time_period_end:
            raise ValueError(
                'The start of the time period may not be after the end of the time '
                'period'
            )
        expected_values_in_list = time_period_end - (time_period_start + 1)
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
    """
    Model for describing the incoming forecast request, which will be used to build the amqp message
    """
    forecast_type: ForecastType = Field(
        default=...,
        alias='forecastType'
    )
    consumer_group: ConsumerGroup = Field(
        default=...,
        alias='consumerGroup'
    )

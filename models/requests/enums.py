"""Enumerations for the requests to limit the available endpoints"""
from enum import Enum


class SpatialUnit(str, Enum):
    """Spatial Units supported by this Endpoint"""
    COMMUNE = "commune"
    COUNTY = "county"


class ForecastType(str, Enum):
    """Forecast types"""
    LOGARITHMIC = "logarithmic"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"


class ConsumerGroup(str, Enum):
    """Consumer Groups"""
    BUSINESSES = "businesses"
    HOUSEHOLDS_AND_SMALL_BUSINESSES = "households_and_small_businesses"
    FARMING_FORESTRY_FISHING_INDUSTRY = "farming_forestry_fishing_industry"
    PUBLIC_INSTITUTIONS = "public_institutions"
    ALL = "all"
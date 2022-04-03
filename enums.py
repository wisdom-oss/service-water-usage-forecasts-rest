import enum


class SpatialUnit(str, enum.Enum):
    """Spatial Units supported by this Endpoint"""

    MUNICIPALITIES = "municipalities"
    DISTRICTS = "districts"


class ForecastModel(str, enum.Enum):
    """Forecast types"""

    LOGARITHMIC = "logarithmic"
    LINEAR = "linear"
    POLYNOMIAL = "polynomial"


class ImportDataTypes(str, enum.Enum):
    """
    A class for fixating the possible data imports
    """

    COMMUNES = "communes"
    COUNTIES = ("counties",)
    CONSUMER_TYPES = "consumerTypes"
    USAGES = "usages"

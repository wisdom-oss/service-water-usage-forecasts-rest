"""Module for custom Exceptions for generating error messages"""


class APIException(Exception):
    """Base class for all custom exceptions for using the Http API"""

    pass


class DuplicateEntryError(Exception):
    """
    A INSERT operation failed since a constraint (e.g. unique or primary key) was violated
    """

    pass


class QueryDataError(APIException):
    """An Exception raised for errors in the Query Data"""

    def __init__(self, short_error: str, error_description: str):
        """New Query Data Exception

        :param short_error: Short error code
        :param error_description: Description for the reason behind raising the exception
        """
        self.short_error = short_error
        self.error_description = error_description


class InsufficientDataError(APIException):

    def __init__(self, consumer_group_id: int, municipality_id: int):
        """
        New Insufficient data error

        :param consumer_group_id: The consumer group id for which is no sufficient data present
        :type consumer_group_id: int
        :param municipality_id: The municipality in which the data is missing
        :type municipality_id: int
        """
        self.consumer_group_id = consumer_group_id
        self.municipality_id = municipality_id

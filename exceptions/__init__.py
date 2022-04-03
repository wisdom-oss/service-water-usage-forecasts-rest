"""Module for custom Exceptions for generating error messages"""
from sqlalchemy.exc import IntegrityError


class APIException(Exception):
    """Base class for all custom exceptions for using the Http API"""

    pass


class DuplicateEntryError(IntegrityError):
    """
    A INSERT operation failed since a constraint (e.g. unique or primary key) was violated
    """

    def __init__(self):
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

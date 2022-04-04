"""Import module for importing csv files into the system"""
import datetime
import os
import typing
import pathlib

import pandas
import sqlalchemy.exc
import sqlalchemy.orm

import exceptions
import database
import database.tables
import database.crud


def import_municipals(
    file_path: typing.Union[str, bytes, os.PathLike], session: sqlalchemy.orm.Session
) -> typing.List[database.tables.Municipal]:
    """
    Read the given csv file and write the found municipals into the database

    :param file_path: The path pointing to the CSV file
    :type file_path: str, bytes, os.PathLike
    :param session: The database session used to insert the data
    :type session: sqlalchemy.orm.Session
    :return: The list of the inserted object
    :rtype: list[database.tables.Municipal]
    """
    # Check if the file_path parameter is a string or bytes, if yes convert it into a Path object
    file_path = (
        pathlib.Path(file_path) if type(file_path) in [str, bytes] else file_path
    )
    # Now check if the file exists
    if not file_path.is_file():
        raise FileNotFoundError("The specified path does not point to a file")
    # Now read the contents of the csv with pandas
    municipal_series = pandas.read_csv(
        file_path,
        header=0,
        names=["Municipal"],
        usecols=["Municipal"],
        dtype=str,
        squeeze=True,
    )
    municipals = []
    for municipal in municipal_series:
        # Create a new municipal
        _municipal = database.tables.Municipal(name=municipal)
        try:
            _municipal = database.crud.insert_object(_municipal, session)
            municipals.append(_municipal)
        except sqlalchemy.exc.IntegrityError:
            raise exceptions.DuplicateEntryError(
                f'The municipal "{municipal}" is already stored ' f"in the database"
            )
    return municipals


def import_usages(
    file_path: typing.Union[str, bytes, os.PathLike], session: sqlalchemy.orm.Session
) -> typing.List[database.tables.Usage]:
    """
    Read the given csv file and write the found usages into the database

    :param file_path: The path pointing to the CSV file
    :type file_path: str, bytes, os.PathLike
    :param session: The database session used to insert the data
    :type session: sqlalchemy.orm.Session
    :return: The list of the inserted object
    :rtype: list[database.tables.Municipal]
    """
    # Check if the file_path parameter is a string or bytes, if yes convert it into a Path object
    file_path = (
        pathlib.Path(file_path) if type(file_path) in [str, bytes] else file_path
    )
    # Now check if the file exists
    if not file_path.is_file():
        raise FileNotFoundError("The specified path does not point to a file")
    # Now read the contents of the csv with pandas
    usage_frame = pandas.read_csv(
        file_path,
        header=0,
        names=["Municipal", "Consumer Group", "Usage Value", "Year"],
        usecols=["Municipal", "Consumer Group", "Usage Value", "Year"],
        dtype=object,
        squeeze=True,
    )
    # Fill missing years with the current one
    usage_frame.where(
        pandas.notnull(usage_frame), datetime.date.today().year, inplace=True
    )
    # Now insert the data
    usages = []
    for usage in usage_frame.iterrows():
        _usage = database.tables.Usage(
            municipal_id=usage["Municipal"],
            consumer_group=usage["Consumer Group"],
            value=usage["Usage"],
            year=["Year"],
        )
        _usage = database.crud.insert_object(_usage, session)
        usages.append(_usage)
    return usages

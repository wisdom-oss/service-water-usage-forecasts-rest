"""Import module for importing csv files into the system"""
import datetime
import os
from typing import List, Optional, Union
from pathlib import Path

import pandas
from sqlalchemy.exc import IntegrityError

from exceptions import DuplicateEntryError
from ... import get_database_session
from ...tables import County, Commune, ConsumerType, WaterUsageAmount
from ...tables.operations import get_commune_id, get_consumer_type_id, get_county_id, \
    get_county_names, insert_object


def import_counties_from_file(file_path: Union[str, bytes, os.PathLike]):
    """Import a set of counties into the database

    :param file_path: Path to the CSV file containing the new counties
    :return: After the successful import it will return all inserted orm items
    :raises FileNotFoundError: The path supplied does not point to a file
    :raises DuplicateEntryError: The file contains an entry which is already in the database
    """
    # Convert a possible string or byte array into a path
    file_path: Path = Path(file_path) if type(file_path) in [str, bytes] else file_path
    # Validate that the file path is indeed a file
    if not file_path.is_file():
        # Raise a new exception
        raise FileNotFoundError("The given path is not a path to a file")
    # Read the file into a pandas dataframe
    counties_series: pandas.Series = pandas.read_csv(
        file_path,
        header=0,
        names=["County"],
        usecols=["County"],
        dtype=str,
        squeeze=True
    )
    # Iterate though the series of counties and save the counties into a list
    counties: List[County] = []
    db_session = next(get_database_session())
    for county in counties_series:
        # Create a new orm mapping
        __county = County(name=county)
        try:
            __county = insert_object(__county, db_session)
        except IntegrityError:
            raise DuplicateEntryError
        counties.append(
           __county
        )
    return counties


def import_communes_from_file(file_path: Union[str, bytes, os.PathLike]) -> List[Commune]:
    """Import communes into the database

    This import will also create the foreign key relations for communes in counties

    :param file_path: Path to the file containing the commune data
    :return: List of created communes
    :raises FileNotFoundError: The path supplied does not point to a file
    :raises DuplicateEntryError: The file contains an entry which is already in the database
    """
    # Convert file_path into a Path if it is a string
    file_path: Path = Path(file_path) if type(file_path) in [str, bytes] else file_path
    # Check if this is an actual file
    if not file_path.is_file():
        raise FileNotFoundError("The given path is not a path to a file")
    # Read the csv into pandas
    commune_data_frame: pandas.DataFrame = pandas.read_csv(
        file_path,
        header=0,
        names=["Commune", "County"],
        usecols=["Commune", "County"],
        dtype=object,
        squeeze=False
    )
    # Replace missing values with none
    commune_data_frame = commune_data_frame.where(pandas.notnull(commune_data_frame), None)
    # Iterate though the rows
    db_session = next(get_database_session())
    communes: List[Commune] = []
    for row in commune_data_frame.itertuples():
        _commune_name = row[1]
        _county_name = row[2]

        if _county_name is not None:
            _commune = Commune(
                name=_commune_name,
                in_county=get_county_id(_county_name, db_session)
            )
        else:
            _commune = Commune(
                name=_commune_name,
                in_county=None
            )
        try:
            _commune = insert_object(_commune, db_session)
        except IntegrityError:
            raise DuplicateEntryError()
        communes.append(_commune)
    return communes


def import_consumer_types_from_file(
        file_path: Union[str, bytes, os.PathLike]
) -> List[ConsumerType]:
    """

    :param file_path: Path to the file containing the consumer types
    :return: List of inserted consumer types
    :raises FileNotFoundError: The path supplied does not point to a file
    :raises DuplicateEntryError: The file contains an entry which is already in the database
    """
    # Convert file_path into a Path if it is a string
    file_path: Path = Path(file_path) if type(file_path) in [str, bytes] else file_path
    # Check if this is an actual file
    if not file_path.is_file():
        raise FileNotFoundError("The given path is not a path to a file")
    # Read csv file into the pandas frame
    consumer_type_data_frame: pandas.DataFrame = pandas.read_csv(
        file_path,
        header=0,
        names=["Name", "Description"],
        usecols=["Name", "Description"],
        dtype=object,
        squeeze=False
    )
    # Replace the missing values with an empty string
    consumer_type_data_frame.where(
        pandas.notnull(consumer_type_data_frame), '',
        inplace=True
    )
    # Get a new database session
    db_session = next(get_database_session())
    # Create a list for the inserted consumer types and iterate through the data frame's rows
    consumer_types: List[ConsumerType] = []
    for row in consumer_type_data_frame.itertuples():
        _consumer_type_name = row[1]
        _consumer_type_description = row[2]

        _consumer_type = ConsumerType(
            name=_consumer_type_name,
            description=_consumer_type_description
        )
        try:
            _consumer_type = insert_object(_consumer_type, db_session)
        except IntegrityError:
            raise DuplicateEntryError()
        consumer_types.append(_consumer_type)
    return consumer_types


def import_water_usages_from_file(
        file_path: Union[str, bytes, os.PathLike]
) -> List[WaterUsageAmount]:
    """Import new water usages from a csv file

    :param file_path: Path to the file containing the water usages
    :return: List of inserted water usage values
    :raises FileNotFoundError: The path supplied does not point to a file
    :raises InconsistentDataError: The import process found a not recoverable data error (often
    missing usage amount)
    """
    # Convert file_path into a Path if it is a string
    file_path: Path = Path(file_path) if type(file_path) in [str, bytes] else file_path
    # Check if this is an actual file
    if not file_path.is_file():
        raise FileNotFoundError("The given path is not a path to a file")
    # Read csv file into the pandas frame
    usage_value_data_frame: pandas.DataFrame = pandas.read_csv(
        file_path,
        header=0,
        names=["Commune", "ConsumerType", "Value", "Year"],
        usecols=["Commune", "ConsumerType", "Value", "Year"],
        dtype=object,
        squeeze=False
    )
    # Replace missing years with the current one
    current_year = datetime.date.today().year
    usage_value_data_frame.where(
        pandas.notnull(usage_value_data_frame),
        None,
        inplace=True
    )
    # Get a database session
    db_session = next(get_database_session())
    usage_values: List[WaterUsageAmount] = []
    for row in usage_value_data_frame.itertuples():
        _usage_location = row[1]
        _usage_type = row[2]
        _usage_amount = row[3]
        _usage_year = row[4]

        if _usage_year is None:
            _usage_year = current_year

        _water_usage_amount = WaterUsageAmount(
            commune=get_commune_id(_usage_location, db_session),
            consumer_type=get_consumer_type_id(_usage_type, db_session),
            value=_usage_amount,
            year=_usage_year
        )
        _water_usage_amount = insert_object(_water_usage_amount, db_session)
        usage_values.append(_water_usage_amount)
    return usage_values



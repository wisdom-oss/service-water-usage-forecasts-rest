"""Module for outsourced functions for better maintainability"""
import logging

import pandas
from sqlalchemy.orm import Session
import sqlalchemy.sql.functions as sql_func

import database.tables.operations
import models.amqp
from database.tables import Commune, County, WaterUsageAmount
from models.requests.enums import ConsumerGroup, SpatialUnit

__logger = logging.getLogger('API-FUNCS')


def district_in_spatial_unit(district: str, spatial_unit: SpatialUnit, db: Session) -> bool:
    """Check if a queried district is in the spatial unit

    This method will check by looking in the table of the spatial unit. If a unit is found in the
    database table then this method will return true

    :param district: District queried in the request
    :type district: str
    :param spatial_unit: Spatial unit set in the request
    :type spatial_unit: SpatialUnit
    :param db: Database Session
    :type db: Session
    :return: True if a unit is found in its spatial unit, False if not
    :rtype: bool
    """
    __logger.debug(
        'Checking if "%s" is listed as district in the spatial unit "%s"',
        district, spatial_unit.value
    )
    query_results = None
    if spatial_unit == SpatialUnit.COMMUNE:
        query_results = db.query(Commune).filter(Commune.name == district).all()
    elif spatial_unit == SpatialUnit.COUNTY:
        query_results = db.query(County).filter(County.name == district).all()
    if query_results is None:
        return False
    elif len(query_results) == 0:
        return False
    else:
        return True


def get_water_usage_data(
        district: str,
        spatial_unit: SpatialUnit,
        db: Session,
        consumer_group: str = ConsumerGroup.ALL.value
):
    """Get the water usage amounts per year

    :param consumer_group:
    :param db:
    :param district:
    :param spatial_unit:
    :return:
    """
    # Check the spatial unit
    if spatial_unit == SpatialUnit.COMMUNE:
        # Get the ID of the consumer group
        _consumer_group_id = database.tables.operations.get_consumer_group_id(consumer_group, db)
        # Get the ID of the district
        _district_id = database.tables.operations.get_commune_id(district, db)
        # Get the water usage list
        _water_usages_per_year = (
            db
            .query(WaterUsageAmount.year, sql_func.sum(WaterUsageAmount.value))
            .filter(WaterUsageAmount.commune == _district_id)
            .filter(WaterUsageAmount.consumer_type == _consumer_group_id)
            .group_by(WaterUsageAmount.year)
            .all()
        )
        # Now get extract the raw usages
        _water_usage_amounts = []
        for dataset in _water_usages_per_year:
            # Since the dataset consists of tuples, access the sum only
            _water_usage_amounts.append(dataset[1])
        # Now return the usages
        return models.amqp.WaterUsages(
            # The year is the first entry of the tuples
            start=_water_usages_per_year[0][0],
            # Access the last usage and access the year
            end=_water_usages_per_year[-1][0],
            usages=_water_usage_amounts
        )
    elif spatial_unit == SpatialUnit.COUNTY:
        # Get the ID of the consumer group
        _consumer_group_id = database.tables.operations.get_consumer_group_id(consumer_group, db)
        # TODO: Query the data about which commune is within a county from the geo data service
        # Get the district id of all districts within the county
        _district_ids = database.tables.operations.get_communes_in_county(district, db)
        # Create an empty data set for all districts
        _district_usages: dict[int, pandas.Series] = {}
        # Get the water usages per district
        for _district_id in _district_ids:
            # Get the water usages
            _water_usages_per_year = (
                db
                .query(WaterUsageAmount.year, sql_func.sum(WaterUsageAmount.value))
                .filter(WaterUsageAmount.commune == _district_id)
                .filter(WaterUsageAmount.consumer_type == _consumer_group_id)
                .group_by(WaterUsageAmount.year)
                .all()
            )
            # Create a list for the years
            _usage_years = []
            # Create a list for the usage values
            _usage_values = []
            # Now populate the lists
            for _water_usage_per_year in _water_usages_per_year:
                _usage_years.append(_water_usage_per_year[0])
                _usage_values.append(_water_usage_per_year[1])
            # Now create a pandas Series and add it to the district usages
            _district_usages.update(
                {_district_id: pandas.Series(_usage_values, _usage_years)}
            )
        # After getting all data build a data frame from the district usages
        district_usage_data = pandas.DataFrame(_district_usages)
        # Now fill all None values with a zero and build the sum the columns
        county_usage_data: pandas.Series = district_usage_data.fillna(0).sum(axis='columns')
        # Now build the Water usage data
        return models.amqp.WaterUsages(
            # The first entry of the series keys is the start of the data set
            start=county_usage_data.keys()[0],
            # The last entry of the series keys is the end of the data set
            end=county_usage_data.keys()[-1],
            usages=county_usage_data.tolist()
        )

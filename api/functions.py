"""Module for outsourced functions for better maintainability"""
import logging

import pandas
from sqlalchemy.orm import Session
from sqlalchemy.sql import functions as func

import database
import models.amqp
from database.tables import Commune, County, WaterUsageAmount, operations
from models.requests import RealData
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
        consumer_group: ConsumerGroup = ConsumerGroup.ALL
):
    """Get the water usage amounts per year

    :param consumer_group:
    :param db:
    :param district:
    :param spatial_unit:
    :return:
    """
    # Check if the consumer Group is not "all"
    if consumer_group is ConsumerGroup.ALL:
        __consumer_group_filter_value = '%'
    else:
        __consumer_group_filter_value = database.tables.operations.get_consumer_group_id(
            consumer_group, db
        )
    # Determine the spatial unit for the water usage amounts
    if spatial_unit is SpatialUnit.COMMUNE:
        # Get the foreign key value for the commune
        __commune_filter_value = database.tables.operations.get_commune_id(district, db)
        # Get the years and usage amounts
        __usage_amounts_with_years = db \
            .query(WaterUsageAmount.year, func.sum(WaterUsageAmount.value)) \
            .group_by(WaterUsageAmount.year) \
            .filter(
                WaterUsageAmount.commune == __commune_filter_value,
                WaterUsageAmount.consumer_type.like(__consumer_group_filter_value)
            ).all()
        # Iterate through the paired valued to receive the usage amounts
        __usage_amounts = []
        for __usage_amount in __usage_amounts_with_years:
            __usage_amounts.append(__usage_amount[1])
        # Build the return value
        return models.amqp.WaterUsages(
            start=__usage_amounts_with_years[0][0],
            end=__usage_amounts_with_years[-1][0],
            usages=__usage_amounts
        )
    elif spatial_unit == SpatialUnit.COUNTY:
        _communes = database.tables.operations.get_communes_in_county(district, db)
        print(_communes)
        _data = {}
        for commune_id in _communes:
            _usages_with_years = db\
                .query(WaterUsageAmount.year, func.sum(WaterUsageAmount.value))\
                .group_by(WaterUsageAmount.year)\
                .filter(
                        WaterUsageAmount.commune == commune_id,
                        WaterUsageAmount.consumer_type.like(__consumer_group_filter_value)
                ).all()
            _years = []
            _usage_amounts = []
            for usage_with_year in _usages_with_years:
                _years.append(usage_with_year[0])
                _usage_amounts.append(usage_with_year[1])
            _data.update({commune_id: pandas.Series(_usage_amounts, _years)})
        data_frame = pandas.DataFrame(_data)
        usage_data: pandas.Series = data_frame.fillna(0).sum(axis='columns')
        return models.amqp.WaterUsages(
            start=usage_data.keys()[0],
            end=usage_data.keys()[-1],
            usages=usage_data.tolist()
        )

"""Module for outsourced functions for better maintainability"""
import logging
from typing import List

from sqlalchemy import func as f
from sqlalchemy.orm import Session

from database.tables import WaterUsageAmount, Commune, County
from models.requests import RealData
from models.requests.enums import SpatialUnit

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


def get_water_usage_data(district: str, spatial_unit: SpatialUnit, db: Session) -> RealData:
    """Get the water usage amounts per year

    :param district:
    :param spatial_unit:
    :return:
    """
    if spatial_unit == SpatialUnit.COMMUNE:
        commune = db.query(Commune).filter(Commune.name == district).first()
        # Query the database for all usage amounts of this commune
        usage_amounts = db.query(WaterUsageAmount.year, f.sum(WaterUsageAmount.value))\
            .group_by(WaterUsageAmount.year)\
            .filter(WaterUsageAmount.commune == commune.id).all()
        __water_usage_list = []
        for usage_amount in usage_amounts:
            __water_usage_list.append(usage_amount[1])
        return RealData(
            time_period_start=usage_amounts[0][0],
            time_period_end=usage_amounts[-1][0],
            water_usage_amounts=__water_usage_list
        )

    elif spatial_unit == SpatialUnit.COUNTY:
        res = db.query(County).filter(County.name == district).first()


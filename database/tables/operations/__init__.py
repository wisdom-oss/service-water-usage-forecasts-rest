"""Collection of generic operations run on the database"""
from typing import List, Optional

from sqlalchemy.orm import Session

from models.requests import ConsumerGroup
from .. import Commune, ConsumerType, County


def get_consumer_group_id(consumer_group: ConsumerGroup, db: Session) -> Optional[int]:
    """Get the ID of a consumer group

    :param consumer_group: Consumer Group Enumeration value for which the id should be looked up
    :param db: Database Session
    :return: The integer id of the consumer group. None if the consumer group does not exist in
    the database
    """
    try:
        return db.query(ConsumerType).filter(ConsumerType.type == consumer_group.value).first().id
    except AttributeError:
        return None


def get_commune_id(district, db):
    """Get the id (primary key) of the commune with the name supplied.

    :param district: Name of the commune
    :param db: Database connection
    :return: The commune id if the commune exists. Else None
    """
    try:
        return db.query(Commune).filter(Commune.name == district).first().id
    except AttributeError:
        return None


def get_communes_in_county(county: str, db) -> List[int]:
    """Get the ids of the communes in a county

    :param county: Name of the county
    :param db: Database connection
    :return:
    """
    # Get the id of the county
    try:
        county_id = db.query(County).filter(County.name == county).first().id
    except AttributeError:
        return []
    _commune_objs = db.query(Commune).filter(Commune.in_county == county_id).all()
    _commune_ids = []
    for commune in _commune_objs:
        _commune_ids.append(commune.id)
    return _commune_ids


def get_commune_names(db: Session) -> List[str]:
    """Get all names of the communes in the database

    :param db: Database connection
    :return:
    """
    _communes: List[Commune] = db.query(Commune).all()
    names = []
    for _commune in _communes:
        names.append(_commune.name)
    return names


def get_county_names(db: Session) -> List[str]:
    """Get the names of all available counties

    :param db: Database connection
    :return:
    """
    _counties: List[County] = db.query(County).all()
    names = []
    for _county in _counties:
        names.append(_county.name)
    return names

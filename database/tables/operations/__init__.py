from typing import List, Optional

from sqlalchemy.orm import Session

import database
from models.requests import ConsumerGroup
from .. import ConsumerType, Commune, County


def get_consumer_group_id(consumer_group: ConsumerGroup, db: Session) -> Optional[int]:
    try:
        return db.query(ConsumerType).filter(ConsumerType.type == consumer_group.value).first().id
    except AttributeError:
        return None


def get_commune_id(district, db):
    """Get the id (primary key) of the commune with the name supplied.

    :param district:
    :param db:
    :return: The commune id if the commune exists. Else None
    """
    try:
        return db.query(Commune).filter(Commune.name == district).first().id
    except AttributeError:
        return None


def get_communes_in_county(county: str, db) -> List[int]:
    """Get the ids of the communes in a county

    :param county:
    :param db:
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

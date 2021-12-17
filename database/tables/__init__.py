"""Module for describing the Tables used in the database accesses"""
from sqlalchemy import Column, ForeignKey, Integer, String, Float

from .. import TableBase


class County(TableBase):
    """Class describing the table used to store the available counties"""
    __tablename__ = "counties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)


class Commune(TableBase):
    """Class describing the table used to store the available municipals"""
    __tablename__ = "communes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    in_county = Column(Integer, ForeignKey("county.id"))


class WaterUsageAmount(TableBase):
    """Class describing the layout of the database table storing the water usage amounts"""
    __tablename__ = "usage_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commune = Column(Integer, ForeignKey("commune.id"))
    consumer_type = Column(String)
    value = Column(Float)
    year = Column(Integer)

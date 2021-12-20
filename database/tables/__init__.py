"""Module for describing the Tables used in the database accesses"""
from sqlalchemy import Column, ForeignKey, Integer, String, Float

from .. import TableBase


class County(TableBase):
    """Class describing the table used to store the available counties"""
    __tablename__ = "counties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True)


class Commune(TableBase):
    """Class describing the table used to store the available municipals"""
    __tablename__ = "communes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True)
    in_county = Column(Integer, ForeignKey("counties.id"))


class ConsumerType(TableBase):
    __tablename__ = "consumer_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), unique=True)
    type = Column(String(255), unique=True)


class WaterUsageAmount(TableBase):
    """Class describing the layout of the database table storing the water usage amounts"""
    __tablename__ = "usage_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commune = Column(Integer, ForeignKey("communes.id"))
    consumer_type = Column(Integer)
    value = Column(Float)
    year = Column(Integer)

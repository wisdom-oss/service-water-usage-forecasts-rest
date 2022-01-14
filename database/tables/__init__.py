"""Module for describing the Tables used in the database accesses"""
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text

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
    in_county = Column(
        Integer, ForeignKey("counties.id", onupdate='CASCADE', ondelete='CASCADE'), nullable=True
    )


class ConsumerType(TableBase):
    """ORM for the consumer types"""
    __tablename__ = "consumer_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True)
    description = Column(Text)


class WaterUsageAmount(TableBase):
    """Class describing the layout of the database table storing the water usage amounts"""
    __tablename__ = "usage_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commune = Column(Integer, ForeignKey("communes.id", onupdate='CASCADE', ondelete='CASCADE'))
    consumer_type = Column(
        Integer,
        ForeignKey("consumer_types.id", onupdate='CASCADE', ondelete='CASCADE')
    )
    value = Column(Float)
    year = Column(Integer)

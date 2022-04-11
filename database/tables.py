"""Object-Relational-Mapping classes for the used database tables"""
import sqlalchemy.orm
import geoalchemy2
from . import engine

metadata = sqlalchemy.MetaData(schema="water_usage")
geo_metadata = sqlalchemy.MetaData(schema="geodata")
ORMDeclarationBase = sqlalchemy.orm.declarative_base(name="ORMDeclarationBase", metadata=metadata)
GeodataDeclarationBase = sqlalchemy.orm.declarative_base(name='GeoDataORMDeclarationBase', metadata=geo_metadata)


def initialize_mappings():
    """
    Initialize the object-relational mapping classes for this service
    """
    ORMDeclarationBase.metadata.create_all(bind=engine())
    GeodataDeclarationBase.metadata.create_all(bind=engine())


class ConsumerGroup(ORMDeclarationBase):
    __tablename__ = "consumer_groups"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    """The *internal* ID of the consumer group"""

    name: str = sqlalchemy.Column(sqlalchemy.String(length=255), unique=True)
    """The name of the consumer group"""

    description: str = sqlalchemy.Column(sqlalchemy.Text)
    """The description of the consumer group"""

    parameter: str = sqlalchemy.Column(sqlalchemy.Text, unique=True)
    """The query parameter value by which this consumer group is identified"""


class Usage(ORMDeclarationBase):
    """
    A documentation of an occurred water usage
    """

    __tablename__ = "usages"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    """The *internal* ID of the usage"""

    municipal_id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        name="municipal",
        nullable=True,
    )
    """The *internal* ID of the municipal in which the usage has been recorded"""

    consumer_id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        name="consumer",
        nullable=True,
    )
    """The *internal* ID of the consumer for which the usage has been recorded"""

    consumer_group_id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("consumer_groups.id"),
        name="consumer_group",
        nullable=True,
    )
    """The *internal* ID of the consumer group which has been associated with the usage record"""

    value: float = sqlalchemy.Column(sqlalchemy.Float)
    """The used amount of water in cubic meters (m³)"""

    year: int = sqlalchemy.Column(sqlalchemy.Integer)
    """The year in which the usage has been recorded"""


class Municipal(GeodataDeclarationBase):
    """

    """
    __tablename__ = "nds_municipalities"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        autoincrement=True
    )

    name: str = sqlalchemy.Column(
        sqlalchemy.String(length=254)
    )


class GeoMunicipal(GeodataDeclarationBase):
    """A Municipal from the geodata storage of this project"""

    __tablename__ = "nds_municipalities"

    __table_args__ = {
        'extend_existing': True
    }

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        autoincrement=True
    )

    name: str = sqlalchemy.Column(
        sqlalchemy.String(length=254)
    )

    geom = sqlalchemy.Column(
        geoalchemy2.Geometry('MULTIPOLYGON')
    )


class District(GeodataDeclarationBase):
    """A district from the geodata storage of the project"""

    __tablename__ = "nds_districts"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        autoincrement=True
    )

    name: str = sqlalchemy.Column(
        sqlalchemy.String(length=254)
    )

    geom = sqlalchemy.Column(
        geoalchemy2.Geometry('MULTIPOLYGON')
    )

    municipals = sqlalchemy.orm.relationship(
        "GeoMunicipal",
        primaryjoin="func.ST_Contains(foreign(District.geom), GeoMunicipal.geom).as_comparison(1,2)",
        viewonly=True,
        uselist=True
    )

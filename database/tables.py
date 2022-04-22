import geoalchemy2
import sqlalchemy

import database

water_usage_meta_data = sqlalchemy.MetaData(schema="water_usage")
geodata_meta_data = sqlalchemy.MetaData(schema="geodata")

usages = sqlalchemy.Table(
    "usages",
    water_usage_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("municipal", None, sqlalchemy.ForeignKey("geodata.nds_municipalities.id")),
    sqlalchemy.Column("consumer", None, sqlalchemy.ForeignKey("consumers.id")),
    sqlalchemy.Column("consumer_group", None, sqlalchemy.ForeignKey("consumer_group.id")),
    sqlalchemy.Column("year", sqlalchemy.Integer),
    sqlalchemy.Column("value", sqlalchemy.Numeric),
)

consumer_groups = sqlalchemy.Table(
    "consumer_groups",
    water_usage_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("name", sqlalchemy.Text),
    sqlalchemy.Column("description", sqlalchemy.Text),
    sqlalchemy.Column("parameter", sqlalchemy.Text),
)

municipals = sqlalchemy.Table(
    "nds_municipalities",
    geodata_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("geom", geoalchemy2.Geometry("MULTIPOLYGON")),
    sqlalchemy.Column("name", sqlalchemy.Text),
)

districts = sqlalchemy.Table(
    "nds_districts",
    geodata_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("geom", geoalchemy2.Geometry("MULTIPOLYGON")),
    sqlalchemy.Column("name", sqlalchemy.Text),
)


def initialize_tables():
    """
    Initialize the used tables
    """
    water_usage_meta_data.create_all(bind=database.engine)
    geodata_meta_data.create_all(bind=database.engine)

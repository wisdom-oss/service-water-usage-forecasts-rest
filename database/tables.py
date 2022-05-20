import sqlalchemy
import sqlalchemy.dialects

import database

water_usage_meta_data = sqlalchemy.MetaData(schema="water_usage")
geodata_meta_data = sqlalchemy.MetaData(schema="geodata")

usages = sqlalchemy.Table(
    "usages",
    water_usage_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("shape", sqlalchemy.Integer, sqlalchemy.ForeignKey("geodata.shape.id")),
    sqlalchemy.Column("consumer", sqlalchemy.dialects.postgresql.UUID, sqlalchemy.ForeignKey("consumers.id")),
    sqlalchemy.Column("consumer_group", sqlalchemy.Integer, sqlalchemy.ForeignKey("consumer_group.id")),
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

shapes = sqlalchemy.Table(
    "shapes",
    geodata_meta_data,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
    sqlalchemy.Column("name", sqlalchemy.Text),
    sqlalchemy.Column("key", sqlalchemy.Text),
    sqlalchemy.Column("nuts_key", sqlalchemy.Text),
)


def initialize_tables():
    """
    Initialize the used tables
    """
    water_usage_meta_data.create_all(bind=database.engine)
    geodata_meta_data.create_all(bind=database.engine)

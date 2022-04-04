import datetime
import logging

import amqp_rpc_client
import sqlalchemy.sql.functions

import database.crud
import database.tables
import models.amqp


def get_municipals_in_district(district: str, client: amqp_rpc_client.Client):
    # TODO: Implement call to Geo Data Service to get the requested data
    pass


def get_water_usage_data(municipal_id, consumer_group_id, session):
    """Get the water usages per year for the supplied municipal and consumer group"""
    usages = (
        session.query(
            database.tables.Usage.year,
            sqlalchemy.sql.functions.sum(database.tables.Usage.value),
        )
        .filter(database.tables.Usage.municipal_id == municipal_id)
        .filter(database.tables.Usage.consumer_group_id == consumer_group_id)
        .group_by(database.tables.Usage.year)
        .all()
    )
    usage_values = []
    for data in usages:
        usage_values.append(data[1])
    return models.amqp.WaterUsages(
        start=usages[0][0], end=usages[-1][0], usages=usage_values
    )


def get_last_database_update(
    schema_name: str, engine: sqlalchemy.engine.Engine
) -> datetime.datetime:
    query = (
        f"SELECT UPDATE_TIME "
        f"FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA = \"{schema_name}\" "
        f"ORDER BY UPDATE_TIME DESC LIMIT 1;"
    )
    result = engine.execute(query)
    for time in result:
        logging.info(time)
        return time

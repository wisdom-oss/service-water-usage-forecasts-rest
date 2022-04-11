import datetime
import logging

import pytz.reference
import sqlalchemy.sql.functions

import database.crud
import database.tables
import exceptions
import models.amqp


def get_water_usage_data(municipal_id, consumer_group_id, session):
    """Get the water usages per year for the supplied municipal and consumer group"""
    query = f"SELECT year, sum(value) " \
            f"FROM water_usage.usages " \
            f"WHERE municipal = {municipal_id} " \
            f"AND consumer_group = {consumer_group_id} " \
            f"GROUP BY year " \
            f"ORDER BY year"
    usages = database.engine().execute(query).all()
    usage_values = []
    for data in usages:
        usage_values.append(float(data[1]))
    if len(usage_values) < 3:
        raise exceptions.InsufficientDataError(consumer_group_id, municipal_id)
    return models.amqp.WaterUsages(
        start=int(usages[0][0]), end=int(usages[-1][0]), usages=usage_values
    )


def get_last_database_update(
    schema_name: str, engine: sqlalchemy.engine.Engine
) -> datetime.datetime:
    query = (
        f"SELECT timestamp "
        f"FROM public.audit "
        f"WHERE schema_name = {schema_name} "
        f"ORDER BY timestamp DESC "
        f"LIMIT 1"
    )
    result = engine.execute(query)
    for time in result:
        logging.info(time)
        return time

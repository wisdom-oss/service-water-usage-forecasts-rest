import datetime
import logging

import pytz.reference
import sqlalchemy.sql.functions


def get_last_database_update(
    schema_name: str, engine: sqlalchemy.engine.Engine
) -> datetime.datetime:
    query = (
        f"SELECT timestamp "
        f"FROM public.audit "
        f"WHERE schema_name = '{schema_name}' "
        f"ORDER BY timestamp DESC "
        f"LIMIT 1"
    )
    result = engine.execute(query)
    for time in result:
        logging.info(time)
        return datetime.datetime.fromtimestamp(
            time[0], tz=pytz.reference.LocalTimezone()
        )

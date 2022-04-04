"""Operations which are related to the tables"""
import typing
import sqlalchemy.orm

from . import tables


def get_consumer_group(
    id_or_name: typing.Union[str, int], session: sqlalchemy.orm.Session
) -> tables.ConsumerGroup:
    """
    Get the consumer group matching the id or the name

    :param id_or_name: The id or name of a consumer group
    :type id_or_name: typing.Union(str, int)
    :param session: The database session used for pulling the data
    :type session: sqlalchemy.orm.Session
    :return: The consumer group if it has been found, else None
    :rtype: typing.Optional(tables.ConsumerGroup)
    """
    if type(id_or_name) is str:
        consumer_group = (
            session.query(tables.ConsumerGroup)
            .filter(tables.ConsumerGroup.name == id_or_name)
            .first()
        )
        return consumer_group
    elif type(id_or_name) is int:
        consumer_group = (
            session.query(tables.ConsumerGroup)
            .filter(tables.ConsumerGroup.id == id_or_name)
            .first()
        )
        return consumer_group
    else:
        raise ValueError("The id_or_name parameter was neither a string nor a integer")


def get_municipal(
    id_or_name: typing.Union[str, int], session: sqlalchemy.orm.Session
) -> tables.Municipal:
    """
    Get the municipal matching the id or the name

    :param id_or_name: The id or name of a municipal
    :type id_or_name: typing.Union(str, int)
    :param session: The database session used for pulling the data
    :type session: sqlalchemy.orm.Session
    :return: The municipal if it has been found, else None
    :rtype: typing.Optional(tables.ConsumerGroup)
    """
    if type(id_or_name) is str:
        municipal = (
            session.query(tables.Municipal)
            .filter(tables.Municipal.name == id_or_name)
            .first()
        )
        return municipal
    elif type(id_or_name) is int:
        municipal = (
            session.query(tables.Municipal)
            .filter(tables.Municipal.id == id_or_name)
            .first()
        )
        return municipal
    else:
        raise ValueError("The id_or_name parameter was neither a string nor a integer")


def get_consumer_groups(session: sqlalchemy.orm.Session) -> list[tables.ConsumerGroup]:
    """
    Get a list consisting of all consumer groups listed in the database
    :param session: The database session used to pull the data from the database
    :type session: sqlalchemy.orm.Session
    :return: A list containing all consumer groups
    :rtype: list[tables.ConsumerGroup]
    """
    return session.query(tables.ConsumerGroup).all()


def insert_object(obj, session):
    """
    Insert a new object into the database

    :param obj: The object which shall be inserted
    :type obj: bases ORMDeclarationBase
    :param session: The database session used to insert the object
    :type session: sqlalchemy.orm.Session
    :return: The list of inserted municipals
    :rtype: list
    """
    if not issubclass(type(obj), tables.ORMDeclarationBase):
        raise ValueError(
            "Only instances of ORM objects may be inserted into the database"
        )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

---
sidebar_label: crud
title: database.crud
---

Operations which are related to the tables


#### get\_consumer\_group

```python
def get_consumer_group(
        id_or_name: typing.Union[str, int],
        session: sqlalchemy.orm.Session) -> tables.ConsumerGroup
```

Get the consumer group matching the id or the name

**Arguments**:

- `id_or_name` (`typing.Union(str, int)`): The id or name of a consumer group
- `session` (`sqlalchemy.orm.Session`): The database session used for pulling the data

**Returns**:

`typing.Optional(tables.ConsumerGroup)`: The consumer group if it has been found, else None

#### get\_consumer\_groups

```python
def get_consumer_groups(
        session: sqlalchemy.orm.Session) -> list[tables.ConsumerGroup]
```

Get a list consisting of all consumer groups listed in the database

**Arguments**:

- `session` (`sqlalchemy.orm.Session`): The database session used to pull the data from the database

**Returns**:

`list[tables.ConsumerGroup]`: A list containing all consumer groups

#### get\_municipal

```python
def get_municipal(id_or_name: typing.Union[str, int],
                  session: sqlalchemy.orm.Session) -> tables.Municipal
```

Get the municipal matching the id or the name

**Arguments**:

- `id_or_name` (`str | int`): The id or name of a consumer group
- `session` (`sqlalchemy.orm.Session`): The database session used for pulling the data

**Returns**:

`tables.Municipal`: The municipal if it has been found else None

#### insert\_object

```python
def insert_object(obj, session: sqlalchemy.orm.Session)
```

Insert a new object into the database

**Arguments**:

- `obj` (`bases ORMDeclarationBase`): The object which shall be inserted
- `session` (`sqlalchemy.orm.Session`): The database session used to insert the object

**Returns**:

`list`: The list of inserted municipals


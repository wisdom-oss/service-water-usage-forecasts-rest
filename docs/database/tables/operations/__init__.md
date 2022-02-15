---
sidebar_label: operations
title: database.tables.operations
---

Collection of generic operations run on the database


#### get\_consumer\_group\_id

```python
def get_consumer_group_id(consumer_group: ConsumerGroup, db: Session) -> Optional[int]
```

Get the ID of a consumer group

**Arguments**:

- `consumer_group`: Consumer Group Enumeration value for which the id should be looked up
- `db`: Database Session

**Returns**:

The integer id of the consumer group. None if the consumer group does not exist in
the database

#### get\_consumer\_type\_id

```python
def get_consumer_type_id(consumer_type: str, db: Session) -> Optional[int]
```

Get the ID of a consumer group defined in the database

**Arguments**:

- `consumer_type`: Consumer Type
- `db`: Database connection

#### get\_commune\_id

```python
def get_commune_id(district, db)
```

Get the id (primary key) of the commune with the name supplied.

**Arguments**:

- `district`: Name of the commune
- `db`: Database connection

**Returns**:

The commune id if the commune exists. Else None

#### get\_county\_id

```python
def get_county_id(district, db)
```

Get the id (primary key) of the commune with the name supplied.

**Arguments**:

- `district`: Name of the commune
- `db`: Database connection

**Returns**:

The commune id if the commune exists. Else None

#### get\_communes\_in\_county

```python
def get_communes_in_county(county: str, db) -> List[int]
```

Get the ids of the communes in a county

**Arguments**:

- `county`: Name of the county
- `db`: Database connection

#### get\_commune\_names

```python
def get_commune_names(db: Session) -> List[str]
```

Get all names of the communes in the database

**Arguments**:

- `db`: Database connection

#### get\_county\_names

```python
def get_county_names(db: Session) -> List[str]
```

Get the names of all available counties

**Arguments**:

- `db`: Database connection

#### insert\_object

```python
def insert_object(obj: Union[Commune, County, ConsumerType, WaterUsageAmount], db: Session) -> Union[Commune, County, ConsumerType, WaterUsageAmount]
```

Insert a new object into the database

**Arguments**:

- `obj`: The object which shall be inserted
- `db`: Database connection


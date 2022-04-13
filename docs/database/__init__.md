---
sidebar_label: database
title: database
---

#### session

```python
def session() -> sqlalchemy.orm.Session
```

Get an opened session to the database

**Returns**:

`sqlalchemy.orm.Session`: The opened database session

#### engine

```python
def engine() -> sqlalchemy.engine.Engine
```

Get the database engine

**Returns**:

`sqlalchemy.engine.Engine`: The database engine used to connect to the database


---
sidebar_label: database
title: database
---

Module for organizing the database connections and operations


#### get\_database\_session

```python
def get_database_session() -> DatabaseSession
```

Get an opened Database session which can be used to query data

**Returns**:

`DatabaseSession`: Database Session

#### initialise\_orm\_models

```python
def initialise_orm_models()
```

Initialize the ORM models and create the necessary metadata



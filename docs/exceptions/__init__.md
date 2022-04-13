---
sidebar_label: exceptions
title: exceptions
---

Module for custom Exceptions for generating error messages


## APIException Objects

```python
class APIException(Exception)
```

Base class for all custom exceptions for using the Http API


## DuplicateEntryError Objects

```python
class DuplicateEntryError(Exception)
```

A INSERT operation failed since a constraint (e.g. unique or primary key) was violated


## QueryDataError Objects

```python
class QueryDataError(APIException)
```

An Exception raised for errors in the Query Data


#### \_\_init\_\_

```python
def __init__(short_error: str, error_description: str)
```

New Query Data Exception

**Arguments**:

- `short_error`: Short error code
- `error_description`: Description for the reason behind raising the exception

## InsufficientDataError Objects

```python
class InsufficientDataError(APIException)
```

#### \_\_init\_\_

```python
def __init__(consumer_group_id: int, municipality_id: int)
```

New Insufficient data error

**Arguments**:

- `consumer_group_id` (`int`): The consumer group id for which is no sufficient data present
- `municipality_id` (`int`): The municipality in which the data is missing


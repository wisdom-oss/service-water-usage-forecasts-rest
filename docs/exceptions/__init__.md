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
class DuplicateEntryError(IntegrityError)
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


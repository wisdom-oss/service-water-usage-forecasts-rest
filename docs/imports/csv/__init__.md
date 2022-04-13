---
sidebar_label: csv
title: imports.csv
---

Import module for importing csv files into the system


#### import\_municipals

```python
def import_municipals(
        file_path: typing.Union[str, bytes,
                                os.PathLike], session: sqlalchemy.orm.Session
) -> typing.List[database.tables.Municipal]
```

Read the given csv file and write the found municipals into the database

**Arguments**:

- `file_path` (`str, bytes, os.PathLike`): The path pointing to the CSV file
- `session` (`sqlalchemy.orm.Session`): The database session used to insert the data

**Returns**:

`list[database.tables.Municipal]`: The list of the inserted object

#### import\_usages

```python
def import_usages(
        file_path: typing.Union[str, bytes, os.PathLike],
        session: sqlalchemy.orm.Session) -> typing.List[database.tables.Usage]
```

Read the given csv file and write the found usages into the database

**Arguments**:

- `file_path` (`str, bytes, os.PathLike`): The path pointing to the CSV file
- `session` (`sqlalchemy.orm.Session`): The database session used to insert the data

**Returns**:

`list[database.tables.Municipal]`: The list of the inserted object


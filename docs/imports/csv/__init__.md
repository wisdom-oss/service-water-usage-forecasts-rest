---
sidebar_label: csv
title: imports.csv
---

Import module for importing csv files into the system


#### import\_counties\_from\_file

```python
def import_counties_from_file(file_path: Union[str, bytes, os.PathLike], db_session: Session) -> List[County]
```

Import a set of counties into the database

**Arguments**:

- `db_session`: Database session used to insert the single rows
- `file_path`: Path to the CSV file containing the new counties

**Raises**:

- `FileNotFoundError`: The path supplied does not point to a file
- `DuplicateEntryError`: The file contains an entry which is already in the database

**Returns**:

After the successful import it will return all inserted orm items

#### import\_communes\_from\_file

```python
def import_communes_from_file(file_path: Union[str, bytes, os.PathLike], db_session: Session) -> List[Commune]
```

Import communes into the database

This import will also create the foreign key relations for communes in counties

**Arguments**:

- `db_session`: Database session used to insert the single rows
- `file_path`: Path to the file containing the commune data

**Raises**:

- `FileNotFoundError`: The path supplied does not point to a file
- `DuplicateEntryError`: The file contains an entry which is already in the database

**Returns**:

List of created communes

#### import\_consumer\_types\_from\_file

```python
def import_consumer_types_from_file(file_path: Union[str, bytes, os.PathLike], db_session: Session) -> List[ConsumerType]
```

Import new consumer types from a csv file

**Arguments**:

- `db_session`: Database session used to insert the single rows
- `file_path`: Path to the file containing the consumer types

**Raises**:

- `FileNotFoundError`: The path supplied does not point to a file
- `DuplicateEntryError`: The file contains an entry which is already in the database

**Returns**:

List of inserted consumer types

#### import\_water\_usages\_from\_file

```python
def import_water_usages_from_file(file_path: Union[str, bytes, os.PathLike], db_session: Session) -> List[WaterUsageAmount]
```

Import new water usages from a csv file

**Arguments**:

- `db_session`: Database session used to insert the single rows
- `file_path`: Path to the file containing the water usages

**Raises**:

- `FileNotFoundError`: The path supplied does not point to a file
- `InconsistentDataError`: The import process found a not recoverable data error (often
missing usage amount)

**Returns**:

List of inserted water usage values


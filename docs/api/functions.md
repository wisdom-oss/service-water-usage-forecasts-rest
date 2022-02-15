---
sidebar_label: functions
title: api.functions
---

Module for outsourced functions for better maintainability


#### district\_in\_spatial\_unit

```python
def district_in_spatial_unit(district: str, spatial_unit: SpatialUnit, db: Session) -> bool
```

Check if a queried district is in the spatial unit

This method will check by looking in the table of the spatial unit. If a unit is found in the
database table then this method will return true

**Arguments**:

- `district` (`str`): District queried in the request
- `spatial_unit` (`SpatialUnit`): Spatial unit set in the request
- `db` (`Session`): Database Session

**Returns**:

`bool`: True if a unit is found in its spatial unit, False if not

#### get\_water\_usage\_data

```python
def get_water_usage_data(district: str, spatial_unit: SpatialUnit, db: Session, consumer_group: ConsumerGroup = ConsumerGroup.ALL)
```

Get the water usage amounts per year

**Arguments**:

- `consumer_group`: 
- `db`: 
- `district`: 
- `spatial_unit`: 


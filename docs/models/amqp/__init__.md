---
sidebar_label: amqp
title: models.amqp
---

## TokenIntrospectionRequest Objects

```python
class TokenIntrospectionRequest(BaseModel)
```

#### bearer\_token

The bearer token which shall be validated


#### scopes

The scopes the token needs to access this resource


## WaterUsages Objects

```python
class WaterUsages(BaseModel)
```

A model for the current water usages


#### start

Start Year

The data contained in the ``usages`` list start in this year


#### end

End Year

The data contained in the ``usages`` list ends in this year


#### usages

Water Usage Amounts

Every entry in this list depicts the water usage of year between the ``start`` and ``end``
attribute of this object. The list needs to be ordered by the corresponding years


#### check\_data\_consistency

```python
@pydantic.root_validator
def check_data_consistency(cls, values)
```

Check if the data is consistent between itself. Meaning for every year is a water usage

amount in the list present and the values for start and end are not switched or equal


## ForecastRequest Objects

```python
class ForecastRequest(BaseModel)
```

#### type

Forecast Type

The type of forecast which shall be executed


#### predicted\_years

Predicted Years

The amount of years which shall be predicted with the supplied model


#### usage\_data

Actual water usage data

This object contains the current water usages and the range of years for the current water
usages



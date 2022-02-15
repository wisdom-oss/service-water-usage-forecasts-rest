---
sidebar_label: requests
title: models.requests
---

Models for the incoming requests


## RealData Objects

```python
class RealData(BaseModel)
```

Data model for the incoming real water usage data.


## Config Objects

```python
class Config()
```

Configuration for the RealData model


#### check\_data\_consistency

```python
@root_validator
def check_data_consistency(cls, values)
```

Pydantic validator which will check for the consistency between the given time period

and the supplied usage amounts

**Arguments**:

- `values`: 

## ForecastRequest Objects

```python
class ForecastRequest(RealData)
```

Model for describing the incoming forecast request, which will be used to build the amqp message



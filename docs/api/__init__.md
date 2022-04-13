---
sidebar_label: api
title: api
---

#### \_service\_startup

```python
@service.on_event("startup")
def _service_startup()
```

Handler for the service startup


#### \_service\_shutdown

```python
@service.on_event("shutdown")
def _service_shutdown()
```

Handle the service shutdown


#### \_token\_check

```python
@service.middleware("http")
async def _token_check(request: starlette.requests.Request, call_next)
```

Intercept every request made to this service and check if the request contains a Bearer token

and check if the bearer token has the correct scope for this service

**Arguments**:

- `request` (`starlette.requests.Request`): The incoming request
- `call_next` (`callable`): The next action which shall be called to generate the response

**Returns**:

`starlette.responses.Response`: The response which has been generated

#### forecast

```python
@service.get(path="/{spatial_unit}/{forecast_model}")
async def forecast(
    spatial_unit: enums.SpatialUnit,
    forecast_model: enums.ForecastModel,
    districts: list[str] = fastapi.Query(default=..., alias="district"),
    consumer_groups: list[str] = fastapi.Query(default=None,
                                               alias="consumerGroup"),
    session: sqlalchemy.orm.Session = fastapi.Depends(database.session))
```

Execute a new forecast

**Arguments**:

- `spatial_unit` (`enums.SpatialUnit`): The spatial unit used for the request
- `forecast_model` (`enums.ForecastModel`): The forecast model which shall be used
- `districts` (`list[str]`): The districts that shall be used for the forecasts
- `consumer_groups` (`list[str], optional`): Consumer Groups which shall be included in the forecasts. If no
consumer group was transmitted the forecast will be executed for all consumer groups and
values with no consumer groups
- `session` (`sqlalchemy.orm.Session`): The session used to access the database

**Returns**:

`list[dict]`: A list with the results of the forecast


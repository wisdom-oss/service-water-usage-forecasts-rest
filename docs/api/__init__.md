---
sidebar_label: api
title: api
---

Module in which the server is described and all ops of the server are commenced in


#### water\_usage\_forecasts\_rest

Fast API Application for this service


#### startup

```python
@water_usage_forecasts_rest.on_event('startup')
async def startup()
```

Startup Event Handler

This event handler will automatically register this service at the service registry,
create the necessary databases and tables and will start a rpc client which will send
messages to the forecasting module


#### shutdown

```python
@water_usage_forecasts_rest.on_event('shutdown')
async def shutdown()
```

Shutdown event handler

This event handler will deregister the service from the service registry


#### request\_validation\_error\_handler

```python
@water_usage_forecasts_rest.exception_handler(RequestValidationError)
async def request_validation_error_handler(__request: Request, exc: RequestValidationError)
```

Error handler for request validation errors

These errors will occur if the request data is not valid. This error handler just changes the
status from 422 (Unprocessable Entity) to 400 (Bad Request)


#### query\_data\_error\_handler

```python
@water_usage_forecasts_rest.exception_handler(QueryDataError)
async def query_data_error_handler(_request: Request, exc: QueryDataError)
```

Error handler for querying data which is not available

This error handler will return a status code 400 (Bad Request) alongside with some
information on the reason for the error


#### query\_data\_error\_handler

```python
@water_usage_forecasts_rest.exception_handler(exceptions.DuplicateEntryError)
async def query_data_error_handler(_request: Request, exc: exceptions.DuplicateEntryError)
```

Error handler for querying data which is not available

This error handler will return a status code 400 (Bad Request) alongside with some
information on the reason for the error


#### run\_prognosis

```python
@water_usage_forecasts_rest.get(path='/{spatial_unit}/{district}/{forecast_type}')
async def run_prognosis(spatial_unit: SpatialUnit, district: str, forecast_type: ForecastType, consumer_group: ConsumerGroup = Query(ConsumerGroup.ALL, alias='consumerGroup'), db_connection: Session = Depends(database.get_database_session))
```

Run a new prognosis

**Arguments**:

- `spatial_unit` (`SpatialUnit`): Selected spatial unit
- `district` (`str`): The district in the selected spatial unit
- `forecast_type` (`ForecastType`): The model which shall be used during broadcasting
- `consumer_group` (`ConsumerGroup`): The consumer group whose water usages shall be predicted, defaults to all
- `db_connection` (`Session`): Connection to the database used to do some queries

#### put\_new\_datafile

```python
import enums


@water_usage_forecasts_rest.put(
    path='/import/{datatype}',
    status_code=201
)
async def put_new_datafile(datatype: enums.ImportDataTypes, data: UploadFile = File(...),
                           db_connection: Session = Depends(database.get_database_session))
```

Import a new set of data into the database

**Arguments**:

- `db_connection`: 
- `datatype`: The type of data which shall be imported
- `data`: The file which shall be imported

**Returns**:

If the request was a success it will send a 201 code back

#### get\_available\_parameters

```python
@water_usage_forecasts_rest.get('/')
async def get_available_parameters(db: Session = Depends(database.get_database_session))
```

Get all possible parameters

**Arguments**:

- `db`: 

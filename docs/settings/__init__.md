---
sidebar_label: settings
title: settings
---

Module containing all settings which are used in the application


## ServiceSettings Objects

```python
class ServiceSettings(BaseSettings)
```

Settings related to the general execution


#### name

Service Name

The name of this service which is used for registering at the service registry and for
identifying this service in AMQP requests. Furthermore, this value is used as part of the
authentication in AMQP requests


#### http\_port

Uvicorn HTTP Port

The HTTP port which will be bound by the internal HTTP server at the startup of the service.
This port will also be announced to the service registry as application port


#### log\_level

Logging Level

The level of logging which will be visible on the console


## Config Objects

```python
class Config()
```

Configuration of the service settings


#### env\_file

Allow loading the values for the service settings from the specified file


## ServiceRegistrySettings Objects

```python
class ServiceRegistrySettings(BaseSettings)
```

Settings related to the connection to the service registry


#### host

Service registry host (required)

The hostname or ip address of the service registry on which this service shall register itself


#### port

Service registry port

The port on which the service registry listens on, defaults to 8761


## Config Objects

```python
class Config()
```

Configuration of the service registry settings


#### env\_file

The location of the environment file from which these values may be loaded


## AMQPSettings Objects

```python
class AMQPSettings(BaseSettings)
```

Settings related to the AMQP connection and the communication


#### dsn

AMQP Data Source Name [REQUIRED]

The URI pointing to the installation of a AMQP-0-9-1 compatible message broker


#### exchange

AMQP Exchange Name [OPTIONAL, default value: `water-usage-forecasts`]

The name of the AMQP exchange which this service listens on for new messages


## Config Objects

```python
class Config()
```

Configuration of the AMQP connection settings


#### env\_file

The location of the environment file from which the settings may be read


## DatabaseSettings Objects

```python
class DatabaseSettings(BaseSettings)
```

Settings related to the database connection


#### dsn

PostgresSQL Data Source Name [REQUIRED]

An URI pointing to the PostgresSQL instance containing the database which contains the water
usage amounts and related values


## Config Objects

```python
class Config()
```

Configuration of the AMQP related settings


#### env\_file

The file from which the settings may be read


## SecuritySettings Objects

```python
class SecuritySettings(BaseSettings)
```

Security related settings


#### authorization\_exchange

Authorization Exchange

The name of the exchange the queues of the authorization service are bound to



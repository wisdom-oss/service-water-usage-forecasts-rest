---
sidebar_label: models
title: models
---

Model for sorting the data models used throughout this project


## ServiceSettings Objects

```python
class ServiceSettings(BaseSettings)
```

Settings for this service


#### database\_dsn

URL pointing to the MariaDB/MySQL Database containing the water usage data


#### service\_registry\_url

Host of the service registry instance


#### amqp\_url

URL containing the credentials and address of the message broker


#### amqp\_exchange

Name of the exchange in which messages will be published



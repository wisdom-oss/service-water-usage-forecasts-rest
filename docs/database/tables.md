---
sidebar_label: tables
title: database.tables
---

Object-Relational-Mapping classes for the used database tables


#### initialize\_mappings

```python
def initialize_mappings()
```

Initialize the object-relational mapping classes for this service


## ConsumerGroup Objects

```python
class ConsumerGroup(ORMDeclarationBase)
```

#### id

The *internal* ID of the consumer group


#### name

The name of the consumer group


#### description

The description of the consumer group


#### parameter

The query parameter value by which this consumer group is identified


## Usage Objects

```python
class Usage(ORMDeclarationBase)
```

A documentation of an occurred water usage


#### id

The *internal* ID of the usage


#### municipal\_id

The *internal* ID of the municipal in which the usage has been recorded


#### consumer\_id

The *internal* ID of the consumer for which the usage has been recorded


#### consumer\_group\_id

The *internal* ID of the consumer group which has been associated with the usage record


#### value

The used amount of water in cubic meters (m³)


#### year

The year in which the usage has been recorded


## Municipal Objects

```python
class Municipal(GeodataDeclarationBase)
```



## GeoMunicipal Objects

```python
class GeoMunicipal(GeodataDeclarationBase)
```

A Municipal from the geodata storage of this project


## District Objects

```python
class District(GeodataDeclarationBase)
```

A district from the geodata storage of the project



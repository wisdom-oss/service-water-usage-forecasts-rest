---
sidebar_label: messaging
title: messaging
---

Async


## AMQPRPCClient Objects

```python
class AMQPRPCClient()
```

This publisher will send out messages to the specified fanout exchange


#### \_\_init\_\_

```python
def __init__(amqp_url, exchange_name)
```

Create a new MessagePublisher

**Arguments**:

- `amqp_url`: AMQP URL specifying the connection details
- `exchange_name`: Name of the exchange the requests should be published to

#### \_\_process\_data\_events

```python
def __process_data_events()
```

Check for new incoming data


#### \_\_on\_message\_received

```python
def __on_message_received(channel: pika.spec.Channel, method: pika.spec.Basic.Deliver, properties: pika.spec.BasicProperties, content: bytes)
```

Handle the received message by adding it to the stack of responses

**Arguments**:

- `channel`: 
- `method`: 
- `properties`: 
- `content`: 

#### publish\_message

```python
def publish_message(request: ForecastRequest) -> Tuple[str, threading.Event]
```

Publish a new message in the exchange for the calculation module

**Arguments**:

- `request`: 

**Returns**:

The correlation id used to send the message


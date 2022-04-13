---
sidebar_label: tools
title: tools
---

#### resolve\_log\_level

```python
def resolve_log_level(level: str) -> int
```

Resolve the logging level from a string

This method will try to get the actual logging level from the logging package

If no valid logging level is supplied this method will return the info level

**Arguments**:

- `level`: The name of the level which should be resolved

**Returns**:

The logging level which may be used in the configuration of loggers

#### is\_host\_available

```python
async def is_host_available(host: str, port: int, timeout: int = 10) -> bool
```

Check if the specified host is reachable on the specified port

**Arguments**:

- `host`: The hostname or ip address which shall be checked
- `port`: The port which shall be checked
- `timeout`: Max. duration of the check

**Returns**:

A boolean indicating the status


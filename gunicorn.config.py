import asyncio
import logging
import multiprocessing
import sys
import typing

import py_eureka_client.eureka_client
import pydantic

import settings
import tools

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
limit_request_line = 0
limit_request_fields = 0
limit_request_field_size = 0
worker_class = "uvicorn.workers.UvicornWorker"
max_requests = 1
timeout = 120

_registry_client: typing.Optional[py_eureka_client.eureka_client.EurekaClient] = None


def on_starting(server):
    _service_settings = settings.ServiceSettings()
    try:
        _registry_settings = settings.ServiceRegistrySettings()
    except pydantic.ValidationError:
        logging.critical(
            "Unable to read the service registry related settings. Please refer to "
            "the documentation for further instructions: "
            "SERVICE_REGISTRY_SETTINGS_INVALID"
        )
        sys.exit(1)
    logging.info("Checking the connection to the service registry")
    _registry_available = asyncio.run(
        tools.is_host_available(
            host=_registry_settings.host, port=_registry_settings.port, timeout=60
        )
    )
    if not _registry_available:
        logging.critical(
            "The service registry is not reachable. Therefore, this service is unable to register "
            "itself at the service registry and it is not callable"
        )
        sys.exit(2)
    global _registry_client
    _registry_client = py_eureka_client.eureka_client.EurekaClient(
        eureka_server=f"http://{_registry_settings.host}:{_registry_settings.port}/",
        app_name=_service_settings.name,
        instance_port=5000,
        should_register=True,
        should_discover=False,
        renewal_interval_in_secs=5,
        duration_in_secs=30,
    )
    _registry_client.start()
    _registry_client.status_update("STARTING")


def when_ready(server):
    _registry_client.status_update("UP")


def on_exit(server):
    _registry_client.stop()

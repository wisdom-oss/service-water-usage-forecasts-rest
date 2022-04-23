"""Module containing all settings which are used in the application"""
import pydantic
from pydantic import BaseSettings, AmqpDsn, Field, PostgresDsn


class ServiceSettings(BaseSettings):
    """Settings related to the general execution"""

    name: str = pydantic.Field(
        default="water-usage-forecasts-calculations-rest",
        alias="CONFIG_SERVICE_NAME",
        env="CONFIG_SERVICE_NAME",
    )
    """
    Microservice Name

    The name of the service which is used for registering at the service registry
    """

    logging_level: str = pydantic.Field(
        default="INFO", alias="CONFIG_LOGGING_LEVEL", env="CONFIG_LOGGING_LEVEL"
    )
    """
    Logging Level

    The logging level which will be visible on the stdout
    """

    http_port: int = Field(
        default=5000,
        title="Uvicorn HTTP Port",
        description="The HTTP port which will be bound by the internal HTTP server at the startup "
        "of the service",
        env="CONFIG_SERVICE_HTTP_PORT",
    )
    """
    Uvicorn HTTP Port
    
    The HTTP port which will be bound by the internal HTTP server at the startup of the service.
    This port will also be announced to the service registry as application port
    """

    class Config:
        """Configuration of the service settings"""

        env_file = ".env"
        """Allow loading the values for the service settings from the specified file"""


class ServiceRegistrySettings(BaseSettings):
    """Settings related to the connection to the service registry"""

    host: str = Field(
        default=...,
        title="Service registry host",
        description="The hostname or ip address of the service registry on which this service "
        "shall register itself",
        env="CONFIG_SERVICE_REGISTRY_HOST",
    )
    """
    Service registry host (required)

    The hostname or ip address of the service registry on which this service shall register itself
    """

    port: int = Field(
        default=8761,
        title="Service registry port",
        description="The port on which the service registry listens on, defaults to 8761",
        env="CONFIG_SERVICE_REGISTRY_PORT",
    )
    """
    Service registry port

    The port on which the service registry listens on, defaults to 8761
    """

    class Config:
        """Configuration of the service registry settings"""

        env_file = ".env"
        """The location of the environment file from which these values may be loaded"""


class AMQPSettings(pydantic.BaseSettings):
    """Settings which are related to the communication with our message broker"""

    dsn: pydantic.AmqpDsn = pydantic.Field(
        default=..., alias="CONFIG_AMQP_DSN", env="CONFIG_AMQP_DSN"
    )
    """
    Advanced Message Queueing Protocol data source name

    The data source name (expressed as URI) pointing to a AMQPv-0-9-1 compatible message broker
    """

    exchange: str = pydantic.Field(
        default="water-usage-forecasts",
        alias="CONFIG_AMQP_EXCHANGE",
        env="CONFIG_AMQP_EXCHANGE",
    )
    """
    Incoming Message Broker Exchange

    The exchange that this service will bind itself to, for receiving messages
    """

    class Config:
        env_file = ".env"


class DatabaseSettings(pydantic.BaseSettings):
    """Settings which are related to the database connection"""

    dsn: pydantic.PostgresDsn = pydantic.Field(
        default=..., alias="CONFIG_DB_DSN", env="CONFIG_DB_DSN"
    )
    """
    PostgreSQL data source name

    The data source name (expressed as URI) pointing to the installation of the used postgresql database
    """

    class Config:
        env_file = ".env"


class SecuritySettings(BaseSettings):
    """Security related settings"""

    authorization_exchange: str = Field(
        default="authorization-service",
        title="Name of the exchange which is bound to the authorization service",
        env="AUTHORIZATION_EXCHANGE",
    )
    """
    Authorization Exchange
    
    The name of the exchange the queues of the authorization service are bound to
    """

    class Config:
        env_file = ".env"

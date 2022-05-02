import pydantic


class BaseSettings(pydantic.BaseSettings):
    class Config:
        env_file = ".env"


class ServiceSettings(BaseSettings):
    """Settings related to the general execution of the service"""

    name: str = pydantic.Field(
        default="water-usage-forecasts-rest",
        alias="CONFIG_SERVICE_NAME",
        env="CONFIG_SERVICE_NAME",
    )
    """
    Microservice Name

    The name of this microservice. The name will be used for registering at the service registry
    and as prefix for errors which may be generated
    """

    logging_level: str = pydantic.Field(
        default="INFO", alias="CONFIG_LOGGING_LEVEL", env="CONFIG_LOGGING_LEVEL"
    )
    """
    Logging Level

    The logging level which will be used by the root logger
    """

    class Config:
        env_file = ".env"


class AMQPSettings(BaseSettings):

    dsn: pydantic.AmqpDsn = pydantic.Field(
        default=..., alias="CONFIG_AMQP_DSN", env="CONFIG_AMQP_DSN"
    )
    """
    Advanced Message Queueing Protocol data source name

    The data source name expressed as URI pointing to an AMQPv0-9-1 compatible message broker
    """

    exchange: str = pydantic.Field(
        default=..., alias="CONFIG_AMQP_EXCHANGE", env="CONFIG_AMQP_EXCHANGE"
    )
    """
    Advanced Message Queueing Protocol Exchange

    The name of the exchange the service will publish it's messages into
    """

    class Config:
        env_file = ".env"


class DatabaseSettings(BaseSettings):
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

    authorization_exchange: str = pydantic.Field(
        default="authorization-service",
        alias="CONFIG_AUTHORIZATION_EXCHANGE",
        env="CONFIG_AUTHORIZATION_EXCHANGE",
    )
    """
    Authorization Exchange

    The name of the exchange the queues of the authorization service are bound to
    """

    class Config:
        env_file = ".env"


class ServiceRegistrySettings(BaseSettings):
    """Settings related to the connection to the service registry"""

    host: str = pydantic.Field(
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

    port: int = pydantic.Field(
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
        env_file = ".env"

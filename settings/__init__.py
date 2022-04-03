"""Module containing all settings which are used in the application"""
from pydantic import BaseSettings, AmqpDsn, Field, stricturl, SecretStr


class ServiceSettings(BaseSettings):
    """Settings related to the general execution"""

    name: str = Field(
        default="water-usage-forecasts-rest",
        title="Service Name",
        description="The name of this service which is used for registering at the service "
        "registry and for identifying this service in AMQP requests",
        env="SERVICE_NAME",
    )
    """
    Service Name
    
    The name of this service which is used for registering at the service registry and for
    identifying this service in AMQP requests. Furthermore, this value is used as part of the
    authentication in AMQP requests
    """

    http_port: int = Field(
        default=5000,
        title="Uvicorn HTTP Port",
        description="The HTTP port which will be bound by the internal HTTP server at the startup "
        "of the service",
        env="SERVICE_HTTP_PORT",
    )
    """
    Uvicorn HTTP Port
    
    The HTTP port which will be bound by the internal HTTP server at the startup of the service.
    This port will also be announced to the service registry as application port
    """

    log_level: str = Field(
        default="INFO",
        title="Logging Level",
        description="The level of logging which will be visible",
        env="SERVICE_LOG_LEVEL",
    )
    """
    Logging Level
    
    The level of logging which will be visible on the console
    """

    class Config:
        """Configuration of the service settings"""

        env_file = ".application.env"
        """Allow loading the values for the service settings from the specified file"""


class ServiceRegistrySettings(BaseSettings):
    """Settings related to the connection to the service registry"""

    host: str = Field(
        default=...,
        title="Service registry host",
        description="The hostname or ip address of the service registry on which this service "
        "shall register itself",
        env="SERVICE_REGISTRY_HOST",
    )
    """
    Service registry host (required)

    The hostname or ip address of the service registry on which this service shall register itself
    """

    port: int = Field(
        default=8761,
        title="Service registry port",
        description="The port on which the service registry listens on, defaults to 8761",
        env="SERVICE_REGISTRY_PORT",
    )
    """
    Service registry port

    The port on which the service registry listens on, defaults to 8761
    """

    class Config:
        """Configuration of the service registry settings"""

        env_file = ".registry.env"
        """The location of the environment file from which these values may be loaded"""


class AMQPSettings(BaseSettings):
    """Settings related to the AMQP connection and the communication"""

    dsn: AmqpDsn = Field(
        default=...,
        title="AMQP Data Source Name",
        description="The URI pointing to the installation of a AMQP-0-9-1 compatible message "
        "broker",
        env="AMQP_DSN",
    )
    """
    AMQP Data Source Name [REQUIRED]

    The URI pointing to the installation of a AMQP-0-9-1 compatible message broker
    """

    exchange: str = Field(
        default="water-usage-forecasts",
        title="AMQP Exchange Name",
        description="The name of the AMQP exchange this service sends messages to",
        env="AMQP_EXCHANGE",
    )
    """
    AMQP Exchange Name [OPTIONAL, default value: `water-usage-forecasts`]

    The name of the AMQP exchange which this service listens on for new messages
    """

    class Config:
        """Configuration of the AMQP connection settings"""

        env_file = ".amqp.env"
        """The location of the environment file from which the settings may be read"""


class DatabaseSettings(BaseSettings):
    """Settings related to the database connection"""

    dsn: stricturl(
        tld_required=False, allowed_schemes={"mariadb+pymysql", "mysql+pymysql"}
    ) = Field(
        default=...,
        title="MariaDB Data Source Name",
        description="A URI pointing to the MariaDB Database and instance containing the water "
        "usage amounts for this service",
        env="DATABASE_DSN",
    )
    """
    MariaDB Data Source Name [REQUIRED]
    
    An URI pointing to the MariaDB instance containing the database which contains the water
    usage amounts and related values
    """

    class Config:
        """Configuration of the AMQP related settings"""

        env_file = ".database.env"
        """The file from which the settings may be read"""


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
        env_file = ".security.env"

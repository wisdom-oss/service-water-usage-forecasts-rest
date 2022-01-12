"""Model for sorting the data models used throughout this project"""
from pydantic import BaseSettings, Field, stricturl


class ServiceSettings(BaseSettings):
    """
    Settings for this service
    """
    database_dsn: stricturl(tld_required=False, allowed_schemes={"mariadb+pymysql"}) = Field(
        default=...,
        env='DATABASE_DSN'
    )
    """URL pointing to the MariaDB/MySQL Database containing the water usage data"""

    service_registry_url: str = Field(
        default=...,
        env='SERVICE_REGISTRY_URL'
    )
    """URL Pointing to the Eureka Server installation of this instance"""

    amqp_url: stricturl(tld_required=False, allowed_schemes={"amqp"}) = Field(
        default=...,
        env="AMQP_URL"
    )
    """URL containing the credentials and address of the message broker"""

    amqp_exchange: str = Field(
        default='weather-forecast-requests',
        env="AMQP_EXCHANGE"
    )
    """Name of the exchange in which messages will be published"""

"""Object-Relational-Mapping classes for the used database tables"""
import sqlalchemy.orm
from . import engine

ORMDeclarationBase = sqlalchemy.orm.declarative_base(name="ORMDeclarationBase")


def initialize_mappings():
    """
    Initialize the object-relational mapping classes for this service
    """
    ORMDeclarationBase.metadata.create_all(bind=engine())


class Municipal(ORMDeclarationBase):
    """
    A municipal in which a usage of water was documented
    """

    __tablename__ = "municipals"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    """The *internal* ID of the municipal"""

    name: str = sqlalchemy.Column(sqlalchemy.String(length=255), unique=True)
    """The name of the municipal"""


class ConsumerGroup(ORMDeclarationBase):

    __tablename__ = "consumer_groups"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    """The *internal* ID of the consumer group"""

    name: str = sqlalchemy.Column(sqlalchemy.String(length=255), unique=True)
    """The name of the consumer group"""

    description: str = sqlalchemy.Column(sqlalchemy.Text)
    """The description of the consumer group"""


class Usage(ORMDeclarationBase):
    """
    A documentation of an occurred water usage
    """

    __tablename__ = "usages"

    id: int = sqlalchemy.Column(
        sqlalchemy.Integer, primary_key=True, autoincrement=True
    )
    """The *internal* ID of the usage"""

    municipal_id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("municipals.id", ondelete="SET NULL", onupdate="CASCADE"),
        name="municipal",
        nullable=True,
    )
    """The *internal* ID of the municipal in which the usage has been recorded"""

    consumer_group_id: int = sqlalchemy.Column(
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("consumer_groups.id"),
        name="consumer_group",
        nullable=True,
    )
    """The *internal* ID of the consumer group which has been associated with the usage record"""

    value: float = sqlalchemy.Column(sqlalchemy.Float)
    """The used amount of water in cubic meters (m³)"""

    year: int = sqlalchemy.Column(sqlalchemy.Integer)
    """The year in which the usage has been recorded"""

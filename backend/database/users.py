import logging

from sqlalchemy import Boolean, Column, String, Integer, DateTime, Sequence

from backend.database.db import Base

logger = logging.getLogger(__name__)


class UserModel(Base):
    __tablename__ = "users"

    # Define sequence for ID
    id_seq = Sequence("user_id_seq", schema="public")

    # Columns matching exactly with Snowflake table
    id = Column(
        "id",
        Integer,
        id_seq,
        server_default=id_seq.next_value(),
        primary_key=True,
        nullable=False,
    )
    username = Column("username", String, nullable=False, unique=True)
    password = Column("password", String, nullable=False)
    email = Column("email", String, nullable=False)
    full_name = Column("full_name", String, nullable=True)
    active = Column("active", Boolean, server_default="TRUE")
    password_timestamp = Column("password_timestamp", Integer, nullable=True)
    created_at = Column(
        "created_at", DateTime, server_default="CURRENT_TIMESTAMP", nullable=False
    )
    modified_at = Column(
        "modified_at", DateTime, server_default="CURRENT_TIMESTAMP", nullable=False
    )

    __table_args__ = {
        "schema": "public"  # Make sure this matches your Snowflake schema
    }
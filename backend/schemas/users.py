from datetime import datetime
from time import time

from pydantic import BaseModel, EmailStr, Field, model_validator

from backend.utils import get_password_hash


class UserRequest(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: str | None = None


class UserCreateRequest(UserRequest):
    active: bool = True
    password_timestamp: int = Field(default_factory=lambda: int(time()))

    @model_validator(mode="after")
    def validator(self) -> "UserCreateRequest":
        self.password = get_password_hash(self.password)
        return self


class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str
    active: bool
    created_at: datetime
    modified_at: datetime

from pydantic import BaseModel, Field
import uuid
from datetime import datetime, date


class UserCreateModel(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=3, max_length=20)
    first_name: str = Field(min_length=3, max_length=20)
    last_name: str = Field(min_length=3, max_length=20)


class UserModel(BaseModel):
    uid: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool
    password_hash: str = Field(exclude=True)
    created_at: datetime
    update_at: datetime

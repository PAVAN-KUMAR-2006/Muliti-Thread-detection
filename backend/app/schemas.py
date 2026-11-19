import re
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def check_password(p: str) -> str:
    if len(p.encode()) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    if len(p) < 10:
        raise ValueError("Password must be at least 10 characters.")
    for pattern, msg in ((r"[A-Z]", "an uppercase letter"), (r"[a-z]", "a lowercase letter"),
                         (r"\d", "a number"), (r"[^A-Za-z0-9]", "a symbol")):
        if not re.search(pattern, p):
            raise ValueError(f"Password must include {msg}.")
    return p


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str

    _pw = field_validator("password")(check_password)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        return " ".join(v.split())


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=2048)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    password: str

    _pw = field_validator("password")(check_password)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut

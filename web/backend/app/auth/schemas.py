"""Pydantic schemas for authentication."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserBase(BaseModel):
    """Base user schema (responses / shared profile shape)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(BaseModel):
    """Strict registration model — only ever validated from normalized keys (login_id, name, password)."""

    model_config = ConfigDict(str_strip_whitespace=False)

    login_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=100)

    @model_validator(mode="after")
    def strip_login_and_name(self) -> "UserCreate":
        """Trim ID and display name; do not trim password (spaces may be intentional)."""
        object.__setattr__(self, "login_id", self.login_id.strip())
        object.__setattr__(self, "name", self.name.strip())
        if not self.login_id:
            raise ValueError("login_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        return self


def user_create_from_register_body(body: dict[str, Any]) -> UserCreate:
    """
    Build UserCreate from raw JSON.

    Never passes a top-level ``email`` key into Pydantic (some stacks still treat it as EmailStr).
    Legacy clients may send ``email``, ``username``, or ``userId``; we map those to ``login_id`` here.
    """
    login_id: str | None = None
    for key in ("login_id", "username", "userId"):
        raw = body.get(key)
        if raw is not None and str(raw).strip() != "":
            login_id = str(raw).strip()
            break
    if login_id is None:
        raw = body.get("email")
        if raw is not None and str(raw).strip() != "":
            login_id = str(raw).strip()
    if login_id is None:
        login_id = ""

    name_raw = body.get("name")
    name_s = str(name_raw).strip() if name_raw is not None else ""

    pw_raw = body.get("password")
    if pw_raw is None:
        pw_s = ""
    elif isinstance(pw_raw, str):
        pw_s = pw_raw
    else:
        pw_s = str(pw_raw)

    return UserCreate.model_validate(
        {"login_id": login_id, "name": name_s, "password": pw_s}
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str  # OAuth2PasswordRequestForm uses 'username'
    password: str


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class Token(BaseModel):
    """Schema for access token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""

    user_id: Optional[int] = None

"""
Pydantic schemas for authentication requests and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# Login/Registration Schemas
# ============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="cashier")  # Role name


class UserLoginRequest(BaseModel):
    """User login request."""

    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation with token."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


# ============================================================================
# User Response Schemas
# ============================================================================


class RoleResponse(BaseModel):
    """Role response."""

    id: UUID
    name: str
    description: Optional[str] = None
    permissions: list = []

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """User response without sensitive data."""

    id: UUID
    username: str
    email: str
    full_name: str
    phone_number: Optional[str] = None
    role: RoleResponse
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    """User detail response with additional info."""

    pass


class UserListResponse(BaseModel):
    """User list response."""

    id: UUID
    username: str
    email: str
    full_name: str
    status: str
    role: RoleResponse
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Token Schemas
# ============================================================================


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenValidateResponse(BaseModel):
    """Token validation response."""

    is_valid: bool
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[str] = None


# ============================================================================
# User Management Schemas
# ============================================================================


class UserCreateRequest(BaseModel):
    """Admin user creation request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)
    role_id: UUID
    status: str = Field(default="active")


class UserUpdateRequest(BaseModel):
    """User update request."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    status: Optional[str] = None
    role_id: Optional[UUID] = None


# ============================================================================
# Permission Schemas
# ============================================================================


class PermissionResponse(BaseModel):
    """Permission response."""

    resource: str
    action: str
    description: Optional[str] = None


class RoleCreateRequest(BaseModel):
    """Role creation request."""

    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None
    permissions: list = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    """Role update request."""

    description: Optional[str] = None
    permissions: Optional[list] = None

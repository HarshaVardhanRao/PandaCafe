"""
Authentication API endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db.database import get_db
from app.schemas.auth import (
    PasswordChangeRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    TokenRefreshRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user(
    token: str = Depends(lambda: None),
    db: Session = Depends(get_db),
):
    """Dependency to get current user from token."""
    # This would be replaced with proper JWT extraction from headers
    # For now, this is a placeholder
    pass


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **username**: Must be unique and 3-50 characters
    - **email**: Must be valid email and unique
    - **password**: Minimum 8 characters
    - **full_name**: 2-100 characters
    - **role**: User role (default: cashier)
    """
    try:
        result = AuthService.register_user(db, request)
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            expires_in=30 * 60,  # 30 minutes
        )
    except ValueError as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login with username and password.

    Returns JWT access and refresh tokens.
    """
    result = AuthService.authenticate_user(db, request.username, request.password)

    if not result:
        logger.warning(f"Failed login attempt for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=result["refresh_token"],
        expires_in=30 * 60,  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    """
    result = AuthService.refresh_access_token(db, request.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=result["access_token"],
        refresh_token=request.refresh_token,
        expires_in=30 * 60,
    )


@router.post("/change-password")
def change_password(
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
    # current_user would be injected here via dependency
):
    """
    Change user password.

    Requires authentication.
    """
    # This endpoint would need proper authentication middleware
    # For now, it's a skeleton
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication middleware required",
    )


@router.post("/logout")
def logout():
    """
    Logout user.

    Client should discard tokens.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(db: Session = Depends(get_db)):
    """
    Get current user information.

    Requires authentication.
    """
    # This endpoint would need proper authentication middleware
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Authentication middleware required",
    )

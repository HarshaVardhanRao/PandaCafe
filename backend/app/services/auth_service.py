"""
Authentication service for user management and token operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models import User, Role
from app.schemas.auth import (
    UserRegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service."""

    @staticmethod
    def register_user(db: Session, request: UserRegisterRequest) -> dict:
        """
        Register a new user.

        Args:
            db: Database session
            request: Registration request data

        Returns:
            User and tokens

        Raises:
            ValueError: If user already exists
        """
        # Check if user exists
        existing_user = db.query(User).filter(User.username == request.username).first()
        if existing_user:
            raise ValueError(f"Username {request.username} already exists")

        existing_email = db.query(User).filter(User.email == request.email).first()
        if existing_email:
            raise ValueError(f"Email {request.email} already registered")

        # Get role
        role = db.query(Role).filter(Role.name == request.role).first()
        if not role:
            # Default to cashier if role doesn't exist
            role = db.query(Role).filter(Role.name == "cashier").first()
            if not role:
                raise ValueError("Default role 'cashier' not found. Please create roles first.")

        # Create user
        user = User(
            username=request.username,
            email=request.email,
            password_hash=get_password_hash(request.password),
            full_name=request.full_name,
            phone_number=request.phone_number,
            role_id=role.id,
            status="active",
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User {request.username} registered successfully")

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role.name,
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user.username,
                "user_id": str(user.id),
                "username": user.username,
            }
        )

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[dict]:
        """
        Authenticate a user.

        Args:
            db: Database session
            username: Username
            password: Password

        Returns:
            User and tokens, or None if authentication failed
        """
        user = db.query(User).filter(User.username == username).first()

        if not user:
            logger.warning(f"Login attempt with non-existent user: {username}")
            return None

        if not verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {username}")
            return None

        if user.status != "active":
            logger.warning(f"Login attempt with inactive user: {username}")
            return None

        logger.info(f"User {username} logged in successfully")

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role.name,
            }
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user.username,
                "user_id": str(user.id),
                "username": user.username,
            }
        )

        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> Optional[dict]:
        """
        Refresh access token using refresh token.

        Args:
            db: Database session
            refresh_token: Refresh token

        Returns:
            New access token, or None if token is invalid
        """
        token_data = verify_token(refresh_token)

        if not token_data:
            logger.warning("Invalid refresh token")
            return None

        user = db.query(User).filter(User.id == UUID(token_data.user_id)).first()

        if not user or user.status != "active":
            logger.warning(f"Refresh token for inactive/non-existent user: {token_data.user_id}")
            return None

        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": str(user.id),
                "username": user.username,
                "role": user.role.name,
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    @staticmethod
    def change_password(db: Session, user_id: UUID, old_password: str, new_password: str) -> bool:
        """
        Change user password.

        Args:
            db: Database session
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if successful, False otherwise
        """
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return False

        if not verify_password(old_password, user.password_hash):
            logger.warning(f"Failed password change attempt for user: {user_id}")
            return False

        user.password_hash = get_password_hash(new_password)
        db.commit()

        logger.info(f"Password changed for user: {user_id}")
        return True

    @staticmethod
    def get_user(db: Session, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users."""
        return db.query(User).filter(User.deleted_at.is_(None)).offset(skip).limit(limit).all()

    @staticmethod
    def update_user_status(db: Session, user_id: UUID, status: str) -> Optional[User]:
        """Update user status."""
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        user.status = status
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)

        logger.info(f"User status updated: {user_id} -> {status}")
        return user

    @staticmethod
    def soft_delete_user(db: Session, user_id: UUID) -> bool:
        """Soft delete a user."""
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return False

        user.deleted_at = datetime.utcnow()
        db.commit()

        logger.info(f"User soft deleted: {user_id}")
        return True

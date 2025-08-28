from __future__ import annotations

from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.core.config import get_settings
from src.core.db import get_db
from src.core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from src.models.models import User
from src.schemas.schemas import Token, UserCreate, UserRead, MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = get_settings()

# OAuth2 scheme for FastAPI security utilities
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    description="Paste the access token as 'Bearer <token>'",
)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Helper to get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Helper to get user by email."""
    return db.query(User).filter(User.email == email).first()


# PUBLIC_INTERFACE
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password, returning the user if valid."""
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# PUBLIC_INTERFACE
def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency to fetch current user from Authorization Bearer token.

    Raises HTTP 401 if token invalid or user not found.
    """
    payload = decode_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = str(payload["sub"])
    user = get_user_by_username(db, username=username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, and password.",
    responses={
        201: {"description": "User created"},
        400: {"description": "Email or username already exists", "model": MessageResponse},
    },
)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Register endpoint to create a new user.

    Parameters:
      - payload: UserCreate with email, username, password

    Returns:
      - UserRead
    """
    # Check duplicates
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    if get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # Hash password and create
    password_hash = get_password_hash(payload.password)
    user = User(email=payload.email, username=payload.username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate a user and receive a JWT access token. Supports OAuth2 password flow.",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials", "model": MessageResponse},
    },
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Login endpoint to exchange username/password for an access token.

    Body (x-www-form-urlencoded via OAuth2PasswordRequestForm):
      - username: str
      - password: str

    Returns:
      - Token with access_token and token_type
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(subject=user.username, expires_delta=expires)
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/profile",
    response_model=UserRead,
    summary="Get current user profile",
    description="Return the authenticated user's profile based on the provided Bearer token.",
    responses={
        200: {"description": "Profile retrieved"},
        401: {"description": "Not authenticated", "model": MessageResponse},
    },
)
def read_profile(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user profile."""
    return current_user

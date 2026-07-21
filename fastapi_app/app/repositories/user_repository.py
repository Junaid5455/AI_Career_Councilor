"""
app/repositories/user_repository.py
====================================
Database CRUD operations for the User model.

Design rules:
  - Every function receives a SQLAlchemy Session as its first argument.
  - Every function is synchronous (matching the existing sync FastAPI routes).
  - No business logic lives here — only database reads and writes.
  - All functions return ORM model instances or None; callers decide what
    to do with them (raise HTTP errors, build Pydantic responses, etc.).
  - Passwords are NEVER handled here. Hashing belongs in an auth service
    layer that calls set_password() before passing the hash to create_user().

Usage in a FastAPI route:
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.database import get_db
    from app.repositories.user_repository import get_user_by_email

    @router.get("/users/{email}")
    def read_user(email: str, db: Session = Depends(get_db)):
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(status_code=404)
        return user
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_user(
    db: Session,
    *,
    email: str,
    full_name: str,
    hashed_password: Optional[str] = None,
    role: str = "student",
) -> User:
    """
    Inserts a new User row and returns the persisted ORM instance.

    Parameters
    ----------
    db              : active SQLAlchemy session (injected via Depends(get_db))
    email           : unique email address — raises IntegrityError if duplicate
    full_name       : display name
    hashed_password : bcrypt hash from the auth layer; None for OAuth accounts
    role            : 'student' (default) | 'counsellor' | 'admin'

    Raises
    ------
    sqlalchemy.exc.IntegrityError
        If a user with the same email already exists.
        Callers should catch this and raise HTTP 409 Conflict.
    """
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hashed_password,
        role=role,
        # is_active and is_verified use server-side defaults (true / false)
    )
    db.add(user)
    db.commit()
    db.refresh(user)   # populate server-side defaults (id, created_at, etc.)
    return user


# ---------------------------------------------------------------------------
# READ — single user
# ---------------------------------------------------------------------------

def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """
    Fetches a User by primary key UUID.
    Returns None if not found.
    """
    return db.get(User, user_id)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Fetches a User by email address (case-sensitive).
    Returns None if not found.

    Used by the login flow to look up an account before verifying its password.
    """
    stmt = select(User).where(User.email == email)
    return db.scalars(stmt).first()


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def update_user(
    db: Session,
    user: User,
    **fields,
) -> User:
    """
    Applies arbitrary field updates to an existing User row.

    Only keys that correspond to real User columns should be passed.
    Unknown keys are silently ignored to prevent accidental column injection.

    Example
    -------
    update_user(db, user, full_name="Ali Khan", is_verified=True)
    """
    allowed = {
        "full_name", "hashed_password", "role",
        "is_active", "is_verified", "last_login_at",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def set_last_login(db: Session, user: User) -> User:
    """
    Stamps last_login_at with the current database time.
    Called after successful authentication.
    """
    from sqlalchemy import func
    user.last_login_at = db.scalar(func.now())
    db.commit()
    db.refresh(user)
    return user


def verify_user(db: Session, user: User) -> User:
    """
    Marks a user's email as verified.
    Called after the email-verification link is clicked.
    """
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user: User) -> User:
    """
    Soft-deletes a user by setting is_active = False.
    The row is retained for audit purposes; the account can be reactivated.
    """
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_user(db: Session, user: User) -> None:
    """
    Permanently removes a User row from the database.

    All related Sessions and Reports will be cascade-deleted by PostgreSQL
    (ON DELETE CASCADE is set on their user_id foreign keys in models.py).

    Prefer deactivate_user() for soft-deletion in most production scenarios.
    """
    db.delete(user)
    db.commit()


# ---------------------------------------------------------------------------
# EXISTENCE CHECK
# ---------------------------------------------------------------------------

def email_exists(db: Session, email: str) -> bool:
    """
    Returns True if any user row already has this email.
    Cheaper than get_user_by_email() when you only need a boolean.
    Used for pre-validation before attempting an INSERT.
    """
    stmt = select(User.id).where(User.email == email).limit(1)
    return db.scalars(stmt).first() is not None
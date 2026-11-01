"""Verifies Supabase access tokens and maps them to a local User.

Supabase owns sign-up, passwords, magic links and OAuth; the backend only checks
the JWT on each request and keeps a User row keyed by the token's `sub`.
"""

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .settings import settings

ASYMMETRIC_ALGORITHMS = ("RS256", "ES256")

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


@lru_cache
def _jwks_client(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json", cache_keys=True)


def decode_token(token: str) -> dict:
    """Return the verified claims, or raise a 401."""
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        # The key is chosen by our configuration, never by the token, so a token
        # can't downgrade itself to HS256 signed with a public key.
        if alg == "HS256" and settings.supabase_jwt_secret:
            key = settings.supabase_jwt_secret
        elif alg in ASYMMETRIC_ALGORITHMS and settings.jwt_issuer:
            key = _jwks_client(settings.jwt_issuer).get_signing_key_from_jwt(token).key
        else:
            raise _unauthorized(f"Unsupported token algorithm {alg!r}")
        return jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise _unauthorized(f"Invalid token: {e}") from None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise _unauthorized("Not signed in")
    claims = decode_token(credentials.credentials)
    subject, email = claims["sub"], claims.get("email") or ""

    user = db.scalars(select(models.User).where(models.User.auth_subject == subject)).first()
    if user is None:
        user = _claim_placeholder(db, claims) or models.User(
            email=email, display_name=email.split("@")[0] or "Me"
        )
        user.auth_subject = subject
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # first request raced another one from the same user
            db.rollback()
            user = db.scalars(select(models.User).where(models.User.auth_subject == subject)).one()
    elif email and user.email != email:
        user.email = email
        db.commit()
    return user


def _claim_placeholder(db: Session, claims: dict) -> models.User | None:
    """The member row someone added for this email before they signed in, if any.

    Only with a verified email, so nobody can take over a placeholder by signing
    up with an address they don't control.
    """
    email = claims.get("email")
    if not email or (claims.get("user_metadata") or {}).get("email_verified") is not True:
        return None
    return db.scalars(
        select(models.User).where(
            models.User.auth_subject.is_(None), func.lower(models.User.email) == email.lower()
        )
    ).first()

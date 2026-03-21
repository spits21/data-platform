import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Header

from app.itsm_reader import ITSMReader

logger = logging.getLogger(__name__)

SECRET_KEY = "data-catalog-jwt-secret-key"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(email: str, is_admin: bool) -> str:
    payload = {
        "sub": email,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency — extracts and validates the Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return {"email": payload["sub"], "is_admin": payload["is_admin"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def check_asset_access(user: dict, table_name: str) -> None:
    """
    Raises 403 if the user does not have an application role for the given table.
    Admins always pass. Regular users must have a record in
    analytics.application_roles_with_users where:
      - full_name matches their login username, AND
      - the role_name keyword (stripped of '_role' suffix) appears in the table_name
    e.g. 'incidents_role' grants access to any table containing 'incidents'.
    """
    if user["is_admin"]:
        return

    pool = ITSMReader.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT 1 FROM analytics.application_roles_with_users
            WHERE full_name = $1
              AND $2 ILIKE '%' || REPLACE(role_name, '_role', '') || '%'
            LIMIT 1
            """,
            user["email"],
            table_name,
        )

    if not row:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: no application role for '{table_name}'",
        )

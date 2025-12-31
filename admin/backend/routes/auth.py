"""Authentication routes."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from admin.backend.config import admin_settings
from admin.backend.schemas import TelegramAuthData, Token

router = APIRouter(prefix="/auth", tags=["auth"])


def verify_telegram_auth(data: TelegramAuthData) -> bool:
    """Verify Telegram Login Widget data."""
    # Build data check string
    check_data = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
    }
    if data.last_name:
        check_data["last_name"] = data.last_name
    if data.username:
        check_data["username"] = data.username
    if data.photo_url:
        check_data["photo_url"] = data.photo_url

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(check_data.items())
    )

    # Create secret key from bot token
    secret_key = hashlib.sha256(
        admin_settings.telegram_bot_token.encode()
    ).digest()

    # Calculate hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Verify hash
    if not hmac.compare_digest(computed_hash, data.hash):
        return False

    # Check auth_date (not older than 1 day)
    if time.time() - data.auth_date > 86400:
        return False

    return True


def create_access_token(telegram_id: int) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(
        minutes=admin_settings.jwt_expire_minutes
    )
    to_encode = {
        "sub": str(telegram_id),  # JWT 'sub' claim must be a string
        "exp": expire,
    }
    return jwt.encode(
        to_encode,
        admin_settings.jwt_secret,
        algorithm=admin_settings.jwt_algorithm,
    )


@router.post("/telegram", response_model=Token)
async def telegram_login(auth_data: TelegramAuthData) -> Token:
    """Authenticate via Telegram Login Widget."""
    # Dev mode bypass - skip hash verification
    is_dev_login = (
        admin_settings.debug
        and auth_data.hash == "dev_hash"
    )

    # Verify auth data (skip in dev mode)
    if not is_dev_login and not verify_telegram_auth(auth_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication data",
        )

    # Check if user is admin
    if auth_data.id not in admin_settings.admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized as admin",
        )

    # Create token
    access_token = create_access_token(auth_data.id)

    return Token(access_token=access_token)


@router.get("/me")
async def get_me(telegram_id: int = None) -> dict:
    """Get current admin info (for testing)."""
    # In production, use: telegram_id: int = Depends(get_current_admin)
    return {"telegram_id": telegram_id, "is_admin": True}

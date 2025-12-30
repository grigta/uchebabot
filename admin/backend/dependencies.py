"""FastAPI dependencies."""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from admin.backend.config import admin_settings

# Use bot's database module
import sys
from pathlib import Path

# Add parent directory to path for bot imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bot.database import async_session

security = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """Validate JWT token and return admin telegram_id."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            admin_settings.jwt_secret,
            algorithms=[admin_settings.jwt_algorithm],
        )
        telegram_id: int = payload.get("sub")
        if telegram_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Verify admin access
    if telegram_id not in admin_settings.admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized as admin",
        )

    return telegram_id

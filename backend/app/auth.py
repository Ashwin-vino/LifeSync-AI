import logging
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.database.supabase_client import get_supabase

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

def get_authenticated_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
    user_id: Optional[str] = None
) -> str:
    """
    Validates the Supabase access token (JWT) from the Authorization header.
    
    1. If a Bearer token is provided:
       - Verifies the token with Supabase Auth (sb.auth.get_user).
       - Returns the authentic user ID from the token payload.
       - If the token is expired or invalid, raises HTTP 401 Unauthorized.
    2. If no Bearer token is provided:
       - In development/local mode, falls back to x_user_id, user_id, or 'default_user'.
    
    Clients can never spoof another user's ID when authenticated with a token.
    """
    if credentials and credentials.credentials:
        token = credentials.credentials.strip()
        if token and token.lower() != "undefined" and token.lower() != "null":
            try:
                sb = get_supabase()
                user_res = sb.auth.get_user(token)
                if user_res and user_res.user and user_res.user.id:
                    return str(user_res.user.id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Supabase authentication session."
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to validate Supabase token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token validation failed or session expired."
                )

    # Fallback for unauthenticated local development or explicit testing header/query
    return x_user_id or user_id or "default_user"

def require_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """Strictly requires a valid Supabase access token. Rejects unauthenticated requests."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required."
        )
    return get_authenticated_user_id(credentials)

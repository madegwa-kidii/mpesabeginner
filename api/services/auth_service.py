import httpx
import base64
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException
from api.core.config import settings


class TokenCache:
    """Simple in-memory cache for access token"""
    _token: Optional[str] = None
    _expiry: Optional[datetime] = None

    @classmethod
    def set_token(cls, token: str, expires_in: int = 3600):
        """
        Store token with expiry time

        Args:
            token: Access token
            expires_in: Token validity in seconds (default 3600)
        """
        cls._token = token
        cls._expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early

    @classmethod
    def get_token(cls) -> Optional[str]:
        """
        Get cached token if still valid

        Returns:
            Access token if valid, None otherwise
        """
        if cls._token and cls._expiry and datetime.now() < cls._expiry:
            return cls._token
        return None

    @classmethod
    def clear_token(cls):
        """Clear cached token"""
        cls._token = None
        cls._expiry = None


class AuthService:
    """Service for handling M-Pesa authentication"""

    @staticmethod
    async def get_access_token(force_refresh: bool = False) -> str:
        """
        Get M-Pesa access token with caching.

        Args:
            force_refresh: Force token refresh even if cached token exists

        Returns:
            Valid access token

        Raises:
            HTTPException: If token generation fails
        """
        # Return cached token if available and not forcing refresh
        if not force_refresh:
            cached_token = TokenCache.get_token()
            if cached_token:
                return cached_token

        try:
            # Generate Basic Auth header
            auth_string = f"{settings.CONSUMER_KEY}:{settings.CONSUMER_SECRET}"
            encoded = base64.b64encode(auth_string.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/json"
            }

            # Request access token
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    settings.oauth_url,
                    headers=headers,
                    timeout=settings.API_TIMEOUT
                )

                # Check for errors
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    raise HTTPException(
                        status_code=response.status_code,
                        detail={
                            "error": "Failed to generate access token",
                            "error_code": error_data.get("errorCode", "AUTH_ERROR"),
                            "error_message": error_data.get("errorMessage", response.text)
                        }
                    )

                data = response.json()
                access_token = data.get("access_token")

                if not access_token:
                    raise HTTPException(
                        status_code=500,
                        detail="Access token not found in response"
                    )

                # Cache token
                expires_in = int(data.get("expires_in", 3600))
                TokenCache.set_token(access_token, expires_in)

                return access_token

        except HTTPException:
            raise
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Timeout while generating access token"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating access token: {str(e)}"
            )

    @staticmethod
    async def verify_credentials() -> bool:
        """
        Verify M-Pesa credentials by attempting to get access token.

        Returns:
            True if credentials are valid

        Raises:
            HTTPException: If credentials are invalid
        """
        try:
            await AuthService.get_access_token(force_refresh=True)
            return True
        except HTTPException:
            raise

    @staticmethod
    def clear_cache():
        """Clear the access token cache"""
        TokenCache.clear_token()
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from aiohttp import ClientSession, ClientTimeout
from vector.core.db import db


@dataclass
class HandlerResult:
    """Handler execution result"""

    success: bool
    message: str = ""
    data: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def ok(
        cls, message: str = "Success", data: Optional[Any] = None
    ) -> "HandlerResult":
        """Create a successful result"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(
        cls, message: str = "Failed", error: Optional[str] = None
    ) -> "HandlerResult":
        """Create a failed result"""
        return cls(success=False, message=message, error=error)

    def __bool__(self) -> bool:
        """Allow using result in boolean context"""
        return self.success


class BaseProvider(ABC):
    """Base provider class with async database configuration management"""

    def __init__(self) -> None:
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._session: Optional[ClientSession] = None

    @property
    def provider_type(self) -> str:
        """Get provider type automatically (using class name)"""
        return self.__class__.__name__

    async def connect(self) -> None:
        """Create database connection"""
        await db.connect()

    async def close(self) -> None:
        """Close database connection"""
        await db.close()
        await self.close_session()

    @property
    def session(self) -> ClientSession:
        """Get or create HTTP client session"""
        if self._session is None:
            self._session = ClientSession()
        return self._session

    async def close_session(self) -> None:
        """Close HTTP client session"""
        if self._session:
            await self._session.close()
            self._session = None

    async def add_provider(
        self, provider_type: str, name: str, data: Dict[str, Any], status: int = 1
    ) -> None:
        """Add a new provider configuration"""
        await db.add_provider(provider_type, name, data, status)

    async def save_provider(
        self, provider_type: str, name: str, data: Dict[str, Any], status: int = 1
    ) -> None:
        """Add or update provider configuration"""
        await db.save_provider(provider_type, name, data, status)

    async def get_provider(
        self, provider_type: Optional[str] = None, name: Optional[str] = None
    ):
        """Get provider configuration(s)

        Args:
            provider_type: Provider type to filter by (defaults to self.provider_type)
            name: Optional name to filter by specific configuration

        Returns:
            List of tuples containing (name, data_dict)
        """
        provider_type = provider_type or self.provider_type
        return await db.get_provider(provider_type, name)

    async def run(self, **kwargs) -> None:
        """Run the provider with given configuration

        Args:
            **kwargs: Arbitrary keyword arguments passed to handler
        """
        try:
            await self.connect()

            name = kwargs.get("name")
            provider_type = kwargs.get("provider_type", self.provider_type)
            providers = await self.get_provider(provider_type, name)

            if not providers:
                self.logger.warning(f"No providers found for type: {provider_type}")
                return

            for provider_name, provider_data in providers:
                self.logger.info(f"Processing provider: {provider_name}")
                try:
                    result = await self.handler(
                        provider_data=provider_data,
                        provider_name=provider_name,
                        **kwargs,
                    )
                    if result.success:
                        self.logger.info(f"✓ {provider_name}: {result.message}")
                    else:
                        self.logger.error(f"✗ {provider_name}: {result.message}")
                        if result.error:
                            self.logger.error(f"  Error details: {result.error}")
                except Exception as e:
                    self.logger.error(
                        f"✗ {provider_name}: Handler exception - {e}", exc_info=True
                    )
        except Exception as e:
            self.logger.error(f"Error in run: {e}", exc_info=True)
        finally:
            await self.close()

    async def fetch(
        self,
        url: str,
        data: Optional[Dict] = None,
        method: str = "GET",
        **kwargs: Any,
    ):
        """Send HTTP request using aiohttp session

        Args:
            url: URL to request
            data: Optional data for POST requests
            method: HTTP method (GET or POST)
            **kwargs: Additional arguments passed to aiohttp (headers, timeout, etc.)

        Returns:
            aiohttp.ClientResponse object
        """
        # Set default headers
        headers = kwargs.pop("headers", {})
        if "user-agent" not in {k.lower() for k in headers.keys()}:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
            )

        # Set timeout
        timeout = kwargs.pop("timeout", 30)
        if isinstance(timeout, (int, float)):
            timeout = ClientTimeout(total=timeout)

        # Set SSL verification
        kwargs.setdefault("ssl", False)

        # Auto-detect POST method
        if data or kwargs.get("json"):
            method = "POST"

        self.logger.debug(f"{method} {url}")

        return await self.session.request(
            method, url, data=data, headers=headers, timeout=timeout, **kwargs
        )

    @abstractmethod
    async def handler(self, provider_data: Dict[str, Any], **kwargs) -> HandlerResult:
        """Handle provider-specific logic (must be implemented by subclasses)

        Args:
            provider_data: Provider configuration data
            **kwargs: Additional keyword arguments

        Returns:
            HandlerResult: Execution result with success status and message
        """
        pass

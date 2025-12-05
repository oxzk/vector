from vector.core.base import BaseProvider, HandlerResult
from typing import Dict, Any


class Afraid(BaseProvider):
    """Afraid.org FreeDNS login checker"""

    BASE_URL = "https://freedns.afraid.org/zc.php?step=2"

    async def handler(self, provider_data: Dict[str, Any], **kwargs) -> HandlerResult:
        """Check Afraid.org login credentials

        Args:
            provider_data: Configuration data with 'username' and 'password'
            **kwargs: Additional keyword arguments

        Returns:
            HandlerResult: Success if login successful
        """
        username = provider_data.get("username")
        password = provider_data.get("password")

        if not username or not password:
            return HandlerResult.fail(
                "Missing credentials", error="username or password not provided"
            )

        self.logger.info(f"Checking login for user: {username}")

        params = {
            "username": username,
            "password": password,
            "submit": "Login",
            "action": "auth",
        }

        response = await self.fetch(self.BASE_URL, data=params)
        html = await response.text()

        if username in html:
            return HandlerResult.ok(f"Login successful for {username}")
        return HandlerResult.fail(
            f"Login failed for {username}",
            error="Username not found in response page",
        )

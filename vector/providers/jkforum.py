from vector.core.discuz import BaseDiscuzProvider
from vector.core.base import HandlerResult
from typing import Dict, Any


class Jkforum(BaseDiscuzProvider):

    async def handler(self, provider_data: Dict[str, Any], **kwargs) -> HandlerResult:
        """Handle jkforum check-in logic"""
        self.base_url = provider_data.get("base_url")
        cookie = provider_data.get("cookie")

        headers = {"Cookie": cookie}
        user_info = await self.user_info(headers=headers)
        self.logger.info(f"User info: {user_info}")

        result = await self.views(headers=headers)
        self.logger.info(f"Views result: {result}")

        result = await self.sign(headers=headers)
        self.logger.info(f"Sign result: {result}")

        result = await self.poke(headers=headers)
        self.logger.info(f"Poke result: {result}")

        return HandlerResult.ok("Jkforum tasks completed")

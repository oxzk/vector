import os
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

# Provider status constants
STATUS_DISABLED = 0  # 禁用
STATUS_ENABLED = 1  # 启用


class MongoDB:
    """MongoDB connection and operations manager"""

    COLLECTION_NAME: str = "providers"
    STATUS_DISABLED: int = 0  # 禁用
    STATUS_ENABLED: int = 1  # 启用

    def __init__(self) -> None:
        self.db_url: str = os.getenv("MONGO_URL", "")
        if not self.db_url:
            raise ValueError("Environment variable MONGO_URL is not set")
        self._client: Optional[AsyncIOMotorClient] = None
        self.collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self) -> None:
        """Create database connection"""
        if self.collection:
            return
        if self._client is None:
            self._client = AsyncIOMotorClient(self.db_url)

        self.collection = self._client["db0"][self.COLLECTION_NAME]

        await self.collection.create_index(
            [("provider_type", 1), ("name", 1)], unique=True
        )

    async def close(self) -> None:
        """Close database connection"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self.collection = None

    async def add_provider(
        self,
        provider_type: str,
        name: str,
        data: Dict[str, Any],
        status: int = 1,
    ) -> None:
        """Add a new provider configuration

        Args:
            provider_type: Type of provider
            name: Provider name
            data: Provider configuration data
            status: Provider status (0=disabled, 1=enabled, default: STATUS_ENABLED)

        Raises:
            Exception: If provider with same type and name already exists
        """
        await self.collection.insert_one(
            {
                "provider_type": provider_type,
                "name": name,
                "data": data,
                "status": status,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

    async def save_provider(
        self,
        provider_type: str,
        name: str,
        data: Dict[str, Any],
        status: int = 1,
    ) -> None:
        """Add or update provider configuration

        Args:
            provider_type: Type of provider
            name: Provider name
            data: Provider configuration data
            status: Provider status (0=disabled, 1=enabled, default: STATUS_ENABLED)
        """
        await self.collection.update_one(
            {"provider_type": provider_type, "name": name},
            {
                "$set": {
                    "data": data,
                    "status": status,
                    "updated_at": datetime.utcnow(),
                },
                "$setOnInsert": {"created_at": datetime.utcnow()},
            },
            upsert=True,
        )

    async def get_provider(
        self, provider_type: str, name: Optional[str] = None
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """Get provider configuration(s)

        Args:
            provider_type: Provider type to filter by
            name: Optional name to filter by specific configuration

        Returns:
            List of tuples containing (name, data_dict)
        """
        query = {"provider_type": provider_type, "status": self.STATUS_ENABLED}
        if name:
            query["name"] = name

        cursor = self.collection.find(query).sort("name", 1)
        results = []
        async for doc in cursor:
            results.append((doc["name"], doc["data"]))

        return results


# Global database instance
db = MongoDB()

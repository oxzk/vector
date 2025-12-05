import asyncio
import asyncpg
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from vector.core.base import BaseProvider, HandlerResult
from typing import Dict, Any


class DatabaseTester(BaseProvider):
    """Database connection tester for Redis, MongoDB, and PostgreSQL"""

    async def _test_redis(self, name: str, uri: str) -> None:
        """Test Redis connection

        Args:
            name: Configuration name
            uri: Redis connection URI
        """
        try:
            client = redis.from_url(uri, decode_responses=True)
            await client.ping()

            # Write test key
            test_key = f"test:connection:{name}"
            await client.set(test_key, "test_value", ex=60)
            value = await client.get(test_key)

            # Delete test key
            await client.delete(test_key)
            await client.close()

            self.logger.info(
                f"Redis [{name}]: Connection successful (wrote and deleted test key)"
            )
        except Exception as e:
            self.logger.error(f"Redis [{name}]: Connection failed - {e}")

    async def _test_mongodb(self, name: str, uri: str) -> None:
        """Test MongoDB connection

        Args:
            name: Configuration name
            uri: MongoDB connection URI
        """
        try:
            client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
            await client.admin.command("ping")
            database_names = await client.list_database_names()
            client.close()
            self.logger.info(
                f"MongoDB [{name}]: Connection successful, databases: {database_names}"
            )
        except Exception as e:
            self.logger.error(f"MongoDB [{name}]: Connection failed - {e}")

    async def _test_postgresql(self, name: str, uri: str) -> None:
        """Test PostgreSQL connection

        Args:
            name: Configuration name
            uri: PostgreSQL connection URI
        """
        try:
            conn = await asyncpg.connect(uri)

            # List all table names
            tables = await conn.fetch(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
            table_names = [row["table_name"] for row in tables]

            await conn.close()

            self.logger.info(
                f"PostgreSQL [{name}]: Connection successful, tables: {table_names}"
            )
        except Exception as e:
            self.logger.error(f"PostgreSQL [{name}]: Connection failed - {e}")

    async def handler(self, provider_data: Dict[str, Any], **kwargs) -> HandlerResult:
        """Run all database connection tests

        Tests Redis, MongoDB, and PostgreSQL connections from stored configurations.
        """
        # Map database types to their test methods
        test_methods = {
            "redis": self._test_redis,
            "mongo": self._test_mongodb,
            "postgre": self._test_postgresql,
        }

        provider_name = kwargs.get("provider_name", "Unknown")
        self.logger.info("=" * 60)
        self.logger.info(f"Testing {provider_name} connections...")
        try:
            for db_name, db_url in provider_data.items():
                test_method = test_methods.get(provider_name)
                if test_method:
                    await test_method(db_name, db_url)
                else:
                    self.logger.warning(f"Unknown database type: {provider_name}")

            self.logger.info("=" * 60)
            return HandlerResult.ok("All database tests completed")

        except Exception as e:
            self.logger.error(f"Error during database tests: {e}", exc_info=True)
            return HandlerResult.fail("Database tests failed", error=str(e))


if __name__ == "__main__":
    test = DatabaseTester()
    asyncio.run(test.run())

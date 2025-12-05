import argparse
import asyncio
import importlib
import inspect
import sys
from vector.core.base import BaseProvider
from vector import logger


def create_provider_instance(provider_name: str) -> BaseProvider:
    """Create provider instance dynamically from module name."""
    module = importlib.import_module(f"vector.providers.{provider_name}")
    class_name = "".join(word.capitalize() for word in provider_name.split("_"))
    if hasattr(module, class_name):
        return getattr(module, class_name)()

    for _, provider_class in inspect.getmembers(module, inspect.isclass):
        # Only load spiders defined in this module (not imported ones)
        if (
            issubclass(provider_class, BaseProvider)
            and provider_class is not BaseProvider
            and provider_class.__module__ == module.__name__
        ):
            try:
                return provider_class()
            except Exception as e:
                logger.error(
                    f"Failed to instantiate provider {provider_class.__name__}: {e}"
                )
    raise ImportError(f"No valid provider class found in module {provider_name}")


async def run_provider(provider_name: str, username: str = None):
    """Run a single provider."""
    logger.info(f"Starting: {provider_name}")
    instance = create_provider_instance(provider_name)
    await instance.run(name=username, provider_type=provider_name)
    logger.info(f"✓ {provider_name} completed")


def main():
    parser = argparse.ArgumentParser(description="Nova - Provider Task Runner")
    parser.add_argument("provider", help="Provider name to run")
    parser.add_argument("-u", "--username", help="Username for provider")
    args = parser.parse_args()

    try:
        asyncio.run(run_provider(args.provider, args.username))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

import asyncio
import json
from vector.core import db, STATUS_ENABLED, STATUS_DISABLED


async def main():
    """Interactive script to add provider configuration"""
    print("=== Add Provider Configuration ===\n")

    # Get provider type
    provider_type = input("Provider Type (e.g., JkforumProvider): ").strip()
    if not provider_type:
        print("Error: Provider type cannot be empty")
        return

    # Get provider name
    name = input("Provider Name (e.g., config1): ").strip()
    if not name:
        print("Error: Provider name cannot be empty")
        return

    # Get provider data
    print(
        '\nEnter provider data as JSON (e.g., {"url": "https://example.com", "token": "xxx"}):'
    )
    data_str = input("Data: ").strip()
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format - {e}")
        return

    # Get status
    status_input = input("\nStatus (0=disabled, 1=enabled, default=1): ").strip()
    if status_input == "0":
        status = STATUS_DISABLED
    else:
        status = STATUS_ENABLED

    # Confirm
    print("\n--- Configuration Summary ---")
    print(f"Provider Type: {provider_type}")
    print(f"Name: {name}")
    print(f"Data: {json.dumps(data, indent=2)}")
    print(f"Status: {'Enabled' if status == STATUS_ENABLED else 'Disabled'}")
    print("-----------------------------")

    confirm = input("\nAdd this provider? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    # Add provider
    try:
        await db.connect()
        await db.add_provider(provider_type, name, data, status)
        print(f"\n✓ Provider '{name}' added successfully!")
    except Exception as e:
        print(f"\n✗ Error adding provider: {e}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())

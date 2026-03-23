"""Allow running dan-computer-use-mcp as a module."""
from dan_computer_use_mcp.server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
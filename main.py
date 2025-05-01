import os
import sys
import asyncio

from logger import logger
from utils.channel_monitor import ChannelMonitor


async def main():
    try:
        # Get API credentials from environment variables
        api_id = os.getenv("API_ID")
        api_hash = os.getenv("API_HASH")

        if not api_id or not api_hash:
            logger.error("API_ID and API_HASH must be set in the .env file")
            sys.exit(1)

        # Convert API_ID to integer
        try:
            api_id = int(api_id)
        except ValueError:
            logger.error("API_ID must be an integer")
            sys.exit(1)

        logger.info("Initializing channel monitor")
        monitor = ChannelMonitor()

        # Initialize and run the monitor
        await monitor.initialize(api_id, api_hash)

        # Set up graceful shutdown
        try:
            await monitor.run()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            await monitor.stop()

    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

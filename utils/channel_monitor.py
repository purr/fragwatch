import os
import re

from telethon import TelegramClient, events

from config import SEND_CHANNEL_ID, RECEIVE_CHANNEL_ID
from logger import logger

from .message_parser import MessageParser
from .fragment_service import get_bidder_info, check_beneficiary_address
from .telegram_service import TelegramService
from .dictionary_service import is_word_in_dictionary


class ChannelMonitor:
    def __init__(self):
        self.api_id = None
        self.api_hash = None
        self.client = None
        self.channel_username = None
        self.channel_title = None

    async def initialize(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        os.makedirs("sessions", exist_ok=True)
        self.client = TelegramClient("sessions/user_session", api_id, api_hash)

        # Start the client - will prompt for phone/code if needed
        logger.info("Starting Telethon client")
        await self.client.start()

        # Check if we're logged in
        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            logger.info(f"Logged in as: {me.first_name} (@{me.username})")
        else:
            logger.error("Client not authorized after start")
            raise Exception("Authentication failed")

        await self.check_channels_access()

        # Get info about the send channel
        await self.get_channel_info()

        self.register_handlers()

    async def get_channel_info(self):
        """Get information about the send channel for displaying in messages"""
        try:
            # Try to get the entity for the send channel
            channel = await self.client.get_entity(SEND_CHANNEL_ID)

            if hasattr(channel, "username") and channel.username:
                self.channel_username = channel.username
                logger.info(f"Channel username: @{self.channel_username}")
            else:
                logger.warning("Channel does not have a username")

            if hasattr(channel, "title"):
                self.channel_title = channel.title
                logger.info(f"Channel title: {self.channel_title}")
            else:
                logger.warning("Channel does not have a title")

            # Make channel info available to the TelegramService
            TelegramService.set_channel_info(self.channel_username, self.channel_title)

        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            # Don't raise an exception here - this isn't critical for operation

    async def check_channels_access(self):
        try:
            receive_channel = await self.client.get_entity(RECEIVE_CHANNEL_ID)
            logger.info(
                f"Successfully accessed receive channel: {receive_channel.title}"
            )

            # Check if we can read messages
            async for message in self.client.iter_messages(receive_channel, limit=1):
                logger.info(f"Successfully read messages from receive channel")
                break
        except Exception as e:
            logger.error(f"Failed to access receive channel: {e}")
            raise

        try:
            # We don't need to check send permissions since we're using the bot API
            logger.info(f"Using bot API to send messages to channel {SEND_CHANNEL_ID}")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            raise

    async def enrich_message_data(self, message_data):
        """Enrich message data with additional information from Fragment"""
        if not message_data:
            return message_data

        try:
            # Parse the price value to determine if we should check for beneficiary
            amount_value = 0
            if message_data.price:
                # Extract numeric value from price string (e.g., "534 TON" -> 534)
                amount_str = (
                    message_data.price.split()[0]
                    .replace(",", "")
                    .strip()
                    .replace("`", "")
                ).split()[0]
                try:
                    amount_value = float(amount_str)
                    logger.info(f"Parsed amount value: {amount_value} TON")
                except ValueError:
                    logger.warning(
                        f"Could not parse price value from '{message_data.price}'"
                    )

            # Check if username (without @) consists only of letters for dictionary lookup
            if message_data.username:
                username_without_at = message_data.username.strip("@")
                if re.match(r"^[a-zA-Z]+$", username_without_at):
                    standard_dict, urban_dict = await is_word_in_dictionary(
                        username_without_at
                    )
                    message_data.in_standard_dict = standard_dict
                    message_data.in_urban_dict = urban_dict
                    logger.info(
                        f"Dictionary results for '{username_without_at}': standard={standard_dict}, urban={urban_dict}"
                    )

            if message_data.username and amount_value >= 104:
                logger.info(
                    f"Checking beneficiary for username: @{message_data.username} (Price: {amount_value} TON)"
                )

                identifier = None

                # Use either username or phone number as identifier
                if message_data.username:
                    identifier = message_data.username.strip("@")
                    logger.info(
                        f"Checking beneficiary for username: @{identifier} (Price: {amount_value} TON)"
                    )

                if identifier:
                    is_user_mint, beneficiary = await check_beneficiary_address(
                        identifier
                    )

                    message_data.user_mint = is_user_mint
                    message_data.beneficiary_address = beneficiary

                    if is_user_mint:
                        logger.info(
                            f"Mint for {identifier} is a user mint with beneficiary: {beneficiary}"
                        )
                    else:
                        logger.info(f"Mint for {identifier} is a Fragment mint")

            # For messages with bidder URL, get short name and possible Telegram URL
            if message_data.bidder_url:
                short_name, telegram_url = await get_bidder_info(
                    message_data.bidder_url
                )

                if short_name:
                    message_data.bidder_short_name = short_name
                    logger.info(f"Found bidder short name: {short_name}")

                if telegram_url:
                    message_data.telegram_url = telegram_url
                    logger.info(f"Found Telegram URL: {telegram_url}")
            else:
                logger.info("No bidder URL found")

            logger.debug(f"Enriched message data: {message_data}")
            return message_data

        except Exception as e:
            logger.error(f"Error enriching message data: {e}")
            return message_data

    def register_handlers(self):
        @self.client.on(events.NewMessage(chats=RECEIVE_CHANNEL_ID))
        async def on_new_message(event):
            try:
                message = event.message
                logger.info(f"New message received from channel {RECEIVE_CHANNEL_ID}")

                # Extract inline buttons from the message
                buttons = []
                if message.reply_markup:
                    for row in message.reply_markup.rows:
                        button_row = []
                        for button in row.buttons:
                            button_data = {"text": button.text}
                            if hasattr(button, "url") and button.url:
                                button_data["url"] = button.url
                            button_row.append(button_data)
                        if button_row:
                            buttons.append(button_row)

                # Parse message text and buttons
                message_data = MessageParser.extract_message_data(message.text, buttons)

                if not message_data:
                    logger.warning("Failed to extract message data")
                    return

                # Enrich message data with additional info from Fragment
                enriched_data = await self.enrich_message_data(message_data)

                # Forward to send channel using API
                success = await TelegramService.send_message(enriched_data)
                if success:
                    logger.info(f"Message processed and forwarded successfully")
                else:
                    logger.error("Failed to forward message")

            except Exception as e:
                logger.error(f"Error handling new message: {e}")

    async def run(self):
        logger.info("Starting channel monitor...")
        await self.client.run_until_disconnected()

    async def stop(self):
        logger.info("Stopping channel monitor...")
        await self.client.disconnect()

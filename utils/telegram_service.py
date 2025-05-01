import re
import json

import aiohttp

from config import SEND_CHANNEL_ID, SEND_MESSAGE_URL
from logger import logger

from .message_parser import MessageData


class TelegramService:
    # Class variables to store channel information
    channel_username = None
    channel_title = None

    @staticmethod
    def set_channel_info(username, title):
        """Set channel information for use in messages"""
        TelegramService.channel_username = username
        TelegramService.channel_title = title
        logger.info(f"Channel info set: @{username} - {title}")

    @staticmethod
    def escape_markdown(text):
        """
        Escape special characters for MarkdownV2 format
        https://core.telegram.org/bots/api#markdownv2-style
        """
        escape_chars = r"_[]()~>#+-=|{}.!"
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)

    @staticmethod
    async def send_message(message_data: MessageData) -> bool:
        try:
            # Use original formatted text for the first line
            emoji = message_data.original_format.split()[1]
            action = message_data.original_format.split()[0].replace("_", "")

            # For non-special elements, we need to escape markdown characters
            price = TelegramService.escape_markdown(message_data.price)

            message_text = f"*{emoji} {action}*"
            in_dictionary = False

            if message_data.username:
                if message_data.in_standard_dict or message_data.in_urban_dict:
                    in_dictionary = True

                username = TelegramService.escape_markdown(message_data.username)
                message_text += f" {username} {"🔍" if in_dictionary else ""}\n"

            elif message_data.phone_number:
                phone_number = "+" + TelegramService.escape_markdown(
                    message_data.phone_number
                )
                message_text += f" [{phone_number}](t.me/{phone_number})\n"

            message_text += f"💎 Amount: {price}\n"

            if in_dictionary:
                message_text += f"📚 `{message_data.username.replace('@', '')}` found in dictionaries\n"

            if TelegramService.channel_username and TelegramService.channel_title:
                button_text = TelegramService.channel_title
                message_text += f"👁️‍🗨️ [{button_text}](https://t.me/{TelegramService.channel_username})"

            # Build buttons
            inline_keyboard = []

            # Add Fragment button
            if message_data.fragment_url:
                inline_keyboard.append(
                    [{"text": "🔗 Open in Fragment", "url": message_data.fragment_url}]
                )

            # Add mint type button with beneficiary link if available
            if message_data.beneficiary_address:
                # Set button text based on user_mint flag
                button_text = (
                    "👤 User Auction" if message_data.user_mint else "🏛️ Fragment Mint"
                )
                beneficiary_url = (
                    f"https://tonviewer.com/{message_data.beneficiary_address}"
                )

                # Add as a separate button row
                inline_keyboard.append([{"text": button_text, "url": beneficiary_url}])

            # Add bidder button with custom name if available
            if message_data.bidder_url:
                # Default button properties
                button_prefix = "🥇 "
                button_text = button_prefix + "Bidder"
                button_url = message_data.bidder_url

                # Customize button based on bidder short name if available
                if message_data.bidder_short_name:
                    short_name = message_data.bidder_short_name
                    button_text = button_prefix + short_name

                    # Special handling for Telegram usernames
                    if ".t.me" in short_name and message_data.telegram_url:
                        tg_username = short_name.replace(".t.me", "")
                        wallet_button = {"text": button_text, "url": button_url}
                        telegram_button = {
                            "text": f"📲 @{tg_username}",
                            "url": message_data.telegram_url,
                        }
                        inline_keyboard.append([wallet_button, telegram_button])
                    else:
                        # Standard button for all other cases (.ton, truncated addresses, etc.)
                        inline_keyboard.append(
                            [{"text": button_text, "url": button_url}]
                        )
                else:
                    # Default bidder button
                    inline_keyboard.append([{"text": button_text, "url": button_url}])

            # Try with "Markdown" parse mode first (simpler and more forgiving)
            payload = {
                "chat_id": SEND_CHANNEL_ID,
                "text": message_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }

            if inline_keyboard:
                payload["reply_markup"] = json.dumps(
                    {"inline_keyboard": inline_keyboard}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(SEND_MESSAGE_URL, data=payload) as response:
                    if response.status == 200:
                        logger.info(
                            f"Message sent successfully to channel {SEND_CHANNEL_ID}"
                        )
                        return True
                    else:
                        response_text = await response.text()
                        logger.warning(
                            f"Failed to send with Markdown: {response.status} - {response_text}. Trying with HTML."
                        )

                        # If Markdown fails, try with HTML (more compatible with some bots)
                        payload["parse_mode"] = "HTML"
                        async with session.post(
                            SEND_MESSAGE_URL, data=payload
                        ) as html_response:
                            if html_response.status == 200:
                                logger.info(
                                    f"Message sent successfully with HTML to channel {SEND_CHANNEL_ID}"
                                )
                                return True
                            else:
                                html_text = await html_response.text()
                                logger.error(
                                    f"Failed to send with HTML: {html_response.status} - {html_text}"
                                )

                                # Last resort: try without parse_mode
                                del payload["parse_mode"]
                                async with session.post(
                                    SEND_MESSAGE_URL, data=payload
                                ) as plain_response:
                                    if plain_response.status == 200:
                                        logger.info(
                                            f"Message sent successfully without formatting to channel {SEND_CHANNEL_ID}"
                                        )
                                        return True
                                    else:
                                        plain_text = await plain_response.text()
                                        logger.error(
                                            f"Failed to send without formatting: {plain_response.status} - {plain_text}"
                                        )
                                        return False

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

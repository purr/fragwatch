from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from logger import logger


@dataclass
class MessageData:
    message_type: str  # "Mint" or "Bid"
    original_format: str  # The original formatted text for the message type
    price: str
    username: Optional[str] = None  # Username for username-based messages
    phone_number: Optional[str] = None  # Phone number for number-based messages
    bidder_url: Optional[str] = None
    fragment_url: Optional[str] = None
    user_mint: bool = False  # True if it's a user mint, False if it's a Fragment mint
    beneficiary_address: Optional[str] = None  # Beneficiary address for user mints
    bidder_short_name: Optional[str] = (
        None  # Short name of the bidder (e.g., .ton or .t.me address)
    )
    telegram_url: Optional[str] = (
        None  # URL to Telegram profile if bidder is a .t.me address
    )
    in_standard_dict: bool = False  # True if username is found in standard dictionary
    in_urban_dict: bool = False  # True if username is found in urban dictionary


class MessageParser:
    @staticmethod
    def is_valid_username(username: str) -> bool:
        """
        Check if a username meets the criteria for processing.
        Rejects usernames with:
        1. More than 1 underscore
        2. More than 1 number
        3. Combination of 1 number and 1 underscore
        """
        if not username:
            return False

        # Count underscores and digits
        underscore_count = username.count("_")
        digit_count = sum(c.isdigit() for c in username)

        # Check conditions
        if underscore_count > 1:
            logger.info(
                f"Skipping username '{username}' - contains {underscore_count} underscores (>1)"
            )
            return False

        if digit_count > 1:
            logger.info(
                f"Skipping username '{username}' - contains {digit_count} digits (>1)"
            )
            return False

        if underscore_count >= 1 and digit_count >= 1:
            logger.info(
                f"Skipping username '{username}' - contains both underscore and digit"
            )
            return False

        return True

    @staticmethod
    def extract_message_data(
        message_text: str, buttons: List[Dict[str, Any]]
    ) -> Optional[MessageData]:
        try:
            lines = message_text.strip().split("\n")

            # Log the first line for debugging
            if lines:
                logger.debug(f"First line of message: {lines[0]}")

            # Determine message type by checking if "Mint" or "Bid" appears in the first line
            # This handles cases with formatting like **__Mint__**
            first_line = lines[0].lower() if lines else ""
            original_first_line = lines[0] if lines else ""

            if "mint" in first_line:
                message_type = "Mint"
            elif "bid" in first_line:
                message_type = "Bid"
            else:
                message_type = None

            if not message_type:
                logger.warning(f"Unknown message type: {lines[0]}")
                return None

            # Check if message has Username or Number
            username = None
            phone_number = None

            # Extract username if present
            username_line = next(
                (line for line in lines if line.startswith("Username:")), None
            )
            if username_line:
                username = username_line.split()[1].replace("*", "")
                logger.debug(f"Found username: {username}")

                # Check if username meets the criteria for processing
                username_without_at = username.strip("@")
                if not MessageParser.is_valid_username(username_without_at):
                    logger.info(
                        f"Username '{username}' does not meet processing criteria, ignoring message"
                    )
                    return None

            # Extract phone number if present
            number_line = next(
                (line for line in lines if line.startswith("Number:")), None
            )
            if number_line:
                phone_number = (
                    number_line.replace("Number:", "")
                    .strip()
                    .replace("*", "")
                    .replace(" ", "")
                )
                logger.debug(f"Found phone number: {phone_number}")

            # Must have either username or number
            if not username and not phone_number:
                logger.warning("Neither Username nor Number found in message")
                return None

            # Extract price
            price_line = next(
                (line for line in lines if line.startswith("Price:")), None
            )
            if not price_line:
                logger.warning("Price not found in message")
                return None

            price = price_line.replace("Price:", "").strip()

            # Extract URLs from buttons
            bidder_url = None
            fragment_url = None

            for row in buttons:
                for button in row:
                    if "url" in button and "text" in button:
                        if button["text"] == "Bidder":
                            bidder_url = button["url"]
                        elif button["text"] == "Fragment":
                            fragment_url = button["url"]

            return MessageData(
                message_type=message_type,
                original_format=original_first_line,
                username=username,
                phone_number=phone_number,
                price=price,
                bidder_url=bidder_url,
                fragment_url=fragment_url,
                user_mint=False,  # Default to Fragment mint, will be updated by the enrichment process
                beneficiary_address=None,
                bidder_short_name=None,
                telegram_url=None,
            )

        except Exception as e:
            logger.error(f"Error parsing message: {e}")
            return None

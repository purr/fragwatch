import asyncio
from typing import Tuple, Optional

import aiohttp
from bs4 import BeautifulSoup

from logger import logger

# Fragment mint address - all official Fragment mints have this beneficiary
FRAGMENT_MINT_ADDRESS = (
    "0:408da3b28b6c065a593e10391269baaa9c5f8caebc0c69d9f0aabbab2a99256b"
)


async def fetch_fragment_url(url: str) -> Optional[str]:
    """
    Fetch content from Fragment website

    Args:
        url: The URL to fetch

    Returns:
        HTML content as string or None if request failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=False) as response:
                if response.status == 200:
                    return await response.text()

                logger.warning(f"Failed to fetch {url}, status code: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


async def get_bidder_info(bidder_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract bidder short name and possible telegram username from bidder URL

    Args:
        bidder_url: URL to the bidder page

    Returns:
        Tuple of (short_name, telegram_url) where either might be None
    """
    if not bidder_url:
        return None, None

    try:
        logger.debug(f"Fetching bidder info from {bidder_url}")
        html_content = await fetch_fragment_url(bidder_url)
        if not html_content:
            return None, None

        soup = BeautifulSoup(html_content, "html.parser")

        # Try to find the name in the h1 element (new Fragment UI)
        name_element = soup.select_one("h1.bdtytpm.nygz236.t1g1t0q6")
        if name_element:
            short_name = name_element.text.strip()
            logger.debug(f"Found short name in h1 element: {short_name}")

            # Check for .t.me address format
            if ".t.me" in short_name:
                tg_username = short_name.replace(".t.me", "")
                telegram_url = f"https://t.me/{tg_username}"
                return short_name, telegram_url

            # Check for .ton address format
            if ".ton" in short_name:
                return short_name, None

            # Check if name contains a period - if not, treat it as a wallet address
            if "." not in short_name and len(short_name) > 10:
                # Format as wallet address (first 5 chars + ... + last 5 chars)
                formatted_address = f"{short_name[:5]}...{short_name[-5:]}"
                return formatted_address, None

            # Regular name (like "Pavel Durov")
            return short_name, None

        # Fall back to the old wallet display method
        wallet_display = soup.select_one(".wallet-display")
        if wallet_display:
            # First check for short name
            short_name_element = wallet_display.select_one("span.short")
            if short_name_element:
                short_name = short_name_element.text.strip()

                # Check if it's a .t.me address
                if ".t.me" in short_name:
                    tg_username = short_name.replace(".t.me", "")
                    telegram_url = f"https://t.me/{tg_username}"
                    return short_name, telegram_url

                # Check if name contains a period - if not, treat it as a wallet address
                if "." not in short_name and len(short_name) > 10:
                    # Format as wallet address (first 5 chars + ... + last 5 chars)
                    formatted_address = f"{short_name[:5]}...{short_name[-5:]}"
                    return formatted_address, None

                return short_name, None

            # If no short name, fall back to wallet address
            head_element = wallet_display.select_one("span.head")
            tail_element = wallet_display.select_one("span.tail")

            if head_element and tail_element:
                head = head_element.text.strip()
                tail = tail_element.text.strip()

                short_name = f"{head[:5]}...{tail[-5:]}"
                return short_name, None

        # Last resort: Extract wallet address from the URL
        if "/address/" in bidder_url:
            wallet_address = bidder_url.split("/address/")[-1]
            short_name = f"{wallet_address[:5]}...{wallet_address[-5:]}"
            return short_name, None

        return None, None
    except Exception as e:
        logger.error(f"Error getting bidder info from {bidder_url}: {e}")
        return None, None


async def check_beneficiary_address(identifier: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a username/number mint is from Fragment or from a user

    Args:
        identifier: The username or phone number to check

    Returns:
        Tuple of (is_user_mint, beneficiary_address) where beneficiary_address might be None
    """
    try:
        # For usernames, use the DNS API
        if not identifier.replace(" ", "").isdigit():
            # This is a username
            username = identifier.replace(" ", "").replace("@", "").replace("*", "")
            dns_url = f"https://tonapi.io/v2/dns/{username}.t.me"

            logger.info(f"Fetching DNS info for username from {dns_url}")

            async with aiohttp.ClientSession() as session:
                # First attempt
                async with session.get(dns_url) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to get DNS info from TONAPI: {response.status}, waiting 20 seconds to retry"
                        )
                        # Wait 20 seconds before retrying
                        await asyncio.sleep(20)

                        # Second attempt
                        async with session.get(dns_url) as retry_response:
                            if retry_response.status != 200:
                                logger.warning(
                                    f"Retry failed to get DNS info from TONAPI: {retry_response.status}, giving up"
                                )
                                return False, None

                            dns_data = await retry_response.json()
                    else:
                        dns_data = await response.json()

                    # Extract address from the response
                    if "item" in dns_data and "address" in dns_data["item"]:
                        address = dns_data["item"]["address"]
                        return await _check_beneficiary_from_address(address)
        else:
            # This is a phone number, first clean it
            clean_number = (
                identifier.replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
            )

            # For phone numbers, use the Fragment API directly
            fragment_url = f"https://fragment.com/number/{clean_number}"
            logger.info(f"Fetching Fragment page for number: {fragment_url}")

            html_content = await fetch_fragment_url(fragment_url)
            if not html_content:
                return False, None

            # Try to find owner info in HTML
            # For now, assume it's a Fragment mint since we don't have a reliable way
            # to check beneficiary for numbers yet
            return False, None

        return False, None
    except Exception as e:
        logger.error(f"Error checking beneficiary for {identifier}: {e}")
        return False, None


async def _check_beneficiary_from_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Helper function to check beneficiary from a TON address

    Args:
        address: The TON address to check

    Returns:
        Tuple of (is_user_mint, beneficiary_address)
    """
    try:
        # Use address to get auction config
        auction_url = f"https://tonapi.io/v2/blockchain/accounts/{address}/methods/get_telemint_auction_config"

        async with aiohttp.ClientSession() as session:
            async with session.get(auction_url) as auction_response:
                if auction_response.status != 200:
                    logger.warning(
                        f"Failed to get auction config from TONAPI: {auction_response.status}"
                    )
                    return False, None

                auction_data = await auction_response.json()

                # Check for beneficiary address
                if (
                    "decoded" in auction_data
                    and "beneficiar" in auction_data["decoded"]
                ):
                    beneficiary = auction_data["decoded"]["beneficiar"]

                    # Check if it's a Fragment mint
                    is_user_mint = beneficiary != FRAGMENT_MINT_ADDRESS

                    return is_user_mint, beneficiary

        return False, None
    except Exception as e:
        logger.error(f"Error checking beneficiary from address: {e}")
        return False, None

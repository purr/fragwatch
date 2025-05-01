import re

import aiohttp

from logger import logger


async def is_word_in_dictionary(word: str) -> tuple[bool, bool]:
    """
    Check if a word exists in dictionary APIs.

    Args:
        word: The word to check

    Returns:
        tuple: (is_in_standard_dict, is_in_urban_dict)
    """
    if not word or not re.match(r"^[a-zA-Z]+$", word):
        logger.debug(
            f"Word '{word}' contains non-letter characters or is empty, skipping dictionary check"
        )
        return False, False

    word = word.lower()
    standard_dict_result = await check_standard_dictionary(word)

    # Only check urban dictionary if standard dictionary doesn't have results
    if not standard_dict_result:
        urban_dict_result = await check_urban_dictionary(word)
    else:
        urban_dict_result = False

    return standard_dict_result, urban_dict_result


async def check_standard_dictionary(word: str) -> bool:
    """Check if word exists in Free Dictionary API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            async with session.get(url) as response:
                if response.status == 200:
                    logger.info(f"Word '{word}' found in standard dictionary")
                    return True
                else:
                    logger.warning(f"Word '{word}' not found in standard dictionary")
                    return False
    except Exception as e:
        logger.error(f"Error checking standard dictionary: {e}")
        return False


async def check_urban_dictionary(word: str) -> bool:
    """Check if word exists in Urban Dictionary API"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.urbandictionary.com/v0/define?term={word}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if there are any definitions
                    if data and "list" in data and len(data["list"]) > 0:
                        logger.info(f"Word '{word}' found in Urban Dictionary")
                        return True
                logger.warning(f"Word '{word}' not found in Urban Dictionary")
                return False
    except Exception as e:
        logger.error(f"Error checking Urban Dictionary: {e}")
        return False

# t.me/FragWatch

ꕤ Monitors Fragment Bids and Mints  
𖦹 Uses data from @Fragment_Monitor  
✎ Easy access and cleaner messages

## Overview

FragWatch is a Telegram bot that monitors and enhances Fragment notifications. It takes messages from the Fragment Monitor channel, enriches them with additional information, and delivers them in a cleaner, more user-friendly format.

## Features

- **Message Monitoring**: Listens to Fragment Monitor channel for bids and mints
- **Data Enrichment**: Enhances messages with:
  - Bidder information (including wallet short names)
  - Telegram username links for .t.me addresses
  - User mint vs Fragment mint differentiation
  - Dictionary checks for usernames
- **Clean Formatting**: Delivers information in a concise, well-formatted way
- **Interactive Buttons**: Provides convenient links to:
  - Fragment auction pages
  - Bidder profiles
  - TON blockchain explorer for addresses

## How It Works

1. Monitors the Fragment Monitor channel for new messages
2. Parses the message content to extract key details
3. Enriches the data with additional information from Fragment and TON APIs
4. Reformats the messages for better readability
5. Forwards the enhanced messages to a specified channel

## Technical Stack

- **Telethon**: For Telegram client functionality
- **aiohttp**: For asynchronous HTTP requests to APIs
- **BeautifulSoup4**: For parsing HTML from Fragment website
- **Loguru**: For structured logging
- **python-dotenv**: For environment variable management

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   API_ID=your_telegram_api_id
   API_HASH=your_telegram_api_hash
   BOT_TOKEN=your_bot_token
   ```
4. Run the bot:
   ```
   python main.py
   ```

## Configuration

Key settings can be modified in `config.py`:

- `RECEIVE_CHANNEL_ID`: The channel ID to monitor for Fragment notifications
- `SEND_CHANNEL_ID`: The channel ID where enhanced messages will be sent

## Special Features

- **Username Analysis**: Identifies usernames found in standard or urban dictionaries
- **Beneficiary Detection**: Identifies if a username mint is from Fragment or a user auction
- **Bidder Recognition**: Shows readable wallet names instead of raw addresses
- **Username Filtering**: Focuses on high-quality usernames by filtering out:
  - Usernames with more than 1 underscore
  - Usernames with more than 1 digit
  - Usernames that contain both an underscore and a digit

## License

This project is for educational purposes.

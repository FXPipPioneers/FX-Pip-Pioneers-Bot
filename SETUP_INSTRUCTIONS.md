# Discord Trading Bot Setup Instructions

## Quick Setup for Render.com Deployment

### 1. Environment Variables (Required)
Set these in your Render dashboard under Environment Variables:

```
DISCORD_TOKEN_PART1=first_half_of_your_bot_token
DISCORD_TOKEN_PART2=second_half_of_your_bot_token
DISCORD_CLIENT_ID_PART1=first_half_of_your_client_id
DISCORD_CLIENT_ID_PART2=second_half_of_your_client_id
METAAPI_TOKEN=your_metaapi_token
MT5_ACCOUNT_ID=your_mt5_account_id
```

### 2. Render Configuration
- Service Type: Web Service
- Build Command: `pip install discord.py python-dotenv aiohttp metaapi-cloud-sdk`
- Start Command: `python main.py`
- Runtime: Python 3.11.0

### 3. Features Included
- `/entry` - Create trading signals with automatic TP/SL calculations
- `/stats` - Display trading performance statistics
- `/monitoring` - Show active signals being tracked
- `/mt5setup` - Configure MetaTrader 5 credentials
- `/mt5status` - Check MT5 connection status
- MetaAPI integration for real trading
- Multi-channel broadcasting
- Automatic TP/SL hit detection
- Market monitoring system

### 4. Bot Permissions Required
- Send Messages
- Use Slash Commands
- Mention Everyone
- Read Message History

### 5. Latest Changes
- OANDA API completely removed
- MetaAPI as primary trading integration
- Enhanced error handling
- Improved market monitoring

Ready for 24/7 deployment on Render.com!
# Discord Trading Bot

A professional Discord bot for sending trading signals with automatic TP/SL calculations and comprehensive statistics tracking.

## Features

### 🎯 /entry Command
- **Entry Types**: Buy limit, Sell limit, Buy execution, Sell execution
- **Trading Pairs**: XAUUSD, GBPJPY, USDJPY, GBPUSD, EURUSD, AUDUSD, NZDUSD, US100, US500, and custom pairs
- **Automatic Calculations**: 
  - TP1: 20 pips from entry
  - TP2: 50 pips from entry
  - TP3: 100 pips from entry
  - SL: 70 pips from entry (opposite direction)
- **Multi-Channel Distribution**: Send signals to multiple channels simultaneously
- **Role Tagging**: Tag specific roles at the bottom of signals
- **Proper Formatting**: Correct decimal places and pip values per instrument

### 📊 /stats Command
- **Comprehensive Statistics**: Track TP hits, SL hits, win rates
- **Custom Date Ranges**: Flexible period selection
- **Multi-Channel Distribution**: Send stats to multiple channels
- **Professional Formatting**: Emoji-rich, clean presentation
- **Performance Breakdown**: Detailed explanation of hit statistics

### 🔒 Enhanced Security
- **Split Token System**: Token stored in two environment variables
- **Secure Deployment**: Environment-based configuration
- **Error Handling**: Comprehensive error management

## Setup Instructions

### 1. Discord Bot Setup
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy your bot token and client ID
4. Enable necessary bot permissions:
   - Send Messages
   - Use Slash Commands
   - Mention Everyone (for role tagging)
   - Read Message History

### 2. Environment Configuration
1. Copy `.env.example` to `.env`
2. Split your Discord bot token into two parts:
   ```env
   DISCORD_TOKEN_PART1=first_half_of_token
   DISCORD_TOKEN_PART2=second_half_of_token
   ```
3. Split your Discord client ID into two parts:
   ```env
   DISCORD_CLIENT_ID_PART1=first_part_of_client_id
   DISCORD_CLIENT_ID_PART2=second_part_of_client_id
   ```

### 3. Local Development
```bash
# Install dependencies
pip install discord.py python-dotenv

# Run the bot
python main.py
```

## Render.com Deployment

### 1. Prepare Your Repository
1. Upload all project files to your GitHub repository
2. Ensure all files are committed and pushed

### 2. Render.com Configuration
1. Connect your GitHub repository to Render.com
2. Create a new Web Service
3. Use these settings:

**Build Command:**
```
pip install discord.py python-dotenv
```

**Start Command:**
```
python main.py
```

### 3. Environment Variables on Render
Set these environment variables in your Render dashboard:
- `DISCORD_TOKEN_PART1` = (first half of your Discord bot token)
- `DISCORD_TOKEN_PART2` = (second half of your Discord bot token)  
- `DISCORD_CLIENT_ID_PART1` = (first half of your Discord app client ID)
- `DISCORD_CLIENT_ID_PART2` = (second half of your Discord app client ID)

**Example Token Split:**
If your token is: `MTIzNDU2Nzg5MDEyMzQ1Njc4.ABCDEF.xyz123abc456def789`
- DISCORD_TOKEN_PART1: `MTIzNDU2Nzg5MDEyMzQ1Njc4.ABC`
- DISCORD_TOKEN_PART2: `DEF.xyz123abc456def789`

If your client ID is: `1234567890123456789`
- DISCORD_CLIENT_ID_PART1: `123456789`
- DISCORD_CLIENT_ID_PART2: `0123456789`

### 4. Deploy
1. Click "Deploy" on Render.com
2. Monitor the deployment logs
3. Once deployed, your bot will run 24/7

## Trading Pair Configurations

The bot automatically handles different decimal places and pip values:

- **XAUUSD & US500**: 2 decimals, $0.1 = 1 pip
- **GBPJPY & USDJPY**: 3 decimals, $0.01 = 1 pip
- **GBPUSD & EURUSD**: 4 decimals, $0.0001 = 1 pip
- **AUDUSD & NZDUSD**: 5 decimals, $0.00001 = 1 pip
- **US100**: 1 decimal, $1 = 1 pip

## Usage Examples

### /entry Command
```
/entry 
- type: Buy execution
- pair: XAUUSD
- price: 2028
- channels: #signals, #trading-room
- roles: @traders, @vip
```

### /stats Command
```
/stats
- date_range: 15/06/2025 - 19/06/2025
- total_signals: 9
- tp1_hits: 7
- tp2_hits: 6
- tp3_hits: 5
- sl_hits: 2
- winrate: 100% (8/8)
- channels: #statistics, #performance
```

## File Structure
```
discord-trading-bot/
├── main.py              # Main bot code
├── .env.example         # Environment template
├── render.yaml          # Render.com configuration
├── Procfile            # Process file for deployment
├── runtime.txt         # Python version specification
├── dependencies.txt    # Python dependencies
└── README.md           # Documentation
```

## Security Features
- Split token storage for enhanced security
- Environment-based configuration
- Comprehensive error handling
- Permission validation
   
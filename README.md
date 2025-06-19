# Discord Trading Signal Bot

A Discord bot that creates trading signals with automatic pip calculations for various trading pairs.

## Features

- `/entry` slash command for creating trading signals
- Support for multiple trading pairs (XAUUSD, GBPJPY, USDJPY, GBPUSD, EURUSD, AUDUSD, NZDUSD, US100, US500, and custom pairs)
- Automatic TP/SL calculations (TP1: 20 pips, TP2: 50 pips, TP3: 100 pips, SL: 50 pips)
- Multi-channel message distribution
- Custom role tagging
- Built-in web server for uptime monitoring
- PostgreSQL database support

## Setup

1. Install dependencies:
```bash
npm install
```

2. Set up your Discord credentials:

**Option A: Environment Variables (Recommended)**
```
DISCORD_TOKEN_PART1=first_half_of_your_token
DISCORD_TOKEN_PART2=second_half_of_your_token
DISCORD_CLIENT_ID_PART1=first_half_of_client_id
DISCORD_CLIENT_ID_PART2=second_half_of_client_id
DATABASE_URL=your_postgresql_url (optional)
```

**Option B: Direct in config.js (Split for Security)**
Edit `config.js` and replace:
- `REPLACE_WITH_FIRST_HALF_OF_TOKEN` with the first half of your Discord token
- `REPLACE_WITH_SECOND_HALF_OF_TOKEN` with the second half of your Discord token
- `REPLACE_WITH_FIRST_HALF_OF_CLIENT_ID` with the first half of your client ID
- `REPLACE_WITH_SECOND_HALF_OF_CLIENT_ID` with the second half of your client ID

**Token Splitting Example:**
If your token is `MTIzNDU2Nzg5MDEyMzQ1Njc4OTA.GaBcDe.FgHiJkLmNoPqRsTuVwXyZ123456789`
- Part 1: `MTIzNDU2Nzg5MDEyMzQ1Njc4OTA.GaBcDe.FgHiJk`
- Part 2: `LmNoPqRsTuVwXyZ123456789`

3. Run the bot:
```bash
node index.js
```

## Commands

### /entry
Creates a trading signal with the following options:
- **type**: Buy limit, Sell limit, Buy execution, Sell execution
- **pair**: Trading pair selection
- **price**: Entry price (supports decimals)
- **channels**: Discord channels to send signal to
- **roles**: Roles to tag at the bottom of the signal
- **custom_pair**: Custom trading pair (when "Other" is selected)
- **decimals**: Decimal precision for custom pairs

## Pip Calculations

- **XAUUSD & US500**: $0.1 = 1 pip (2 decimals)
- **USDJPY & GBPJPY**: $0.01 = 1 pip (3 decimals)
- **EURUSD & GBPUSD**: $0.0001 = 1 pip (4 decimals)
- **AUDUSD & NZDUSD**: $0.0001 = 1 pip (5 decimals)
- **US100**: $1 = 1 pip (1 decimal)

## Web Interface

The bot includes a web server on port 5000 for monitoring:
- `/` - Bot status and uptime
- `/health` - Health check endpoint

## File Structure

```
├── index.js              # Main bot file
├── config.js             # Configuration
├── commands/
│   └── entry.js          # Entry command handler
├── utils/
│   ├── pipCalculator.js  # Pip calculation logic
│   └── messageFormatter.js # Message formatting
└── package.json          # Dependencies
```

## Discord Bot Permissions

Required permissions:
- Send Messages
- Use Slash Commands
- Read Message History
- View Channels
- Mention Everyone

## Deployment

The bot can be deployed on any Node.js hosting platform. It's configured to run on port 5000 and includes health monitoring endpoints for uptime services.
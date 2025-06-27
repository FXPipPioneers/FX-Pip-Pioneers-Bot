# Discord Trading Bot

## Overview

This is a professional Discord bot designed for trading signal distribution with automatic TP/SL calculations and comprehensive statistics tracking. The bot provides a complete solution for forex and commodity trading communities to share and track trading signals across multiple Discord channels.

## System Architecture

### Core Technologies
- **Runtime**: Python 3.11
- **Framework**: Discord.py 2.5.2 (async/await architecture)
- **Environment Management**: python-dotenv for configuration
- **Web Framework**: aiohttp for web server functionality
- **Deployment**: Multi-platform support (Render.com, Heroku, Replit)

### Security Architecture
- **Split Token System**: Discord bot tokens are split into two environment variables for enhanced security
- **Environment-based Configuration**: All sensitive data stored in environment variables
- **Secure Deployment**: No hardcoded credentials in source code

## Key Components

### Bot Commands
1. **`/entry` Command**: Creates and distributes trading signals
   - Entry types: Buy limit, Sell limit, Buy execution, Sell execution
   - Supported pairs: XAUUSD, GBPJPY, USDJPY, GBPUSD, EURUSD, AUDUSD, NZDUSD, US100, US500, custom pairs
   - Automatic TP/SL calculation based on pip values
   - Multi-channel distribution
   - Role tagging functionality

2. **`/stats` Command**: Displays trading performance statistics
   - Customizable date ranges
   - TP hit tracking (TP1, TP2, TP3)
   - SL hit tracking
   - Win rate calculations
   - Multi-channel distribution

### Trading Logic
- **Pip Calculation Engine**: Instrument-specific pip value calculations
- **Price Formatting**: Decimal precision based on trading pair requirements
- **Automatic TP/SL Generation**: 
  - TP1: 20 pips from entry
  - TP2: 50 pips from entry  
  - TP3: 100 pips from entry
  - SL: 70 pips from entry (opposite direction)

### Message Distribution
- **Multi-channel Broadcasting**: Send signals to multiple channels simultaneously
- **Role Tagging System**: Configurable role mentions at message bottom
- **Immediate Delivery**: Real-time signal distribution without delays

## Data Flow

1. **Command Input**: User executes `/entry` or `/stats` slash command
2. **Parameter Validation**: Bot validates trading pair, price format, and channels
3. **Calculation Engine**: Automatic TP/SL calculation based on pair configuration
4. **Message Generation**: Professional formatting with proper decimal places
5. **Multi-channel Distribution**: Simultaneous broadcasting to selected channels
6. **Role Notification**: Tag specified roles at message bottom

### Trading Pair Configuration
```python
PAIR_CONFIG = {
    'XAUUSD': {'decimals': 2, 'pip_value': 0.1},
    'GBPJPY': {'decimals': 3, 'pip_value': 0.01},
    'USDJPY': {'decimals': 3, 'pip_value': 0.01},
    'GBPUSD': {'decimals': 4, 'pip_value': 0.0001},
    'EURUSD': {'decimals': 4, 'pip_value': 0.0001},
    'AUDUSD': {'decimals': 5, 'pip_value': 0.0001},
    'NZDUSD': {'decimals': 5, 'pip_value': 0.0001},
    'US100': {'decimals': 0, 'pip_value': 1.0},
    'US500': {'decimals': 2, 'pip_value': 0.1}
}
```

## External Dependencies

### Required Packages
- `discord.py==2.5.2`: Discord API interaction
- `python-dotenv==1.1.0`: Environment variable management
- `aiohttp==3.12.13`: Web server functionality

### Discord API Requirements
- Bot token with appropriate permissions:
  - Send Messages
  - Use Slash Commands
  - Mention Everyone (for role tagging)
  - Read Message History

### Environment Variables
- `DISCORD_TOKEN_PART1`: First half of Discord bot token
- `DISCORD_TOKEN_PART2`: Second half of Discord bot token
- `DISCORD_CLIENT_ID_PART1`: First half of Discord client ID
- `DISCORD_CLIENT_ID_PART2`: Second half of Discord client ID

## Deployment Strategy

### Multi-platform Support
1. **Render.com**: Web service deployment with automatic scaling
2. **Heroku**: Worker dyno configuration via Procfile
3. **Replit**: Development and testing environment

### Deployment Configuration
- **Build Command**: `pip install discord.py python-dotenv aiohttp`
- **Start Command**: `python main.py`
- **Runtime**: Python 3.11.0
- **Service Type**: Web service (keeps bot alive 24/7)

### Security Considerations
- Split token system prevents complete token exposure
- Environment-based configuration
- No sensitive data in version control
- Secure deployment practices across platforms

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- June 26, 2025: Implemented MetaTrader 5 integration for automatic trade execution
- June 26, 2025: Added market monitoring system with automatic TP/SL hit detection
- June 26, 2025: Fixed channel selection issue for servers with duplicate channel names
- June 26, 2025: Added randomized Discord reply messages for TP1/TP2/TP3/SL hits
- June 26, 2025: Created /channels command to help with precise channel selection
- June 26, 2025: Added /signals command to monitor active trading signals

## Changelog

Changelog:
- June 24, 2025. Initial setup
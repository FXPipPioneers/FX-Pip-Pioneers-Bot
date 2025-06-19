# Discord Trading Bot Setup Guide

## Quick Setup for GitHub Deployment

### 1. Download and Extract
Download `discord-bot-github.tar.gz` and extract all files to your project directory.

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Discord Credentials
Edit `config.js` and replace the placeholder values:

**Discord Token (split for security):**
- Line 4: Replace `'REPLACE_WITH_FIRST_HALF_OF_TOKEN'` with first half of your Discord bot token
- Line 5: Replace `'REPLACE_WITH_SECOND_HALF_OF_TOKEN'` with second half of your Discord bot token

**Discord Client ID (split for security):**
- Line 9: Replace `'REPLACE_WITH_FIRST_HALF_OF_CLIENT_ID'` with first half of your Discord app client ID
- Line 10: Replace `'REPLACE_WITH_SECOND_HALF_OF_CLIENT_ID'` with second half of your Discord app client ID

### 4. Run the Bot
```bash
node index.js
```

## Features
- `/entry` slash command for all major trading pairs
- Automatic TP/SL calculations (20, 50, 100 pips TP / 50 pips SL)
- Multi-channel messaging support
- Mandatory role tagging for notifications
- Built-in web server for uptime monitoring on port 5000

## Trading Pairs Supported
XAUUSD, GBPJPY, USDJPY, EURJPY, AUDJPY, NZDJPY, CADJPY, CHFJPY, EURGBP, GBPUSD, EURUSD, GBPCAD, GBPAUD, GBPNZD, GBPCHF, AUDCAD, AUDCHF, AUDNZD, AUDUSD, CADCHF, CADJPY, EURAUD, EURCAD, EURCHF, EURNZD, NZDCAD, NZDCHF, NZDUSD, USDCAD, USDCHF, Other

## Security Features
- Split token storage prevents accidental exposure
- Environment variable support for production deployment
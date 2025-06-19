# Render Deployment Setup Guide

## For Render.com Deployment

### 1. Repository Setup
Upload all files to your GitHub repository.

### 2. Render Configuration
**Build Command:** `npm install`
**Start Command:** `node index.js`

### 3. Environment Variables
In Render dashboard, add these environment variables:
- `DISCORD_TOKEN_PART1` = (first half of your Discord bot token)
- `DISCORD_TOKEN_PART2` = (second half of your Discord bot token)
- `DISCORD_CLIENT_ID_PART1` = (first half of your Discord app client ID)
- `DISCORD_CLIENT_ID_PART2` = (second half of your Discord app client ID)

### 4. Package Manager
- Render will automatically detect and use Yarn (yarn.lock is included)
- This resolves the package-lock.json warning

### 5. Files for Upload
**IMPORTANT:** Rename `render-package.json` to `package.json` before uploading to GitHub.
This optimized package.json includes:
- Proper build script that installs dependencies
- Start script for the bot
- Node.js engine specification
- Render deployment optimization

### 6. Port Configuration
The bot runs a web server on port 5000 for health checks and uptime monitoring.
Render will automatically detect and use this port.

### Commands Available
- `/entry` - Create trading signals with automatic TP/SL calculations
- `/stats` - Display trading performance statistics

### 24/7 Operation
Once deployed on Render, your bot will run continuously without interruption.
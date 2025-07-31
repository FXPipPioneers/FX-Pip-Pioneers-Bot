# Render Deployment Guide

## Method 1: Using render.yaml (Recommended)

1. Connect your GitHub repository to Render
2. Render will automatically detect the `render.yaml` file
3. Set your environment variables in the Render dashboard:
   - `DISCORD_TOKEN_PART1`
   - `DISCORD_TOKEN_PART2`
   - `DISCORD_CLIENT_ID_PART1`
   - `DISCORD_CLIENT_ID_PART2`

## Method 2: Manual Render Configuration

If render.yaml doesn't work, create a new Web Service manually with these settings:

### Build Settings:
- **Build Command**: `pip install --upgrade pip && pip install discord.py==2.5.2 python-dotenv==1.1.0 aiohttp==3.12.13 requests pyrogram==2.0.106 tgcrypto==1.2.5 pytz==2024.1`
- **Start Command**: `python main.py`

### Runtime:
- **Runtime**: `python-3.11.0`

### Environment Variables:
Add these in the Render dashboard:
- `DISCORD_TOKEN_PART1` = (first half of your Discord bot token)
- `DISCORD_TOKEN_PART2` = (second half of your Discord bot token)
- `DISCORD_CLIENT_ID_PART1` = (first half of your Discord client ID)
- `DISCORD_CLIENT_ID_PART2` = (second half of your Discord client ID)

### Health Check:
- **Health Check Path**: `/health`

## Method 3: Using requirements.txt

If the above methods fail, try using the requirements.txt file:

### Build Command:
```
pip install --upgrade pip && pip install -r requirements.txt
```

## Troubleshooting

If you still get pytz import errors:

1. Check the build logs in Render dashboard
2. Ensure all dependencies are installing correctly
3. Try the manual build command method
4. Contact Render support if the issue persists

## Files Included:
- `main.py` - Complete bot code
- `render.yaml` - Render configuration
- `requirements.txt` - Python dependencies (alternative)
- `dependencies.txt` - Python dependencies (alternative)
- `build.sh` - Build script (alternative)
- `Procfile` - Process file for other platforms
- `runtime.txt` - Python version specification
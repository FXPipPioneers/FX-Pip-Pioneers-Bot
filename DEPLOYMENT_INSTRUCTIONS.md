# Discord Trading Bot - Deployment Instructions

## For Render.com Deployment

### Service Type: Web Service (FREE)
**Good news:** You can use the FREE Web Service option!

### Build Command:
```
pip install discord.py python-dotenv aiohttp
```

### Start Command:
```
python main.py
```

### Required Environment Variables:
Set these in your Render.com dashboard:

1. `DISCORD_TOKEN_PART1` = (first half of your Discord bot token)
2. `DISCORD_TOKEN_PART2` = (second half of your Discord bot token)
3. `DISCORD_CLIENT_ID_PART1` = (first half of your Discord app client ID)
4. `DISCORD_CLIENT_ID_PART2` = (second half of your Discord app client ID)

### How to Split Your Token:
If your Discord bot token is: `MTIzNDU2Nzg5MDEyMzQ1Njc4.ABCDEF.xyz123abc456def789`

Split it roughly in half:
- DISCORD_TOKEN_PART1: `MTIzNDU2Nzg5MDEyMzQ1Njc4.ABC`
- DISCORD_TOKEN_PART2: `DEF.xyz123abc456def789`

### How to Split Your Client ID:
If your Discord client ID is: `1234567890123456789`

Split it roughly in half:
- DISCORD_CLIENT_ID_PART1: `123456789`
- DISCORD_CLIENT_ID_PART2: `0123456789`

### Deployment Steps:
1. Upload all files to your GitHub repository
2. Connect GitHub to Render.com
3. **Create a new "Web Service"** (FREE tier available)
4. Set the build and start commands above
5. Add the environment variables
6. Deploy

Your bot will run 24/7 once deployed successfully!

### How it works:
The bot now includes a simple web server that responds to health checks, allowing it to use Render's free Web Service tier instead of the paid Background Worker.
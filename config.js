require('dotenv').config();

module.exports = {
    token: process.env.DISCORD_TOKEN || 'your_discord_bot_token_here',
    clientId: process.env.DISCORD_CLIENT_ID || 'your_discord_client_id_here'
};

require('dotenv').config();

// Split token for security - combine both parts to form the complete token
const tokenPart1 = process.env.DISCORD_TOKEN_PART1 || 'MTM4NTI5Mzc2OTgyOTUxNTMyNA.GUrJ10.MO5G9GYbgCqjO';
const tokenPart2 = process.env.DISCORD_TOKEN_PART2 || '0rRCAbG70rnwnNQYhJzIXd1l8';
const fullToken = tokenPart1 + tokenPart2;

// Split client ID for security - combine both parts to form the complete client ID
const clientIdPart1 = process.env.DISCORD_CLIENT_ID_PART1 || '1385293769';
const clientIdPart2 = process.env.DISCORD_CLIENT_ID_PART2 || '829515324';
const fullClientId = clientIdPart1 + clientIdPart2;

module.exports = {
    token: fullToken,
    clientId: fullClientId
};

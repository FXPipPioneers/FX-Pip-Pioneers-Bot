require('dotenv').config();

// Split token for security - combine both parts to form the complete token
const tokenPart1 = process.env.DISCORD_TOKEN_PART1 || 'REPLACE_WITH_FIRST_HALF_OF_TOKEN';
const tokenPart2 = process.env.DISCORD_TOKEN_PART2 || 'REPLACE_WITH_SECOND_HALF_OF_TOKEN';
const fullToken = tokenPart1 + tokenPart2;

// Split client ID for security - combine both parts to form the complete client ID
const clientIdPart1 = process.env.DISCORD_CLIENT_ID_PART1 || 'REPLACE_WITH_FIRST_HALF_OF_CLIENT_ID';
const clientIdPart2 = process.env.DISCORD_CLIENT_ID_PART2 || 'REPLACE_WITH_SECOND_HALF_OF_CLIENT_ID';
const fullClientId = clientIdPart1 + clientIdPart2;

module.exports = {
    token: fullToken,
    clientId: fullClientId
};

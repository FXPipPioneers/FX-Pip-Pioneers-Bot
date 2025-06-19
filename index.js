const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const express = require('express');
const config = require('./config');
const entryCommand = require('./commands/entry');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ]
});

// Register slash commands
const rest = new REST({ version: '10' }).setToken(config.token);

const commands = [
    {
        name: 'entry',
        description: 'Create a trading signal entry',
        options: [
            {
                name: 'type',
                description: 'Type of entry',
                type: 3, // STRING
                required: true,
                choices: [
                    { name: 'Buy limit', value: 'buy_limit' },
                    { name: 'Sell limit', value: 'sell_limit' },
                    { name: 'Buy execution', value: 'buy_execution' },
                    { name: 'Sell execution', value: 'sell_execution' }
                ]
            },
            {
                name: 'pair',
                description: 'Trading pair',
                type: 3, // STRING
                required: true,
                choices: [
                    { name: 'XAUUSD', value: 'XAUUSD' },
                    { name: 'GBPJPY', value: 'GBPJPY' },
                    { name: 'USDJPY', value: 'USDJPY' },
                    { name: 'GBPUSD', value: 'GBPUSD' },
                    { name: 'EURUSD', value: 'EURUSD' },
                    { name: 'AUDUSD', value: 'AUDUSD' },
                    { name: 'NZDUSD', value: 'NZDUSD' },
                    { name: 'US100', value: 'US100' },
                    { name: 'US500', value: 'US500' },
                    { name: 'Other', value: 'other' }
                ]
            },
            {
                name: 'price',
                description: 'Entry price (e.g., 2995.50 or 1.2345)',
                type: 10, // NUMBER (allows decimals)
                required: true
            },
            {
                name: 'channels',
                description: 'Mention channels to send signal to (e.g., #channel1 #channel2)',
                type: 3, // STRING
                required: true
            },
            {
                name: 'roles',
                description: 'Roles to tag at the bottom (e.g., @signal alert @traders)',
                type: 3, // STRING
                required: true
            },
            {
                name: 'custom_pair',
                description: 'Custom trading pair (only when "Other" is selected)',
                type: 3, // STRING
                required: false
            },
            {
                name: 'decimals',
                description: 'Number of decimals for custom pair (only when "Other" is selected)',
                type: 4, // INTEGER
                required: false
            }
        ]
    }
];

async function deployCommands() {
    try {
        console.log('Started refreshing application (/) commands.');
        
        // Get all guilds the bot is in
        const guilds = client.guilds.cache.map(guild => guild.id);
        
        for (const guildId of guilds) {
            await rest.put(
                Routes.applicationGuildCommands(config.clientId, guildId),
                { body: commands }
            );
        }
        
        console.log('Successfully reloaded application (/) commands.');
    } catch (error) {
        console.error('Error deploying commands:', error);
    }
}

client.once('ready', async () => {
    console.log(`Logged in as ${client.user.tag}!`);
    await deployCommands();
});

client.on('guildCreate', async (guild) => {
    // Deploy commands to new guild
    try {
        await rest.put(
            Routes.applicationGuildCommands(config.clientId, guild.id),
            { body: commands }
        );
        console.log(`Deployed commands to new guild: ${guild.name}`);
    } catch (error) {
        console.error('Error deploying commands to new guild:', error);
    }
});

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) return;
    
    if (interaction.commandName === 'entry') {
        await entryCommand.execute(interaction);
    }
});

client.on('error', (error) => {
    console.error('Discord client error:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('Unhandled promise rejection:', error);
});

// Create Express server for uptime monitoring
const app = express();
const PORT = process.env.PORT || 5000;

app.get('/', (req, res) => {
    const botStatus = client.user ? 'Online' : 'Offline';
    const uptime = process.uptime();
    const uptimeHours = Math.floor(uptime / 3600);
    const uptimeMinutes = Math.floor((uptime % 3600) / 60);
    
    res.json({
        status: 'Discord Bot Server Running',
        bot_status: botStatus,
        bot_name: client.user ? client.user.tag : 'Not connected',
        uptime: `${uptimeHours}h ${uptimeMinutes}m`,
        timestamp: new Date().toISOString()
    });
});

app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy',
        bot_connected: !!client.user,
        timestamp: new Date().toISOString()
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Web server running on port ${PORT}`);
});

client.login(config.token);

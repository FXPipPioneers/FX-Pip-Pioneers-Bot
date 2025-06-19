const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const express = require('express');
const config = require('./config');
const entryCommand = require('./commands/entry');
const statsCommand = require('./commands/stats');

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
    entryCommand.data.toJSON(),
    statsCommand.data.toJSON()
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
    } else if (interaction.commandName === 'stats') {
        await statsCommand.execute(interaction);
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

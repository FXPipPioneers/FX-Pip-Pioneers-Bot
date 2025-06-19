const { EmbedBuilder } = require('discord.js');
const pipCalculator = require('../utils/pipCalculator');
const messageFormatter = require('../utils/messageFormatter');

module.exports = {
    async execute(interaction) {
        try {
            const type = interaction.options.getString('type');
            let pair = interaction.options.getString('pair');
            const price = interaction.options.getNumber('price');
            const channelsInput = interaction.options.getString('channels');
            const customPair = interaction.options.getString('custom_pair');
            const customDecimals = interaction.options.getInteger('decimals');
            const rolesToTag = interaction.options.getString('roles');

            // Handle custom pair
            if (pair === 'other') {
                if (!customPair) {
                    return await interaction.reply({
                        content: 'Please provide a custom trading pair when selecting "Other".',
                        flags: 64 // EPHEMERAL flag
                    });
                }
                if (customDecimals === null || customDecimals === undefined) {
                    return await interaction.reply({
                        content: 'Please provide the number of decimals for your custom trading pair.',
                        flags: 64 // EPHEMERAL flag
                    });
                }
                pair = customPair.toUpperCase();
            }

            // Parse channel mentions from the input
            const channelIds = [];
            const channelMentions = channelsInput.match(/<#(\d+)>/g);
            
            if (channelMentions) {
                for (const mention of channelMentions) {
                    const channelId = mention.match(/\d+/)[0];
                    channelIds.push(channelId);
                }
            } else {
                // If no channel mentions found, try to parse as channel IDs
                const ids = channelsInput.split(/[,\s]+/).filter(id => id.trim());
                channelIds.push(...ids);
            }

            if (channelIds.length === 0) {
                return await interaction.reply({
                    content: 'Please mention at least one channel (e.g., #channel1 #channel2) or provide channel IDs.',
                    flags: 64 // EPHEMERAL flag
                });
            }

            // Calculate pip values and format prices
            const calculations = pipCalculator.calculateLevels(pair, price, type, customDecimals);
            
            if (!calculations) {
                return await interaction.reply({
                    content: 'Error calculating pip levels. Please check your input.',
                    flags: 64 // EPHEMERAL flag
                });
            }

            // Format the message
            const signalMessage = messageFormatter.formatSignal(pair, type, calculations, rolesToTag);

            // Send to all specified channels
            const successfulChannels = [];
            const failedChannels = [];

            for (const channelId of channelIds) {
                try {
                    const channel = await interaction.client.channels.fetch(channelId.trim());
                    
                    if (!channel) {
                        failedChannels.push(`Channel ID ${channelId} not found`);
                        continue;
                    }

                    if (!channel.isTextBased()) {
                        failedChannels.push(`${channel.name} is not a text channel`);
                        continue;
                    }

                    // Check if bot has permission to send messages
                    const permissions = channel.permissionsFor(interaction.client.user);
                    if (!permissions || !permissions.has('SendMessages')) {
                        failedChannels.push(`No permission to send messages in ${channel.name}`);
                        continue;
                    }

                    await channel.send(signalMessage);
                    successfulChannels.push(channel.name);
                } catch (error) {
                    console.error(`Error sending to channel ${channelId}:`, error);
                    failedChannels.push(`${channelId}: ${error.message}`);
                }
            }

            // Respond to the user
            let responseMessage = '';
            if (successfulChannels.length > 0) {
                responseMessage += `✅ Signal sent successfully to: ${successfulChannels.join(', ')}\n`;
            }
            if (failedChannels.length > 0) {
                responseMessage += `❌ Failed to send to: ${failedChannels.join(', ')}`;
            }

            await interaction.reply({
                content: responseMessage || 'Signal processing completed.',
                flags: 64 // EPHEMERAL flag
            });

        } catch (error) {
            console.error('Error in entry command:', error);
            
            if (!interaction.replied && !interaction.deferred) {
                await interaction.reply({
                    content: 'An error occurred while processing your entry command. Please try again.',
                    flags: 64 // EPHEMERAL flag
                });
            }
        }
    }
};

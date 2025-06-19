module.exports = {
    /**
     * Format trading signal message
     * @param {string} pair - Trading pair
     * @param {string} type - Entry type
     * @param {object} calculations - Calculated TP/SL levels
     * @param {string} rolesToTag - Roles to tag at the bottom
     * @returns {string} Formatted signal message
     */
    formatSignal(pair, type, calculations, rolesToTag) {
        // Convert type to readable format
        const typeMap = {
            'buy_limit': 'Buy limit',
            'sell_limit': 'Sell limit',
            'buy_execution': 'Buy execution',
            'sell_execution': 'Sell execution'
        };

        const readableType = typeMap[type] || type;

        // Use the provided roles (now required)
        const tagsToUse = rolesToTag;

        const message = `**Trade signal for: ${pair.toUpperCase()}**
Entry Type: ${readableType}
Entry Price: ${calculations.entry}

**Take Profit Levels:**
TP1: ${calculations.tp1}
TP2: ${calculations.tp2}
TP3: ${calculations.tp3}

Stop Loss: ${calculations.sl}

${tagsToUse}`;

        return message;
    }
};

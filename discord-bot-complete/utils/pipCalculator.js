module.exports = {
    /**
     * Calculate TP and SL levels based on trading pair and entry price
     * @param {string} pair - Trading pair
     * @param {number} entryPrice - Entry price
     * @param {string} type - Entry type (buy_limit, sell_limit, buy_execution, sell_execution)
     * @param {number} customDecimals - Custom decimal places for "other" pairs
     * @returns {object} Calculated levels with formatted prices
     */
    calculateLevels(pair, entryPrice, type, customDecimals = null) {
        try {
            const isBuy = type.includes('buy');
            let pipValue;
            let decimals;

            // Define pip values and decimal places for each pair
            switch (pair.toUpperCase()) {
                case 'XAUUSD':
                case 'US500':
                    pipValue = 0.1; // $0.1 = 1 pip
                    decimals = 2;
                    break;
                case 'USDJPY':
                case 'GBPJPY':
                    pipValue = 0.01; // $0.01 = 1 pip
                    decimals = 3;
                    break;
                case 'EURUSD':
                case 'GBPUSD':
                    pipValue = 0.0001; // Standard forex pip
                    decimals = 4;
                    break;
                case 'AUDUSD':
                case 'NZDUSD':
                    pipValue = 0.0001; // $0.0001 = 1 pip
                    decimals = 5;
                    break;
                case 'US100':
                    pipValue = 1; // $1 = 1 pip
                    decimals = 1;
                    break;
                default:
                    // For custom pairs, use default pip value and custom decimals
                    pipValue = 0.0001;
                    decimals = customDecimals || 4;
                    break;
            }

            // Calculate pip distances
            const pip20 = pipValue * 20;
            const pip50 = pipValue * 50;
            const pip100 = pipValue * 100;

            let tp1, tp2, tp3, sl;

            if (isBuy) {
                // For buy orders: TP above entry, SL below entry
                tp1 = entryPrice + pip20;
                tp2 = entryPrice + pip50;
                tp3 = entryPrice + pip100;
                sl = entryPrice - pip50;
            } else {
                // For sell orders: TP below entry, SL above entry
                tp1 = entryPrice - pip20;
                tp2 = entryPrice - pip50;
                tp3 = entryPrice - pip100;
                sl = entryPrice + pip50;
            }

            // Format prices according to decimal places
            return {
                entry: this.formatPrice(entryPrice, decimals),
                tp1: this.formatPrice(tp1, decimals),
                tp2: this.formatPrice(tp2, decimals),
                tp3: this.formatPrice(tp3, decimals),
                sl: this.formatPrice(sl, decimals),
                decimals: decimals
            };

        } catch (error) {
            console.error('Error calculating levels:', error);
            return null;
        }
    },

    /**
     * Format price according to specified decimal places
     * @param {number} price - Price to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted price with $ symbol
     */
    formatPrice(price, decimals) {
        return '$' + price.toFixed(decimals);
    }
};

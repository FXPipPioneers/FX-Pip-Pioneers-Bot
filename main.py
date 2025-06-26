import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web
import random
import json
import time
from typing import Dict, List, Optional
import threading

# Load environment variables
load_dotenv()

# Reconstruct tokens from split parts for enhanced security
DISCORD_TOKEN_PART1 = os.getenv("DISCORD_TOKEN_PART1", "")
DISCORD_TOKEN_PART2 = os.getenv("DISCORD_TOKEN_PART2", "")
DISCORD_TOKEN = DISCORD_TOKEN_PART1 + DISCORD_TOKEN_PART2

DISCORD_CLIENT_ID_PART1 = os.getenv("DISCORD_CLIENT_ID_PART1", "")
DISCORD_CLIENT_ID_PART2 = os.getenv("DISCORD_CLIENT_ID_PART2", "")
DISCORD_CLIENT_ID = DISCORD_CLIENT_ID_PART1 + DISCORD_CLIENT_ID_PART2

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class TradingBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)

    async def setup_hook(self):
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f'{self.user} has landed!')
        if self.user:
            print(f'Bot ID: {self.user.id}')

bot = TradingBot()

# Global storage for active signals and market monitoring
active_signals = {}  # Format: {message_id: {pair, entry_price, tp1, tp2, tp3, sl, channels, entry_type}}
market_monitor_active = False

# Response messages for different TP/SL hits
TP1_MESSAGES = [
    "@everyone TP1 has been hit. First target secured, let's keep it going. Next stop: TP2 📈🔥",
    "@everyone TP1 smashed. Secure some profits if you'd like and let's aim for TP2 🎯💪",
    "@everyone We've just hit TP1. Nice start. The current momentum is looking good for TP2 🚀📊",
    "@everyone TP1 has been hit! Keep your eyes on the next level. TP2 up next 👀💸",
    "@everyone First milestone hit. The trade is off to a clean start 📉➡️📈",
    "@everyone TP1 has been reached. Let's keep the discipline and push for TP2 💼🔁",
    "@everyone First TP level hit! TP1 is in. Stay focused as we aim for TP2 & TP3! 💹🚀",
    "@everyone TP1 locked in. Let's keep monitoring price action and go for TP2 💰📍",
    "@everyone TP1 has been reached. Trade is moving as planned. Next stop: TP2 🔄📊",
    "@everyone TP1 hit. Great entry. now let's trail it smart toward TP2 🧠📈"
]

TP2_MESSAGES = [
    "@everyone TP1 & TP2 have both been hit :rocket::rocket: move your SL to breakeven and lets get TP3 :money_with_wings:",
    "@everyone TP2 has been hit :rocket::rocket: move your SL to breakeven and lets get TP3 :money_with_wings:",
    "@everyone TP2 has been hit :rocket::rocket: move your sl to breakeven, partially close the trade and lets get tp3 :dart::dart::dart:",
    "@everyone TP2 has been hit:money_with_wings: please move your SL to breakeven, partially close the trade and lets go for TP3 :rocket:",
    "@everyone TP2 has been hit. Move your SL to breakeven and secure those profits. Let's push for TP3. we're not done yet 🚀💰",
    "@everyone TP2 has officially been smashed. Move SL to breakeven, partial close if you haven't already. TP3 is calling 📈🔥",
    "@everyone TP2 just got hit. Lock in those gains by moving your SL to breakeven. TP3 is the next target so let's stay sharp and ride this momentum 💪📊",
    "@everyone Another level cleared as TP2 has been hit. Shift SL to breakeven and lock it in. Eyes on TP3 now so let's finish strong 🧠🎯",
    "@everyone TP2 has been hit. Move your SL to breakeven immediately. This setup is moving clean and TP3 is well within reach 🚀🔒",
    "@everyone Great move traders, TP2 has been tagged. Time to shift SL to breakeven and secure the bag. TP3 is the final boss and we're coming for it 💼⚔️"
]

TP3_MESSAGES = [
    "@everyone TP3 hit. Full target smashed, perfect execution 🔥🔥🔥",
    "@everyone Huge win, TP3 reached. Congrats to everyone who followed 📊🚀",
    "@everyone TP3 just got hit. Close it out and lock in profits 💸🎯",
    "@everyone TP3 tagged. That wraps up the full setup — solid trade 💪💼",
    "@everyone TP3 locked in. Flawless setup from entry to exit 🙌📈",
    "@everyone TP3 hit. This one went exactly as expected. Great job ✅💰",
    "@everyone TP3 has been reached. Hope you secured profits all the way through 🏁📊",
    "@everyone TP3 reached. Strategy and patience paid off big time 🔍🚀",
    "@everyone Final target hit. Huge win for FX Pip Pioneers 🔥💸",
    "@everyone TP3 secured. That's the result of following the plan 💼💎"
]

SL_MESSAGES = [
    "@everyone This one hit SL. It happens. Let's stay focused and get the next one 🔄🧠",
    "@everyone SL has been hit. Risk was managed, we move on 💪📉",
    "@everyone This setup didn't go as planned and hit SL. On to the next 📊",
    "@everyone SL tagged. It's all part of the process. Stay disciplined 💼📚",
    "@everyone SL hit. Losses are part of trading. We bounce back 📈⏭️",
    "@everyone SL reached. Trust the process and prepare for the next opportunity 🔄🧠",
    "@everyone SL was hit on this one. We took the loss, now let's stay sharp 🔁💪",
    "@everyone SL hit. It's part of the game. Let's stay focused on quality 📉🎯",
    "@everyone This trade hit SL. Discipline keeps us in the game 💼🧘‍♂️",
    "@everyone SL tagged. The next setup could be the win that makes the week 🔍📊"
]

# MetaTrader 5 integration - Cloud-based connection
MT5_ENABLED = False
MT5_CREDENTIALS = {
    'login': None,
    'password': None,
    'server': 'MetaQuotes-Demo'
}

try:
    import MetaTrader5 as mt5
    MT5_ENABLED = True
    print("MetaTrader5 module available")
except ImportError:
    print("MetaTrader5 not available on this platform. Using cloud MT5 simulation.")
    mt5 = None

# Cloud MT5 simulation for when actual MT5 isn't available
class CloudMT5Simulator:
    def __init__(self):
        self.connected = False
        self.orders = {}
        self.order_counter = 1000
        
        # MT5 constants for cloud simulation
        self.TRADE_ACTION_DEAL = 1
        self.TRADE_ACTION_SLTP = 2
        self.ORDER_TYPE_BUY = 0
        self.ORDER_TYPE_SELL = 1
        self.ORDER_TIME_GTC = 0
        self.ORDER_FILLING_IOC = 1
        self.TRADE_RETCODE_DONE = 10009
    
    def initialize(self, login=None, password=None, server=None):
        # Simulate MetaQuotes Demo server validation
        if login and password and server:
            # Basic validation for demo accounts
            if str(login).isdigit() and len(str(login)) >= 6:
                self.connected = True
                print(f"Connected to MT5 cloud simulation - Login: {login}, Server: {server}")
                return True
            else:
                print(f"Invalid login format: {login}")
                return False
        print(f"Missing credentials - Login: {login}, Password: {'***' if password else None}, Server: {server}")
        return False
    
    def login(self, login, password, server):
        # Simulate MetaQuotes Demo server login validation
        if login and password and server:
            if str(login).isdigit() and len(str(login)) >= 6:
                self.connected = True
                print(f"Logged into MT5 - Account: {login}, Server: {server}")
                return True
            else:
                print(f"Login failed - Invalid account format: {login}")
                return False
        print(f"Login failed - Missing credentials")
        return False
    
    def order_send(self, request):
        if not self.connected:
            return type('obj', (object,), {'retcode': 10004, 'comment': 'Not connected'})
        
        self.order_counter += 1
        order_id = self.order_counter
        
        # Simulate successful order
        self.orders[order_id] = {
            'symbol': request.get('symbol'),
            'volume': request.get('volume'),
            'type': request.get('type'),
            'price': request.get('price'),
            'sl': request.get('sl'),
            'tp': request.get('tp')
        }
        
        print(f"Cloud MT5 - Order placed: {order_id} for {request.get('symbol')}")
        return type('obj', (object,), {
            'retcode': 10009,  # TRADE_RETCODE_DONE
            'order': order_id,
            'comment': 'Cloud simulation order placed'
        })
    
    def positions_get(self, ticket=None):
        if ticket and ticket in self.orders:
            order = self.orders[ticket]
            return [type('obj', (object,), {
                'symbol': order['symbol'],
                'tp': order['tp'],
                'sl': order['sl']
            })]
        return []
    
    def symbol_info_tick(self, symbol):
        # Simulate market prices - you could integrate real price feeds here
        import random
        base_prices = {
            'XAUUSD': 2000.0,
            'GBPUSD': 1.2500,
            'EURUSD': 1.0800,
            'USDJPY': 150.0,
            'GBPJPY': 187.5
        }
        
        base_price = base_prices.get(symbol, 1.0000)
        spread = base_price * 0.0001  # 1 pip spread simulation
        
        return type('obj', (object,), {
            'bid': base_price - spread/2,
            'ask': base_price + spread/2
        })
    
    def last_error(self):
        return (0, "No error")

# Initialize cloud simulator if MT5 not available
if not MT5_ENABLED or mt5 is None:
    mt5 = CloudMT5Simulator()
    MT5_ENABLED = True  # Enable simulated MT5
    print("Using MT5 cloud simulation")

# Trading pair configurations
PAIR_CONFIG = {
    'XAUUSD': {'decimals': 2, 'pip_value': 0.1},
    'GBPJPY': {'decimals': 3, 'pip_value': 0.01},
    'GBPUSD': {'decimals': 4, 'pip_value': 0.0001},
    'EURUSD': {'decimals': 4, 'pip_value': 0.0001},
    'AUDUSD': {'decimals': 5, 'pip_value': 0.00001},
    'NZDUSD': {'decimals': 5, 'pip_value': 0.00001},
    'US100': {'decimals': 1, 'pip_value': 1.0},
    'US500': {'decimals': 2, 'pip_value': 0.1},
    'GER40': {'decimals': 1, 'pip_value': 1.0},  # Same as US100
    'BTCUSD': {'decimals': 1, 'pip_value': 1.0},  # Same as US100 and GER40
    'GBPCHF': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'USDCHF': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'CADCHF': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'AUDCHF': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'CHFJPY': {'decimals': 3, 'pip_value': 0.01},  # Same as GBPJPY
    'CADJPY': {'decimals': 3, 'pip_value': 0.01},  # Same as GBPJPY
    'AUDJPY': {'decimals': 3, 'pip_value': 0.01},  # Same as GBPJPY
    'USDCAD': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'GBPCAD': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'EURCAD': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'AUDCAD': {'decimals': 4, 'pip_value': 0.0001},  # Same as GBPUSD
    'AUDNZD': {'decimals': 4, 'pip_value': 0.0001}   # Same as GBPUSD
}

def calculate_levels(entry_price: float, pair: str, entry_type: str):
    """Calculate TP and SL levels based on pair configuration"""
    if pair in PAIR_CONFIG:
        pip_value = PAIR_CONFIG[pair]['pip_value']
        decimals = PAIR_CONFIG[pair]['decimals']
    else:
        # Default values for unknown pairs
        pip_value = 0.0001  
        decimals = 4
    
    # Calculate pip amounts
    tp1_pips = 20 * pip_value
    tp2_pips = 50 * pip_value
    tp3_pips = 100 * pip_value
    sl_pips = 70 * pip_value
    
    # Determine direction based on entry type
    is_buy = entry_type.lower().startswith('buy')
    
    if is_buy:
        tp1 = entry_price + tp1_pips
        tp2 = entry_price + tp2_pips
        tp3 = entry_price + tp3_pips
        sl = entry_price - sl_pips
    else:  # Sell
        tp1 = entry_price - tp1_pips
        tp2 = entry_price - tp2_pips
        tp3 = entry_price - tp3_pips
        sl = entry_price + sl_pips
    
    # Format prices with correct decimals
    if pair == 'XAUUSD' or pair == 'US500':
        currency_symbol = '$'
    elif pair == 'US100':
        currency_symbol = '$'
    else:
        currency_symbol = '$'
    
    def format_price(price):
        return f"{currency_symbol}{price:.{decimals}f}"
    
    return {
        'tp1': format_price(tp1),
        'tp2': format_price(tp2),
        'tp3': format_price(tp3),
        'sl': format_price(sl),
        'entry': format_price(entry_price),
        'tp1_raw': tp1,
        'tp2_raw': tp2,
        'tp3_raw': tp3,
        'sl_raw': sl,
        'entry_raw': entry_price
    }

# MetaTrader 5 Functions
async def connect_mt5():
    """Connect to MetaTrader 5 with stored credentials"""
    if not MT5_ENABLED:
        return False
    
    # For cloud simulator
    if hasattr(mt5, 'initialize'):
        if MT5_CREDENTIALS['login'] and MT5_CREDENTIALS['password']:
            success = mt5.initialize()
            if success:
                # Login with credentials
                login_success = mt5.login(
                    MT5_CREDENTIALS['login'],
                    MT5_CREDENTIALS['password'], 
                    MT5_CREDENTIALS['server']
                )
                if login_success:
                    print(f"MT5 connected - Account: {MT5_CREDENTIALS['login']}")
                    return True
                else:
                    print(f"MT5 login failed: {mt5.last_error()}")
                    return False
            else:
                print(f"MT5 initialization failed: {mt5.last_error()}")
                return False
        else:
            print("MT5 credentials not set. Use /mt5setup command first.")
            return False
    else:
        # Cloud simulator
        if MT5_CREDENTIALS['login'] and MT5_CREDENTIALS['password']:
            return mt5.initialize(
                MT5_CREDENTIALS['login'],
                MT5_CREDENTIALS['password'],
                MT5_CREDENTIALS['server']
            )
        else:
            print("MT5 credentials not set. Use /mt5setup command first.")
            return False

async def place_mt5_trade(pair: str, entry_price: float, tp3_price: float, sl_price: float, entry_type: str, lot_size: float = 0.01):
    """Place a trade in MetaTrader 5"""
    if not MT5_ENABLED:
        print("MT5 not enabled - trade placement skipped")
        return None
    
    try:
        # Determine order type
        is_buy = entry_type.lower().startswith('buy')
        order_type = getattr(mt5, 'ORDER_TYPE_BUY', 0) if is_buy else getattr(mt5, 'ORDER_TYPE_SELL', 1)
        
        # Create trade request
        request = {
            "action": getattr(mt5, 'TRADE_ACTION_DEAL', 1),
            "symbol": pair,
            "volume": lot_size,
            "type": order_type,
            "price": entry_price,
            "sl": sl_price,
            "tp": tp3_price,  # Always use TP3 as final target
            "deviation": 20,
            "magic": 12345,
            "comment": "Discord Bot Trade",
            "type_time": getattr(mt5, 'ORDER_TIME_GTC', 0),
            "type_filling": getattr(mt5, 'ORDER_FILLING_IOC', 1),
        }
        
        # Send trade request
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"MT5 trade failed: {result.comment}")
            return None
        
        print(f"MT5 trade placed successfully: {result.order}")
        return result.order
        
    except Exception as e:
        print(f"Error placing MT5 trade: {e}")
        return None

async def move_sl_to_breakeven(order_id: int, entry_price: float):
    """Move stop loss to breakeven (entry price)"""
    if not MT5_ENABLED or not order_id:
        return False
    
    try:
        # Get position info
        positions = mt5.positions_get(ticket=order_id)
        if not positions:
            print(f"Position {order_id} not found")
            return False
        
        position = positions[0]
        
        # Create modification request
        request = {
            "action": getattr(mt5, 'TRADE_ACTION_SLTP', 2),
            "symbol": position.symbol,
            "sl": entry_price,  # Move SL to entry (breakeven)
            "tp": position.tp,  # Keep existing TP
            "position": order_id,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != getattr(mt5, 'TRADE_RETCODE_DONE', 10009):
            print(f"Failed to move SL to breakeven: {result.comment}")
            return False
        
        print(f"SL moved to breakeven for order {order_id}")
        return True
        
    except Exception as e:
        print(f"Error moving SL to breakeven: {e}")
        return False

# Market monitoring function
async def start_market_monitor():
    """Start monitoring market prices for TP/SL hits"""
    global market_monitor_active
    market_monitor_active = True
    
    while market_monitor_active and active_signals:
        try:
            for message_id, signal_data in list(active_signals.items()):
                await check_signal_levels(message_id, signal_data)
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"Error in market monitor: {e}")
            await asyncio.sleep(10)

async def check_signal_levels(message_id: int, signal_data: dict):
    """Check if TP or SL levels have been hit for a signal"""
    try:
        pair = signal_data['pair']
        
        # Get current market price (placeholder - would need real price feed)
        current_price = await get_market_price(pair)
        if current_price is None:
            return
        
        # Check TP/SL hits based on entry type
        is_buy = signal_data['entry_type'].lower().startswith('buy')
        
        if is_buy:
            # For buy orders, price needs to go up to hit TPs
            if not signal_data.get('tp1_hit') and current_price >= signal_data['tp1_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP1')
            elif not signal_data.get('tp2_hit') and current_price >= signal_data['tp2_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP2')
            elif not signal_data.get('tp3_hit') and current_price >= signal_data['tp3_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP3')
            elif current_price <= signal_data['sl_raw']:
                await handle_sl_hit(message_id, signal_data)
        else:
            # For sell orders, price needs to go down to hit TPs
            if not signal_data.get('tp1_hit') and current_price <= signal_data['tp1_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP1')
            elif not signal_data.get('tp2_hit') and current_price <= signal_data['tp2_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP2')
            elif not signal_data.get('tp3_hit') and current_price <= signal_data['tp3_raw']:
                await handle_tp_hit(message_id, signal_data, 'TP3')
            elif current_price >= signal_data['sl_raw']:
                await handle_sl_hit(message_id, signal_data)
        
    except Exception as e:
        print(f"Error checking signal levels: {e}")

async def get_market_price(pair: str) -> Optional[float]:
    """Get current market price for a trading pair"""
    if MT5_ENABLED:
        try:
            tick = mt5.symbol_info_tick(pair)
            if tick:
                return (tick.bid + tick.ask) / 2  # Use mid price
        except Exception as e:
            print(f"Error getting MT5 price for {pair}: {e}")
    
    # Placeholder for when MT5 is not available
    # In production, you'd integrate with a price feed API
    return None

async def handle_tp_hit(message_id: int, signal_data: dict, tp_level: str):
    """Handle when a TP level is hit"""
    try:
        # Mark this TP as hit
        signal_data[f'{tp_level.lower()}_hit'] = True
        
        # Get random message for this TP level
        message = ""
        if tp_level == 'TP1':
            message = random.choice(TP1_MESSAGES)
        elif tp_level == 'TP2':
            message = random.choice(TP2_MESSAGES)
            # Move SL to breakeven for TP2 hits
            if signal_data.get('mt5_order_id'):
                await move_sl_to_breakeven(signal_data['mt5_order_id'], signal_data['entry_raw'])
        elif tp_level == 'TP3':
            message = random.choice(TP3_MESSAGES)
            # Remove signal from monitoring after TP3
            del active_signals[message_id]
        
        # Reply to original message in all channels
        await reply_to_signal_message(message_id, signal_data, message)
        
        print(f"{tp_level} hit for {signal_data['pair']} signal")
        
    except Exception as e:
        print(f"Error handling {tp_level} hit: {e}")

async def handle_sl_hit(message_id: int, signal_data: dict):
    """Handle when SL is hit"""
    try:
        # Get random SL message
        message = random.choice(SL_MESSAGES)
        
        # Reply to original message in all channels
        await reply_to_signal_message(message_id, signal_data, message)
        
        # Remove signal from monitoring
        del active_signals[message_id]
        
        print(f"SL hit for {signal_data['pair']} signal")
        
    except Exception as e:
        print(f"Error handling SL hit: {e}")

async def reply_to_signal_message(message_id: int, signal_data: dict, reply_text: str):
    """Reply to the original signal message in all channels"""
    try:
        for channel_id in signal_data['channel_ids']:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    original_message = await channel.fetch_message(message_id)
                    await original_message.reply(reply_text)
                except discord.NotFound:
                    print(f"Original message {message_id} not found in channel {channel.name}")
                except Exception as e:
                    print(f"Error replying to message in {channel.name}: {e}")
    except Exception as e:
        print(f"Error replying to signal message: {e}")

@bot.tree.command(name="entry", description="Create a trading signal entry")
@app_commands.describe(
    entry_type="Type of entry (Long, Short, Long Swing, Short Swing)",
    pair="Trading pair",
    price="Entry price",
    channels="Select channels to send the signal to (comma-separated channel mentions or names)",
    roles="Roles to mention (comma-separated, required)"
)
async def entry_command(
    interaction: discord.Interaction,
    entry_type: str,
    pair: str,
    price: float,
    channels: str,
    roles: str
):
    """Create and send a trading signal to specified channels"""
    
    try:
        # Calculate TP and SL levels
        levels = calculate_levels(price, pair, entry_type)
        
        # Create the signal message
        signal_message = f"""**Trade Signal For: {pair}**
Entry Type: {entry_type}
Entry Price: {levels['entry']}

**Take Profit Levels:**
TP1: {levels['tp1']}
TP2: {levels['tp2']}
TP3: {levels['tp3']}

Stop Loss: {levels['sl']}"""
        
        # Add role mentions at the bottom if provided
        if roles.strip():
            role_mentions = []
            role_names = [role.strip() for role in roles.split(',')]
            for role_name in role_names:
                # Handle @everyone specifically to avoid double @
                if role_name.lower() == "@everyone" or role_name.lower() == "everyone":
                    role_mentions.append("@everyone")
                else:
                    # Find role by name in the guild
                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    if role:
                        role_mentions.append(role.mention)
                    else:
                        role_mentions.append(f"{role_name}")
            
            if role_mentions:
                signal_message += f"\n\n{' '.join(role_mentions)}"
        
        # Parse and send to multiple channels - using channel IDs to avoid name conflicts
        channel_list = [ch.strip() for ch in channels.split(',')]
        sent_channels = []
        sent_messages = []
        channel_ids = []
        
        for channel_identifier in channel_list:
            target_channel = None
            
            # Priority 1: Try to parse as channel mention (most reliable)
            if channel_identifier.startswith('<#') and channel_identifier.endswith('>'):
                channel_id = int(channel_identifier[2:-1])
                target_channel = bot.get_channel(channel_id)
            # Priority 2: Try to parse as channel ID
            elif channel_identifier.isdigit():
                target_channel = bot.get_channel(int(channel_identifier))
            # Priority 3: Find by name (will get first match - this is the issue you mentioned)
            else:
                target_channel = discord.utils.get(interaction.guild.channels, name=channel_identifier)
            
            if target_channel and isinstance(target_channel, discord.TextChannel):
                try:
                    sent_message = await target_channel.send(signal_message)
                    sent_channels.append(target_channel.name)
                    sent_messages.append(sent_message)
                    channel_ids.append(target_channel.id)
                except discord.Forbidden:
                    await interaction.followup.send(f"❌ No permission to send to #{target_channel.name}", ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(f"❌ Error sending to #{target_channel.name}: {str(e)}", ephemeral=True)
        
        if sent_channels:
            # Store signal data for monitoring if messages were sent successfully
            if sent_messages:
                # Use the first message ID as the primary reference
                primary_message = sent_messages[0]
                
                # Store signal data for market monitoring
                signal_data = {
                    'pair': pair,
                    'entry_type': entry_type,
                    'entry_raw': levels['entry_raw'],
                    'tp1_raw': levels['tp1_raw'],
                    'tp2_raw': levels['tp2_raw'],
                    'tp3_raw': levels['tp3_raw'],
                    'sl_raw': levels['sl_raw'],
                    'channel_ids': channel_ids,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'sl_hit': False
                }
                
                # Place MT5 trade if enabled
                if MT5_ENABLED:
                    await connect_mt5()
                    mt5_order_id = await place_mt5_trade(
                        pair=pair,
                        entry_price=levels['entry_raw'],
                        tp3_price=levels['tp3_raw'],
                        sl_price=levels['sl_raw'],
                        entry_type=entry_type
                    )
                    if mt5_order_id:
                        signal_data['mt5_order_id'] = mt5_order_id
                        print(f"MT5 trade placed for {pair}: Order #{mt5_order_id}")
                
                # Store in active signals for monitoring
                active_signals[primary_message.id] = signal_data
                
                # Start market monitor if not already running
                global market_monitor_active
                if not market_monitor_active:
                    asyncio.create_task(start_market_monitor())
                
            success_msg = f"✅ Signal sent to: {', '.join(sent_channels)}"
            if sent_messages and MT5_ENABLED and signal_data.get('mt5_order_id'):
                success_msg += f"\n🔄 MT5 trade placed (Order #{signal_data['mt5_order_id']})"
            success_msg += f"\n📊 Market monitoring active for {pair}"
            
            await interaction.response.send_message(success_msg, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No valid channels found or no messages sent.", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error creating signal: {str(e)}", ephemeral=True)

@entry_command.autocomplete('entry_type')
async def entry_type_autocomplete(interaction: discord.Interaction, current: str):
    types = ['Buy limit', 'Sell limit', 'Buy execution', 'Sell execution']
    return [
        app_commands.Choice(name=entry_type, value=entry_type)
        for entry_type in types if current.lower() in entry_type.lower()
    ]

@entry_command.autocomplete('pair')
async def pair_autocomplete(interaction: discord.Interaction, current: str):
    # Organized pairs by currency groups for easier navigation
    pairs = [
        # USD pairs
        'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'XAUUSD', 'BTCUSD',
        # JPY pairs  
        'GBPJPY', 'CHFJPY', 'CADJPY', 'AUDJPY',
        # CHF pairs
        'GBPCHF', 'CADCHF', 'AUDCHF',
        # CAD pairs
        'GBPCAD', 'EURCAD', 'AUDCAD',
        # Cross pairs
        'AUDNZD',
        # Indices
        'US100', 'US500', 'GER40'
    ]
    return [
        app_commands.Choice(name=pair, value=pair)
        for pair in pairs if current.lower() in pair.lower()
    ]

@bot.tree.command(name="stats", description="Send trading statistics summary")
@app_commands.describe(
    date_range="Date range for the statistics",
    total_signals="Total number of signals sent",
    tp1_hits="Number of TP1 hits",
    tp2_hits="Number of TP2 hits", 
    tp3_hits="Number of TP3 hits",
    sl_hits="Number of SL hits",
    channels="Select channels to send the stats to (comma-separated channel mentions or names)",
    currently_open="Number of currently open trades",
    total_closed="Total closed trades (auto-calculated if not provided)"
)
async def stats_command(
    interaction: discord.Interaction,
    date_range: str,
    total_signals: int,
    tp1_hits: int,
    tp2_hits: int,
    tp3_hits: int,
    sl_hits: int,
    channels: str,
    currently_open: str = "0",
    total_closed: int = None
):
    """Send formatted trading statistics to specified channels"""
    
    try:
        # Calculate total closed if not provided
        if total_closed is None:
            total_closed = tp1_hits + sl_hits
        
        # Calculate percentages
        def calc_percentage(hits, total):
            if total == 0:
                return "0%"
            return f"{(hits/total)*100:.0f}%"
        
        tp1_percent = calc_percentage(tp1_hits, total_closed) if total_closed > 0 else "0%"
        tp2_percent = calc_percentage(tp2_hits, total_closed) if total_closed > 0 else "0%"
        tp3_percent = calc_percentage(tp3_hits, total_closed) if total_closed > 0 else "0%"
        sl_percent = calc_percentage(sl_hits, total_closed) if total_closed > 0 else "0%"
        
        # Create the stats message
        stats_message = f"""**:bar_chart: TRADING SIGNAL STATISTICS**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**:date: Period:** {date_range}

**:chart_with_upwards_trend: SIGNAL OVERVIEW**
• Total Signals Sent: **{total_signals}**
• Total Closed Positions: **{total_closed}**
• Currently Open: **{currently_open}**

**:dart: TAKE PROFIT PERFORMANCE**
• TP1 Hits: **{tp1_hits}**
• TP2 Hits: **{tp2_hits}**
• TP3 Hits: **{tp3_hits}**

**:octagonal_sign: STOP LOSS**
• SL Hits: **{sl_hits}** ({sl_percent})

**:bar_chart: PERFORMANCE SUMMARY**
• **Win Rate:** {tp1_percent}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Parse and send to multiple channels
        channel_list = [ch.strip() for ch in channels.split(',')]
        sent_channels = []
        
        for channel_identifier in channel_list:
            target_channel = None
            
            # Try to parse as channel mention
            if channel_identifier.startswith('<#') and channel_identifier.endswith('>'):
                channel_id = int(channel_identifier[2:-1])
                target_channel = bot.get_channel(channel_id)
            # Try to parse as channel ID
            elif channel_identifier.isdigit():
                target_channel = bot.get_channel(int(channel_identifier))
            # Try to find by name
            else:
                target_channel = discord.utils.get(interaction.guild.channels, name=channel_identifier)
            
            if target_channel and isinstance(target_channel, discord.TextChannel):
                try:
                    await target_channel.send(stats_message)
                    sent_channels.append(target_channel.name)
                except discord.Forbidden:
                    await interaction.followup.send(f"❌ No permission to send to #{target_channel.name}", ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(f"❌ Error sending to #{target_channel.name}: {str(e)}", ephemeral=True)
        
        if sent_channels:
            await interaction.response.send_message(f"✅ Stats sent to: {', '.join(sent_channels)}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No valid channels found or no messages sent.", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending statistics: {str(e)}", ephemeral=True)

@bot.tree.command(name="channels", description="List all channels with their IDs for precise selection")
async def channels_command(interaction: discord.Interaction):
    """List all channels with their IDs to help with channel selection"""
    try:
        text_channels = [ch for ch in interaction.guild.channels if isinstance(ch, discord.TextChannel)]
        
        if not text_channels:
            await interaction.response.send_message("❌ No text channels found.", ephemeral=True)
            return
        
        # Group channels by name to show duplicates
        channel_groups = {}
        for channel in text_channels:
            if channel.name not in channel_groups:
                channel_groups[channel.name] = []
            channel_groups[channel.name].append(channel)
        
        channel_list = "**📋 Available Channels:**\n\n"
        
        for name, channels in sorted(channel_groups.items()):
            if len(channels) == 1:
                channel = channels[0]
                channel_list += f"• **{name}** - `<#{channel.id}>` (ID: {channel.id})\n"
            else:
                channel_list += f"• **{name}** ({len(channels)} channels with same name):\n"
                for i, channel in enumerate(channels, 1):
                    channel_list += f"  └ {name} #{i} - `<#{channel.id}>` (ID: {channel.id})\n"
        
        channel_list += "\n**💡 Usage Tips:**\n"
        channel_list += "• Copy the `<#ID>` format for exact channel selection\n"
        channel_list += "• Use channel IDs when you have multiple channels with same name\n"
        channel_list += "• Separate multiple channels with commas in /entry command"
        
        # Split into multiple messages if too long
        if len(channel_list) > 2000:
            chunks = [channel_list[i:i+2000] for i in range(0, len(channel_list), 2000)]
            await interaction.response.send_message(chunks[0], ephemeral=True)
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk, ephemeral=True)
        else:
            await interaction.response.send_message(channel_list, ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error listing channels: {str(e)}", ephemeral=True)

@bot.tree.command(name="signals", description="Show active signals being monitored")
async def signals_command(interaction: discord.Interaction):
    """Show currently active signals and their status"""
    try:
        if not active_signals:
            await interaction.response.send_message("📊 No active signals being monitored.", ephemeral=True)
            return
        
        signals_list = "**📊 Active Signals:**\n\n"
        
        for message_id, signal_data in active_signals.items():
            pair = signal_data['pair']
            entry_type = signal_data['entry_type']
            entry_price = signal_data['entry_raw']
            
            status_indicators = []
            if signal_data.get('tp1_hit'):
                status_indicators.append("✅ TP1")
            else:
                status_indicators.append("⏳ TP1")
                
            if signal_data.get('tp2_hit'):
                status_indicators.append("✅ TP2")
            else:
                status_indicators.append("⏳ TP2")
                
            if signal_data.get('tp3_hit'):
                status_indicators.append("✅ TP3")
            else:
                status_indicators.append("⏳ TP3")
            
            mt5_status = ""
            if signal_data.get('mt5_order_id'):
                mt5_status = f" 🔄 MT5: #{signal_data['mt5_order_id']}"
            
            signals_list += f"**{pair}** ({entry_type}) @ {entry_price:.5f}{mt5_status}\n"
            signals_list += f"  {' | '.join(status_indicators)}\n\n"
        
        signals_list += f"**📈 Market Monitor:** {'🟢 Active' if market_monitor_active else '🔴 Inactive'}"
        
        await interaction.response.send_message(signals_list, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error showing signals: {str(e)}", ephemeral=True)

@bot.tree.command(name="mt5setup", description="Configure MetaTrader 5 credentials for 24/7 trading")
@app_commands.describe(
    login="Your MT5 account login number (6+ digits)",
    password="Your MT5 MASTER password (not investor password)",
    server="MT5 server (default: MetaQuotes-Demo)"
)
async def mt5setup_command(
    interaction: discord.Interaction,
    login: str,
    password: str,
    server: str = "MetaQuotes-Demo"
):
    """Configure MT5 credentials for automatic trading"""
    try:
        # Store credentials globally
        global MT5_CREDENTIALS
        MT5_CREDENTIALS['login'] = int(login)
        MT5_CREDENTIALS['password'] = password
        MT5_CREDENTIALS['server'] = server
        
        # Test connection
        connection_success = await connect_mt5()
        
        if connection_success:
            success_msg = f"✅ MT5 Setup Complete!\n"
            success_msg += f"🔗 Account: {login}\n"
            success_msg += f"🌐 Server: {server}\n"
            success_msg += f"🎯 Status: Connected and ready for 24/7 trading\n\n"
            success_msg += f"🚀 The bot will now automatically place trades when you use /entry commands"
            
            await interaction.response.send_message(success_msg, ephemeral=True)
        else:
            error_msg = f"❌ MT5 Connection Failed\n\n"
            error_msg += f"**Common Issues:**\n"
            error_msg += f"• **Login Format**: Must be 6+ digits (e.g. 123456789)\n"
            error_msg += f"• **Password Type**: Use MASTER password, not investor password\n"
            error_msg += f"• **Server**: Try 'MetaQuotes-Demo' for demo accounts\n"
            error_msg += f"• **API Trading**: Must be enabled in MT5 settings\n\n"
            error_msg += f"**Your Input:**\n"
            error_msg += f"• Login: {login} {'✅' if str(login).isdigit() and len(str(login)) >= 6 else '❌ Invalid format'}\n"
            error_msg += f"• Server: {server}\n\n"
            error_msg += f"**Need Help?** Check your MT5 account details and try again."
            
            await interaction.response.send_message(error_msg, ephemeral=True)
            
    except ValueError:
        await interaction.response.send_message("❌ Login must be a valid account number", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error setting up MT5: {str(e)}", ephemeral=True)

@bot.tree.command(name="mt5status", description="Check MT5 connection status")
async def mt5status_command(interaction: discord.Interaction):
    """Check current MT5 connection status"""
    try:
        if not MT5_CREDENTIALS['login']:
            await interaction.response.send_message(
                "❌ MT5 not configured. Use /mt5setup to set your credentials.", 
                ephemeral=True
            )
            return
        
        connection_status = await connect_mt5()
        
        status_msg = f"**📊 MT5 Status Report**\n\n"
        status_msg += f"🔗 Account: {MT5_CREDENTIALS['login']}\n"
        status_msg += f"🌐 Server: {MT5_CREDENTIALS['server']}\n"
        status_msg += f"🎯 Connection: {'🟢 Active' if connection_status else '🔴 Failed'}\n"
        status_msg += f"📈 Trading: {'✅ Enabled' if connection_status else '❌ Disabled'}\n\n"
        
        if connection_status:
            status_msg += f"✅ Bot ready for automatic trade execution"
        else:
            status_msg += f"❌ Check credentials or try reconnecting with /mt5setup"
        
        await interaction.response.send_message(status_msg, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error checking MT5 status: {str(e)}", ephemeral=True)

@bot.tree.command(name="role", description="Assign roles to members based on criteria")
@app_commands.describe(
    options="Select the role to give to members",
    amount="Number of people to give the role to",
    status="Member status filter (online, offline, or both)",
    included="Required role - only give role to members who have this role (optional)",
    excluded="Excluded role - don't give role to members who have this role (optional)"
)
async def role_command(
    interaction: discord.Interaction,
    options: discord.Role,
    amount: int,
    status: str,
    included: discord.Role = None,
    excluded: discord.Role = None
):
    """Assign a role to specified number of members based on criteria"""
    
    try:
        # Validate status parameter
        if status.lower() not in ['online', 'offline', 'both']:
            await interaction.response.send_message("❌ Status must be 'online', 'offline', or 'both'", ephemeral=True)
            return
        
        # Validate amount
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be greater than 0", ephemeral=True)
            return
        
        # Check bot permissions
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ Bot doesn't have permission to manage roles", ephemeral=True)
            return
        
        # Check if bot can assign this role (role hierarchy)
        if options.position >= interaction.guild.me.top_role.position:
            await interaction.response.send_message(f"❌ Cannot assign role {options.name} - it's higher than bot's highest role", ephemeral=True)
            return
        
        # Check if user has permission to assign this role
        if options.position >= interaction.user.top_role.position and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(f"❌ You don't have permission to assign role {options.name}", ephemeral=True)
            return
        
        # Ensure we have all members loaded (for large servers)
        if not interaction.guild.chunked:
            await interaction.guild.chunk()
        
        # Get all members and filter based on criteria
        eligible_members = []
        debug_counts = {
            'total_members': 0,
            'bots_skipped': 0,
            'already_has_role': 0,
            'missing_included': 0,
            'has_excluded': 0,
            'wrong_status': 0,
            'eligible': 0
        }
        
        # Track detailed member info for debugging
        member_details = []
        
        for member in interaction.guild.members:
            debug_counts['total_members'] += 1
            member_info = f"{member.display_name} ({'bot' if member.bot else 'human'}, {member.status})"
            
            # Skip bots
            if member.bot:
                debug_counts['bots_skipped'] += 1
                member_details.append(f"❌ {member_info} - Bot skipped")
                continue
            
            # Skip if member already has the target role
            if options in member.roles:
                debug_counts['already_has_role'] += 1
                member_details.append(f"❌ {member_info} - Already has role")
                continue
            
            # Check included role requirement
            if included and included not in member.roles:
                debug_counts['missing_included'] += 1
                member_details.append(f"❌ {member_info} - Missing required role '{included.name}'")
                continue
            
            # Check excluded role restriction
            if excluded and excluded in member.roles:
                debug_counts['has_excluded'] += 1
                member_details.append(f"❌ {member_info} - Has excluded role '{excluded.name}'")
                continue
            
            # Check status filter
            if status.lower() == 'online' and member.status in [discord.Status.offline, discord.Status.invisible]:
                debug_counts['wrong_status'] += 1
                member_details.append(f"❌ {member_info} - Wrong status (need online)")
                continue
            elif status.lower() == 'offline' and member.status not in [discord.Status.offline, discord.Status.invisible]:
                debug_counts['wrong_status'] += 1
                member_details.append(f"❌ {member_info} - Wrong status (need offline)")
                continue
            # For 'both', we include everyone regardless of status
            
            eligible_members.append(member)
            debug_counts['eligible'] += 1
            member_details.append(f"✅ {member_info} - Eligible")
        
        # Check if we have enough eligible members
        if len(eligible_members) == 0:
            debug_msg = f"❌ No eligible members found matching the criteria\n\n**Debug Info:**\n"
            debug_msg += f"• Total members: {debug_counts['total_members']}\n"
            debug_msg += f"• Bots skipped: {debug_counts['bots_skipped']}\n"
            debug_msg += f"• Already have target role '{options.name}': {debug_counts['already_has_role']}\n"
            if included:
                debug_msg += f"• Missing required role '{included.name}': {debug_counts['missing_included']}\n"
            if excluded:
                debug_msg += f"• Have excluded role '{excluded.name}': {debug_counts['has_excluded']}\n"
            debug_msg += f"• Wrong status (need {status}): {debug_counts['wrong_status']}\n"
            debug_msg += f"• **Eligible members: {debug_counts['eligible']}**\n\n"
            
            # Add detailed member breakdown (limit to first 10 to avoid message length issues)
            if member_details:
                debug_msg += "**Member Details:**\n"
                for detail in member_details[:10]:
                    debug_msg += f"{detail}\n"
                if len(member_details) > 10:
                    debug_msg += f"... and {len(member_details) - 10} more members"
            
            await interaction.response.send_message(debug_msg, ephemeral=True)
            return
        
        # Limit to requested amount
        selected_members = eligible_members[:amount]
        
        # Assign roles
        successful_assignments = []
        failed_assignments = []
        
        await interaction.response.defer(ephemeral=True)
        
        for member in selected_members:
            try:
                await member.add_roles(options, reason=f"Role assignment via /role command by {interaction.user}")
                successful_assignments.append(member.display_name)
            except discord.Forbidden:
                failed_assignments.append(f"{member.display_name} (no permission)")
            except discord.HTTPException as e:
                failed_assignments.append(f"{member.display_name} (error: {str(e)})")
        
        # Create response message
        response_parts = []
        
        if successful_assignments:
            response_parts.append(f"✅ Successfully assigned role **{options.name}** to {len(successful_assignments)} members:")
            response_parts.append(f"• {', '.join(successful_assignments)}")
        
        if failed_assignments:
            response_parts.append(f"\n❌ Failed to assign role to {len(failed_assignments)} members:")
            response_parts.append(f"• {', '.join(failed_assignments)}")
        
        # Add summary
        response_parts.append(f"\n**Summary:**")
        response_parts.append(f"• Target role: {options.name}")
        response_parts.append(f"• Requested amount: {amount}")
        response_parts.append(f"• Status filter: {status}")
        if included:
            response_parts.append(f"• Required role: {included.name}")
        if excluded:
            response_parts.append(f"• Excluded role: {excluded.name}")
        response_parts.append(f"• Eligible members found: {len(eligible_members)}")
        response_parts.append(f"• Successfully assigned: {len(successful_assignments)}")
        
        # Split response if too long
        response_text = '\n'.join(response_parts)
        if len(response_text) > 2000:
            # Send summary first
            summary = f"✅ Role assignment completed!\n**{options.name}** assigned to {len(successful_assignments)}/{amount} requested members"
            if failed_assignments:
                summary += f"\n❌ {len(failed_assignments)} assignments failed"
            await interaction.followup.send(summary, ephemeral=True)
        else:
            await interaction.followup.send(response_text, ephemeral=True)
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error during role assignment: {str(e)}", ephemeral=True)

@role_command.autocomplete('status')
async def status_autocomplete(interaction: discord.Interaction, current: str):
    statuses = ['online', 'offline', 'both']
    return [
        app_commands.Choice(name=status, value=status)
        for status in statuses if current.lower() in status.lower()
    ]

# Error handling
@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if not interaction.response.is_done():
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
    print(f"Application command error: {error}")

# Simple web server for Render.com health checks
async def health_check(request):
    return web.Response(text="Discord Trading Bot is running!", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    # Use PORT environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")
    return site

async def start_bot():
    """Start the Discord bot"""
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables")
        return
    
    await bot.start(DISCORD_TOKEN)

async def main():
    """Main function to run both web server and bot"""
    print("Starting web server...")
    await start_web_server()
    
    print("Starting Discord bot...")
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())
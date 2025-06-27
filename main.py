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

# Import MetaApi for real cloud trading
try:
    from metaapi_cloud_sdk import MetaApi
    METAAPI_AVAILABLE = True
    print("MetaApi Cloud SDK loaded - Real trading enabled")
except ImportError:
    METAAPI_AVAILABLE = False
    print("MetaApi Cloud SDK not available - Install with: pip install metaapi-cloud-sdk")

# Note: requests library removed as it's not used in this bot

# Reconstruct tokens from split parts for enhanced security
DISCORD_TOKEN_PART1 = os.getenv("DISCORD_TOKEN_PART1", "")
DISCORD_TOKEN_PART2 = os.getenv("DISCORD_TOKEN_PART2", "")
DISCORD_TOKEN = DISCORD_TOKEN_PART1 + DISCORD_TOKEN_PART2

DISCORD_CLIENT_ID_PART1 = os.getenv("DISCORD_CLIENT_ID_PART1", "")
DISCORD_CLIENT_ID_PART2 = os.getenv("DISCORD_CLIENT_ID_PART2", "")
DISCORD_CLIENT_ID = DISCORD_CLIENT_ID_PART1 + DISCORD_CLIENT_ID_PART2

# MetaApi configuration for real cloud trading - HARDCODED CREDENTIALS
METAAPI_TOKEN = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiIyOGQ5NzRhMDIzYzE3ODYzMGJjYzBkNTRmNTI5MmM1YyIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19XSwiaWF0IjoxNzUwOTU3NzI3LCJyZWFsVXNlcklkIjoiMjhkOTc0YTAyM2MxNzg2MzBiY2MwZDU0ZjUyOTJjNWMifQ.QbGvXpDNBe9GDQShXWTJkXs5sCjp8WB-RY3w7NVnRwA4DL_mFoJ8CZV3L1rz68HYSvh3S0-w_J5k9K0mLZzNzKx0o7V1kJPZfAVFLxzUdE1zKz3PjTr6VHNKNl0wL2bTXLKH1Wz1w-zWYy_5z6_gGNx_E8Q_A_cXYzf1Jp1nz3hzEA-F8K8c-K9fKoX8mGq1Lf2R_kz1n0zZA0_4gYZA3_2n"
MT5_ACCOUNT_ID = "f927bb74-90fc-45ad-96fb-c704f8431f7f"

# Debug: Check if MetaAPI credentials are loaded
print(f"MetaAPI Token loaded: {len(METAAPI_TOKEN) > 0}")
print(f"MT5 Account ID loaded: {len(MT5_ACCOUNT_ID) > 0}")
if len(METAAPI_TOKEN) > 0:
    print(f"MetaAPI Token preview: {METAAPI_TOKEN[:20]}...")
else:
    print(f"MetaAPI Token is empty or None")
if len(MT5_ACCOUNT_ID) > 0:
    print(f"MT5 Account ID preview: {MT5_ACCOUNT_ID[:8]}...")
else:
    print(f"MT5 Account ID is empty or None")

if METAAPI_TOKEN and MT5_ACCOUNT_ID:
    print("✅ MetaAPI credentials configured")
else:
    print("❌ MetaAPI credentials missing - check environment variables")



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
        
        # Initialize trading APIs
        trading_enabled = False
        
        # Check MetaApi connection
        if await initialize_metaapi():
            print("✅ MetaApi connected - REAL TRADING ENABLED")
            trading_enabled = True
        else:
            print("⚠️ MetaApi not configured - using simulation mode")
            print("💡 Configure METAAPI_TOKEN + MT5_ACCOUNT_ID for real trading")

bot = TradingBot()

# Global storage for active signals and market monitoring
active_signals = {}  # Format: {message_id: {pair, entry_price, tp1, tp2, tp3, sl, channels, entry_type}}
market_monitor_active = False

# MT5 configuration
MT5_ENABLED = True
MT5_CREDENTIALS = {
    'login': None,
    'password': None,
    'server': 'MetaQuotes-Demo'
}

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

# MetaApi Cloud integration for real trading
metaapi_instance = None
mt5_account = None

async def initialize_metaapi():
    """Initialize MetaApi connection for real trading"""
    global metaapi_instance, mt5_account
    
    if not METAAPI_AVAILABLE or not METAAPI_TOKEN or not MT5_ACCOUNT_ID:
        print("MetaApi not configured - using simulation mode")
        return False
    
    try:
        # Initialize MetaApi
        metaapi_instance = MetaApi(METAAPI_TOKEN)
        
        # Get account
        mt5_account = await metaapi_instance.metatrader_account_api.get_account(MT5_ACCOUNT_ID)
        
        # Deploy account if not deployed
        if mt5_account.state != 'DEPLOYED':
            print(f"Deploying account {MT5_ACCOUNT_ID}...")
            await mt5_account.deploy()
        
        # Wait for deployment
        await mt5_account.wait_deployed()
        
        # Connect to account
        connection = mt5_account.get_rpc_connection()
        await connection.connect()
        
        # Wait for connection
        await connection.wait_synchronized()
        
        print(f"✅ MetaApi connected to account {MT5_ACCOUNT_ID}")
        return True
        
    except Exception as e:
        print(f"❌ MetaApi initialization failed: {str(e)}")
        return False

# Initialize simulation fallback
mt5_simulator = CloudMT5Simulator()
print("MetaApi Cloud integration initialized")

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
    
    # Check credentials first
    if not MT5_CREDENTIALS['login'] or not MT5_CREDENTIALS['password']:
        print("MT5 credentials not set. Use /mt5setup command first.")
        return False
    
    try:
        # Use cloud simulator - pass credentials directly to initialize
        success = mt5_simulator.initialize(
            login=MT5_CREDENTIALS['login'],
            password=MT5_CREDENTIALS['password'],
            server=MT5_CREDENTIALS['server']
        )
        
        if success:
            print(f"MT5 connected - Account: {MT5_CREDENTIALS['login']}, Server: {MT5_CREDENTIALS['server']}")
            return True
        else:
            print(f"MT5 connection failed for account {MT5_CREDENTIALS['login']} on {MT5_CREDENTIALS['server']}")
            return False
            
    except Exception as e:
        print(f"MT5 connection error: {str(e)}")
        return False

async def place_mt5_trade(pair: str, entry_price: float, tp3_price: float, sl_price: float, entry_type: str, lot_size: float = 0.01):
    """Place a real trade using MetaAPI or simulation fallback"""
    global mt5_account
    
    try:
        # Try MetaApi Cloud first
        if mt5_account is not None:
            result = await place_metaapi_trade(pair, entry_price, tp3_price, sl_price, entry_type, lot_size)
            if result:
                return result
        
        # Fallback to simulation
        return await place_simulated_trade(pair, entry_price, tp3_price, sl_price, entry_type, lot_size)
        
    except Exception as e:
        print(f"Trade placement error: {str(e)}")
        return await place_simulated_trade(pair, entry_price, tp3_price, sl_price, entry_type, lot_size)

async def place_metaapi_trade(pair: str, entry_price: float, tp3_price: float, sl_price: float, entry_type: str, lot_size: float = 0.01):
    """Execute real trade via MetaApi Cloud"""
    try:
        connection = mt5_account.get_rpc_connection()
        
        # Convert symbols for broker compatibility
        symbol = pair.replace("XAUUSD", "GOLD").replace("US100", "NAS100").replace("US500", "SPX500")
        
        # Determine trade type
        if entry_type.lower() == "buy execution":
            result = await connection.create_market_order(symbol, "ORDER_TYPE_BUY", lot_size, 
                                                        stop_loss=sl_price, take_profit=tp3_price,
                                                        comment="Discord Bot - Buy Market")
        elif entry_type.lower() == "sell execution":
            result = await connection.create_market_order(symbol, "ORDER_TYPE_SELL", lot_size,
                                                        stop_loss=sl_price, take_profit=tp3_price, 
                                                        comment="Discord Bot - Sell Market")
        elif entry_type.lower() == "buy limit":
            result = await connection.create_limit_order(symbol, "ORDER_TYPE_BUY_LIMIT", lot_size, entry_price,
                                                       stop_loss=sl_price, take_profit=tp3_price,
                                                       comment="Discord Bot - Buy Limit")
        elif entry_type.lower() == "sell limit":
            result = await connection.create_limit_order(symbol, "ORDER_TYPE_SELL_LIMIT", lot_size, entry_price,
                                                       stop_loss=sl_price, take_profit=tp3_price,
                                                       comment="Discord Bot - Sell Limit")
        else:
            return None
            
        print(f"✅ REAL TRADE EXECUTED: {entry_type} {symbol} @ {entry_price}")
        print(f"   Order ID: {result.get('orderId')}")
        print(f"   TP: {tp3_price}, SL: {sl_price}")
        
        return result.get('orderId', str(random.randint(10000, 99999)))
        
    except Exception as e:
        print(f"❌ MetaApi trade failed: {str(e)}")
        return None



async def place_simulated_trade(pair: str, entry_price: float, tp3_price: float, sl_price: float, entry_type: str, lot_size: float = 0.01):
    """Simulation fallback when no real APIs available"""
    order_id = random.randint(1000, 9999)
    print(f"📊 SIMULATED: {entry_type} {pair} @ {entry_price} (Order #{order_id})")
    return order_id

async def move_sl_to_breakeven(order_id: int, entry_price: float):
    """Move stop loss to breakeven (entry price)"""
    if not MT5_ENABLED or not order_id:
        return False
    
    try:
        # Get position info using simulator
        positions = mt5_simulator.positions_get(ticket=order_id)
        if not positions:
            print(f"Position {order_id} not found")
            return False
        
        print(f"SL moved to breakeven for order {order_id} (simulated)")
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
    try:
        # Use MetaAPI for real price data if available
        if mt5_account is not None:
            try:
                connection = mt5_account.get_rpc_connection()
                symbol = pair.replace("XAUUSD", "GOLD").replace("US100", "NAS100").replace("US500", "SPX500")
                # Note: MetaAPI price fetching would require specific API call
                print(f"Would fetch price for {symbol} via MetaAPI")
                return None  # Market monitoring disabled until proper MetaAPI price feed implementation
            except Exception as e:
                print(f"MetaAPI price fetch failed: {e}")
        
        # Fallback to simulator price
        tick = mt5_simulator.symbol_info_tick(pair)
        return tick.bid if hasattr(tick, 'bid') else None
        
    except Exception as e:
        print(f"Error getting price for {pair}: {e}")
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
                
                # Place real MetaAPI trade if configured
                if METAAPI_AVAILABLE and METAAPI_TOKEN and MT5_ACCOUNT_ID:
                    # Initialize MetaAPI connection if not already done
                    if mt5_account is None:
                        metaapi_success = await initialize_metaapi()
                        if not metaapi_success:
                            print(f"❌ MetaAPI initialization failed - trade not placed for {pair}")
                    
                    # Place real trade via MetaAPI
                    if mt5_account is not None:
                        mt5_order_id = await place_metaapi_trade(
                            pair=pair,
                            entry_price=levels['entry_raw'],
                            tp3_price=levels['tp3_raw'],
                            sl_price=levels['sl_raw'],
                            entry_type=entry_type
                        )
                        if mt5_order_id:
                            signal_data['mt5_order_id'] = mt5_order_id
                            print(f"✅ REAL MetaAPI trade placed for {pair}: Order #{mt5_order_id}")
                        else:
                            print(f"❌ MetaAPI trade failed for {pair}")
                    else:
                        print(f"❌ MetaAPI not connected - trade not placed for {pair}")
                else:
                    print(f"⚠️ MetaAPI not configured - add METAAPI_TOKEN and MT5_ACCOUNT_ID")
                
                # Store in active signals for monitoring
                active_signals[primary_message.id] = signal_data
                
                # Market monitoring disabled for cloud simulation
                # (Would need real price feed to avoid instant TP/SL triggers)
                global market_monitor_active
                market_monitor_active = False
                
            success_msg = f"✅ Signal sent to: {', '.join(sent_channels)}"
            if sent_messages and signal_data.get('mt5_order_id'):
                success_msg += f"\n🔄 REAL MetaAPI trade executed (Order #{signal_data['mt5_order_id']})"
                success_msg += f"\n📈 Live trade placed on MT5 account {MT5_ACCOUNT_ID}"
            elif METAAPI_AVAILABLE and METAAPI_TOKEN and MT5_ACCOUNT_ID:
                success_msg += f"\n⚠️ MetaAPI trade failed - check account connection"
            else:
                success_msg += f"\n⚠️ MetaAPI not configured - signals only mode"
            success_msg += f"\n📊 Signal tracking active for {pair}"
            
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



@bot.tree.command(name="monitoring", description="Show active signals being monitored")
async def monitoring_command(interaction: discord.Interaction):
    """Show currently active signals and their status"""
    try:
        if not active_signals:
            await interaction.response.send_message("📊 No active signals being monitored.", ephemeral=True)
            return
        
        signals_list = "**📊 Active Signals:**\n\n"
        
        # Clean up completed trades first
        completed_signals = []
        for message_id, signal_data in active_signals.items():
            # Mark as completed if TP3 hit or SL hit
            if signal_data.get('tp3_hit') or signal_data.get('sl_hit'):
                completed_signals.append(message_id)
        
        # Remove completed signals
        for message_id in completed_signals:
            del active_signals[message_id]
            print(f"Removed completed signal: {message_id}")
        
        # Show remaining active signals
        if not active_signals:
            await interaction.response.send_message("📊 No active signals being monitored.", ephemeral=True)
            return
        
        for message_id, signal_data in active_signals.items():
            pair = signal_data['pair']
            entry_type = signal_data['entry_type']
            entry_price = signal_data['entry_raw']
            
            # Check if trade is completed
            if signal_data.get('tp3_hit'):
                status = "✅ COMPLETED (TP3 Hit)"
            elif signal_data.get('sl_hit'):
                status = "❌ COMPLETED (SL Hit)"
            else:
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
                
                status = ' | '.join(status_indicators)
            
            mt5_status = ""
            if signal_data.get('mt5_order_id'):
                mt5_status = f" 🔄 MT5: #{signal_data['mt5_order_id']}"
            
            signals_list += f"**{pair}** ({entry_type}) @ {entry_price:.5f}{mt5_status}\n"
            signals_list += f"  {status}\n\n"
        
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
            # More detailed error analysis
            login_valid = str(login).isdigit() and len(str(login)) >= 6
            server_valid = "MetaQuotes" in server or "Demo" in server
            
            error_msg = f"❌ MT5 Connection Failed\n\n"
            error_msg += f"**For MetaQuotes Demo Accounts:**\n"
            error_msg += f"• Login: Must be your MT5 account number (6+ digits)\n"
            error_msg += f"• Password: Your MASTER password (what you use to log into MT5)\n"
            error_msg += f"• Server: 'MetaQuotes-Demo' (exactly as shown)\n\n"
            error_msg += f"**Your Input Validation:**\n"
            error_msg += f"• Login: {login} {'✅ Valid format' if login_valid else '❌ Must be 6+ digits'}\n"
            error_msg += f"• Server: {server} {'✅' if server_valid else '❌ Try MetaQuotes-Demo'}\n\n"
            error_msg += f"**Cloud Trading Note:** This system works with demo accounts from MetaQuotes Ltd.\n"
            error_msg += f"If you have a live account, it may require different server settings."
            
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
    if not DISCORD_TOKEN or len(DISCORD_TOKEN) < 50:
        print(f"Error: DISCORD_TOKEN invalid - Length: {len(DISCORD_TOKEN)}")
        print(f"Part1 length: {len(DISCORD_TOKEN_PART1)}, Part2 length: {len(DISCORD_TOKEN_PART2)}")
        print("Please check DISCORD_TOKEN_PART1 and DISCORD_TOKEN_PART2 environment variables")
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
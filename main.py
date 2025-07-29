import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web
import json
from datetime import datetime, timedelta

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
intents.members = True  # Required for member join events

# Auto-role system storage
AUTO_ROLE_CONFIG = {
    "enabled": False,
    "role_id": None,
    "duration_hours": 24,
    "custom_message": "Your 1-day free trial has ended. Thank you for trying our service!",
    "active_members": {}  # member_id: {"role_added_time": datetime, "role_id": role_id}
}

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
        
        # Start the role removal task
        if not self.role_removal_task.is_running():
            self.role_removal_task.start()
        
        # Load auto-role config if it exists
        await self.load_auto_role_config()

    async def on_member_join(self, member):
        """Handle new member joins and assign auto-role if enabled"""
        if not AUTO_ROLE_CONFIG["enabled"] or not AUTO_ROLE_CONFIG["role_id"]:
            return
        
        try:
            role = member.guild.get_role(AUTO_ROLE_CONFIG["role_id"])
            if not role:
                print(f"❌ Auto-role not found in guild {member.guild.name}")
                return
            
            # Add the role to the new member
            await member.add_roles(role, reason="Auto-role for new member")
            
            # Record the member for role removal tracking
            AUTO_ROLE_CONFIG["active_members"][str(member.id)] = {
                "role_added_time": datetime.now().isoformat(),
                "role_id": AUTO_ROLE_CONFIG["role_id"],
                "guild_id": member.guild.id
            }
            
            # Save the updated config
            await self.save_auto_role_config()
            
            print(f"✅ Auto-role '{role.name}' added to {member.display_name} ({member.id})")
            
        except discord.Forbidden:
            print(f"❌ No permission to assign role to {member.display_name}")
        except Exception as e:
            print(f"❌ Error assigning auto-role to {member.display_name}: {str(e)}")

    async def load_auto_role_config(self):
        """Load auto-role configuration from file if it exists"""
        try:
            if os.path.exists("auto_role_config.json"):
                with open("auto_role_config.json", "r") as f:
                    loaded_config = json.load(f)
                    AUTO_ROLE_CONFIG.update(loaded_config)
                print("✅ Auto-role configuration loaded")
        except Exception as e:
            print(f"⚠️ Error loading auto-role config: {str(e)}")

    async def save_auto_role_config(self):
        """Save auto-role configuration to file"""
        try:
            with open("auto_role_config.json", "w") as f:
                json.dump(AUTO_ROLE_CONFIG, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving auto-role config: {str(e)}")

    @tasks.loop(minutes=30)  # Check every 30 minutes
    async def role_removal_task(self):
        """Background task to remove expired roles and send DMs"""
        if not AUTO_ROLE_CONFIG["enabled"] or not AUTO_ROLE_CONFIG["active_members"]:
            return
        
        current_time = datetime.now()
        expired_members = []
        
        for member_id, data in AUTO_ROLE_CONFIG["active_members"].items():
            try:
                # Parse the stored datetime
                role_added_time = datetime.fromisoformat(data["role_added_time"])
                duration = timedelta(hours=AUTO_ROLE_CONFIG["duration_hours"])
                
                if current_time >= role_added_time + duration:
                    expired_members.append(member_id)
            except Exception as e:
                print(f"❌ Error processing member {member_id}: {str(e)}")
                expired_members.append(member_id)  # Remove corrupted entries
        
        # Process expired members
        for member_id in expired_members:
            await self.remove_expired_role(member_id)
        
        # Save updated config if there were changes
        if expired_members:
            await self.save_auto_role_config()

    async def remove_expired_role(self, member_id):
        """Remove expired role from member and send DM"""
        try:
            data = AUTO_ROLE_CONFIG["active_members"].get(member_id)
            if not data:
                return
            
            # Get the guild and member
            guild = self.get_guild(data["guild_id"])
            if not guild:
                print(f"❌ Guild not found for member {member_id}")
                del AUTO_ROLE_CONFIG["active_members"][member_id]
                return
            
            member = guild.get_member(int(member_id))
            if not member:
                print(f"❌ Member {member_id} not found in guild")
                del AUTO_ROLE_CONFIG["active_members"][member_id]
                return
            
            # Get the role
            role = guild.get_role(data["role_id"])
            if role and role in member.roles:
                await member.remove_roles(role, reason="Auto-role expired")
                print(f"✅ Removed expired role '{role.name}' from {member.display_name}")
            
            # Send DM to the member
            try:
                await member.send(AUTO_ROLE_CONFIG["custom_message"])
                print(f"✅ Sent expiration DM to {member.display_name}")
            except discord.Forbidden:
                print(f"⚠️ Could not send DM to {member.display_name} (DMs disabled)")
            except Exception as e:
                print(f"❌ Error sending DM to {member.display_name}: {str(e)}")
            
            # Remove from active tracking
            del AUTO_ROLE_CONFIG["active_members"][member_id]
            
        except Exception as e:
            print(f"❌ Error removing expired role for member {member_id}: {str(e)}")
            # Clean up corrupted entry
            if member_id in AUTO_ROLE_CONFIG["active_members"]:
                del AUTO_ROLE_CONFIG["active_members"][member_id]

bot = TradingBot()

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
        'entry': format_price(entry_price)
    }

@bot.tree.command(name="timedautorole", description="Configure timed auto-role for new members")
@app_commands.describe(
    action="Enable/disable or check status of auto-role system",
    role="Role to assign to new members (required when enabling)",
    duration_hours="Duration in hours to keep the role (default: 24)",
    custom_message="Custom message to send when role expires"
)
async def timed_auto_role_command(
    interaction: discord.Interaction,
    action: str,
    role: discord.Role | None = None,
    duration_hours: int = 24,
    custom_message: str | None = None
):
    """Configure the timed auto-role system"""
    
    # Check permissions
    if not hasattr(interaction.user, 'guild_permissions') or not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    try:
        if action.lower() == "enable":
            if not role:
                await interaction.response.send_message("❌ You must specify a role when enabling auto-role.", ephemeral=True)
                return
            
            # Check if bot has permission to manage the role
            if interaction.guild and interaction.guild.me and role >= interaction.guild.me.top_role:
                await interaction.response.send_message(f"❌ I cannot manage the role '{role.name}' because it's higher than my highest role.", ephemeral=True)
                return
            
            # Update configuration
            AUTO_ROLE_CONFIG["enabled"] = True
            AUTO_ROLE_CONFIG["role_id"] = role.id
            AUTO_ROLE_CONFIG["duration_hours"] = duration_hours
            if custom_message:
                AUTO_ROLE_CONFIG["custom_message"] = custom_message
            
            # Save configuration
            await bot.save_auto_role_config()
            
            await interaction.response.send_message(
                f"✅ **Auto-role system enabled!**\n"
                f"• **Role:** {role.mention}\n"
                f"• **Duration:** {duration_hours} hours\n"
                f"• **Expiration message:** {AUTO_ROLE_CONFIG['custom_message']}\n\n"
                f"New members will automatically receive this role for {duration_hours} hours.",
                ephemeral=True
            )
            
        elif action.lower() == "disable":
            AUTO_ROLE_CONFIG["enabled"] = False
            await bot.save_auto_role_config()
            
            await interaction.response.send_message("✅ Auto-role system disabled. No new roles will be assigned to new members.", ephemeral=True)
            
        elif action.lower() == "status":
            if AUTO_ROLE_CONFIG["enabled"]:
                role = interaction.guild.get_role(AUTO_ROLE_CONFIG["role_id"]) if interaction.guild and AUTO_ROLE_CONFIG["role_id"] else None
                active_count = len(AUTO_ROLE_CONFIG["active_members"])
                
                status_message = f"✅ **Auto-role system is ENABLED**\n"
                if role:
                    status_message += f"• **Role:** {role.mention}\n"
                else:
                    status_message += f"• **Role:** Not found (ID: {AUTO_ROLE_CONFIG['role_id']})\n"
                status_message += f"• **Duration:** {AUTO_ROLE_CONFIG['duration_hours']} hours\n"
                status_message += f"• **Active members:** {active_count}\n"
                status_message += f"• **Expiration message:** {AUTO_ROLE_CONFIG['custom_message']}"
            else:
                status_message = "❌ **Auto-role system is DISABLED**"
            
            await interaction.response.send_message(status_message, ephemeral=True)
            
        else:
            await interaction.response.send_message("❌ Invalid action. Use 'enable', 'disable', or 'status'.", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error configuring auto-role: {str(e)}", ephemeral=True)

@timed_auto_role_command.autocomplete('action')
async def action_autocomplete(interaction: discord.Interaction, current: str):
    actions = ['enable', 'disable', 'status']
    return [
        app_commands.Choice(name=action, value=action)
        for action in actions if current.lower() in action.lower()
    ]

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
                    role = discord.utils.get(interaction.guild.roles, name=role_name) if interaction.guild else None
                    if role:
                        role_mentions.append(role.mention)
                    else:
                        role_mentions.append(f"{role_name}")
            
            if role_mentions:
                signal_message += f"\n\n{' '.join(role_mentions)}"
        
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
                target_channel = discord.utils.get(interaction.guild.channels, name=channel_identifier) if interaction.guild else None
            
            if target_channel and isinstance(target_channel, discord.TextChannel):
                try:
                    await target_channel.send(signal_message)
                    sent_channels.append(target_channel.name)
                except discord.Forbidden:
                    await interaction.followup.send(f"❌ No permission to send to #{target_channel.name}", ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(f"❌ Error sending to #{target_channel.name}: {str(e)}", ephemeral=True)
        
        if sent_channels:
            await interaction.response.send_message(f"✅ Signal sent to: {', '.join(sent_channels)}", ephemeral=True)
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
                target_channel = discord.utils.get(interaction.guild.channels, name=channel_identifier) if interaction.guild else None
            
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

async def start_bot():
    if not DISCORD_TOKEN:
        print("❌ Discord token not found. Please check your environment variables.")
        return
    
    try:
        await bot.start(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Invalid Discord token. Please check your token parts in environment variables.")
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")

async def main():
    # Start web server first (required for Render.com)
    print("Starting web server...")
    web_task = asyncio.create_task(start_web_server())
    
    # Wait a moment for web server to initialize
    await asyncio.sleep(1)
    
    # Start Discord bot (don't let it crash the web server)
    print("Starting Discord bot...")
    bot_task = asyncio.create_task(start_bot())
    
    # Keep both running, but prioritize web server for Render
    try:
        await asyncio.gather(web_task, bot_task, return_exceptions=True)
    except Exception as e:
        print(f"Error in main: {e}")
        # Keep web server running even if bot fails
        await web_task

# Run the bot
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
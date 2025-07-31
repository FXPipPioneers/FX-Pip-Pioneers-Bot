import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web
import json
from datetime import datetime, timedelta, timezone

# Telegram integration
try:
    from pyrogram.client import Client
    from pyrogram import filters
    from pyrogram.types import Message
    TELEGRAM_AVAILABLE = True
    print("Pyrogram loaded - Telegram integration enabled")
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Pyrogram not available - Install with: pip install pyrogram tgcrypto")

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

# Auto-role system storage with weekend handling
AUTO_ROLE_CONFIG = {
    "enabled": False,
    "role_id": None,
    "duration_hours": 24,  # Fixed at 24 hours
    "custom_message": "Hey! Your **24-hour free access** to the <#1350929852299214999> channel has unfortunately **ran out**. We truly hope you were able to benefit with us & we hope to see you back soon! For now, feel free to continue following our trade signals in ⁠<#1350929790148022324>",
    "active_members": {},  # member_id: {"role_added_time": datetime, "role_id": role_id, "weekend_delayed": bool}
    "weekend_pending": {}  # member_id: {"join_time": datetime, "guild_id": guild_id} for weekend joiners
}

# Amsterdam timezone (UTC+1, UTC+2 during DST)
AMSTERDAM_TZ = timezone(timedelta(hours=1))  # CET (Central European Time)

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
        
        # Start the weekend activation task
        if not self.weekend_activation_task.is_running():
            self.weekend_activation_task.start()
        
        # Load auto-role config if it exists
        await self.load_auto_role_config()
        
        print("⚠️ Telegram integration not configured")

    def is_weekend_time(self, dt=None):
        """Check if the given datetime (or now) falls within weekend trading closure"""
        if dt is None:
            dt = datetime.now(AMSTERDAM_TZ)
        else:
            dt = dt.astimezone(AMSTERDAM_TZ)
        
        # Weekend period: Friday 12:00 to Sunday 23:59 (Amsterdam time)
        weekday = dt.weekday()  # Monday=0, Sunday=6
        hour = dt.hour
        
        if weekday == 4 and hour >= 12:  # Friday from 12:00
            return True
        elif weekday == 5 or weekday == 6:  # Saturday or Sunday
            return True
        else:
            return False

    def get_next_monday_activation_time(self):
        """Get the next Monday 00:01 Amsterdam time"""
        now = datetime.now(AMSTERDAM_TZ)
        
        # Find next Monday
        days_ahead = 0 - now.weekday()  # Monday is 0
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_monday = now + timedelta(days=days_ahead)
        activation_time = next_monday.replace(hour=0, minute=1, second=0, microsecond=0)
        
        return activation_time

    async def on_member_join(self, member):
        """Handle new member joins and assign auto-role if enabled"""
        if not AUTO_ROLE_CONFIG["enabled"] or not AUTO_ROLE_CONFIG["role_id"]:
            return
        
        try:
            role = member.guild.get_role(AUTO_ROLE_CONFIG["role_id"])
            if not role:
                print(f"❌ Auto-role not found in guild {member.guild.name}")
                return
            
            join_time = datetime.now(AMSTERDAM_TZ)
            
            # Check if it's weekend time
            if self.is_weekend_time(join_time):
                # Weekend join - delay activation until Monday
                AUTO_ROLE_CONFIG["weekend_pending"][str(member.id)] = {
                    "join_time": join_time.isoformat(),
                    "guild_id": member.guild.id
                }
                
                # Add the role immediately but mark as weekend delayed
                await member.add_roles(role, reason="Auto-role for new member (weekend delayed)")
                
                AUTO_ROLE_CONFIG["active_members"][str(member.id)] = {
                    "role_added_time": join_time.isoformat(),
                    "role_id": AUTO_ROLE_CONFIG["role_id"],
                    "guild_id": member.guild.id,
                    "weekend_delayed": True,
                    "activation_time": self.get_next_monday_activation_time().isoformat()
                }
                
                # Send weekend notification DM
                try:
                    weekend_message = ("Hey! We're in the weekend right now, which means the trading markets are closed. "
                                     "We contacted you earlier to let you know about the 24-hour Premium Channel welcome gift, "
                                     "and we're writing you again to let you know that your 24 hours will start counting from the "
                                     "moment the markets open again on the upcoming Monday. This way, your welcome gift won't be "
                                     "wasted on the weekend, and you'll actually be able to make use of it.")
                    await member.send(weekend_message)
                    print(f"✅ Sent weekend notification DM to {member.display_name}")
                except discord.Forbidden:
                    print(f"⚠️ Could not send weekend notification DM to {member.display_name} (DMs disabled)")
                except Exception as e:
                    print(f"❌ Error sending weekend notification DM to {member.display_name}: {str(e)}")
                
                print(f"✅ Auto-role '{role.name}' added to {member.display_name} (weekend delayed activation)")
                
            else:
                # Normal join - immediate activation
                await member.add_roles(role, reason="Auto-role for new member")
                
                AUTO_ROLE_CONFIG["active_members"][str(member.id)] = {
                    "role_added_time": join_time.isoformat(),
                    "role_id": AUTO_ROLE_CONFIG["role_id"],
                    "guild_id": member.guild.id,
                    "weekend_delayed": False
                }
                
                print(f"✅ Auto-role '{role.name}' added to {member.display_name} (immediate activation)")
            
            # Save the updated config
            await self.save_auto_role_config()
            
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

    @tasks.loop(minutes=15)  # Check every 15 minutes for more precise timing
    async def role_removal_task(self):
        """Background task to remove expired roles and send DMs"""
        if not AUTO_ROLE_CONFIG["enabled"] or not AUTO_ROLE_CONFIG["active_members"]:
            return
        
        current_time = datetime.now(AMSTERDAM_TZ)
        expired_members = []
        
        for member_id, data in AUTO_ROLE_CONFIG["active_members"].items():
            try:
                # Skip weekend delayed members that haven't been activated yet
                if data.get("weekend_delayed", False):
                    # Check if activation time has been reached
                    activation_time = datetime.fromisoformat(data.get("activation_time"))
                    if activation_time.tzinfo is None:
                        activation_time = activation_time.replace(tzinfo=AMSTERDAM_TZ)
                    else:
                        activation_time = activation_time.astimezone(AMSTERDAM_TZ)
                    
                    if current_time < activation_time:
                        continue  # Not yet activated
                    
                    # Calculate expiry from activation time, not role_added_time
                    expiry_time = activation_time + timedelta(hours=24)
                else:
                    # Normal members - calculate from role_added_time
                    role_added_time = datetime.fromisoformat(data["role_added_time"])
                    if role_added_time.tzinfo is None:
                        role_added_time = role_added_time.replace(tzinfo=AMSTERDAM_TZ)
                    else:
                        role_added_time = role_added_time.astimezone(AMSTERDAM_TZ)
                    
                    expiry_time = role_added_time + timedelta(hours=24)
                
                if current_time >= expiry_time:
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

    @tasks.loop(minutes=5)  # Check every 5 minutes for weekend activations
    async def weekend_activation_task(self):
        """Background task to activate weekend delayed roles on Monday"""
        if not AUTO_ROLE_CONFIG["enabled"] or not AUTO_ROLE_CONFIG["active_members"]:
            return
        
        current_time = datetime.now(AMSTERDAM_TZ)
        activated_members = []
        
        for member_id, data in AUTO_ROLE_CONFIG["active_members"].items():
            try:
                if not data.get("weekend_delayed", False):
                    continue
                
                activation_time = datetime.fromisoformat(data.get("activation_time"))
                if activation_time.tzinfo is None:
                    activation_time = activation_time.replace(tzinfo=AMSTERDAM_TZ)
                else:
                    activation_time = activation_time.astimezone(AMSTERDAM_TZ)
                
                # Check if it's time to activate (Monday 00:01 has passed)
                if current_time >= activation_time and data.get("weekend_delayed"):
                    # Send activation notification DM
                    guild = self.get_guild(data["guild_id"])
                    if guild:
                        member = guild.get_member(int(member_id))
                        if member:
                            try:
                                activation_message = ("Hey! The weekend is over and the markets are now open. "
                                                    "That means your 24-hour welcome gift has officially started. "
                                                    "You now have full access to the <#1384668129036075109> channel. "
                                                    "Let's make the most of it by securing some wins together!")
                                await member.send(activation_message)
                                print(f"✅ Sent activation notification DM to {member.display_name}")
                            except discord.Forbidden:
                                print(f"⚠️ Could not send activation notification DM to {member.display_name} (DMs disabled)")
                            except Exception as e:
                                print(f"❌ Error sending activation notification DM to {member.display_name}: {str(e)}")
                    
                    # Mark as activated (remove weekend_delayed flag)
                    AUTO_ROLE_CONFIG["active_members"][member_id]["weekend_delayed"] = False
                    AUTO_ROLE_CONFIG["active_members"][member_id]["role_added_time"] = activation_time.isoformat()
                    activated_members.append(member_id)
                    
            except Exception as e:
                print(f"❌ Error processing weekend activation for member {member_id}: {str(e)}")
        
        # Clean up weekend_pending entries for activated members
        for member_id in activated_members:
            if member_id in AUTO_ROLE_CONFIG["weekend_pending"]:
                del AUTO_ROLE_CONFIG["weekend_pending"][member_id]
        
        # Save updated config if there were changes
        if activated_members:
            await self.save_auto_role_config()
            print(f"✅ Activated {len(activated_members)} weekend delayed roles")

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

def get_remaining_time_display(member_id: str) -> str:
    """Get formatted remaining time display for a member"""
    try:
        data = AUTO_ROLE_CONFIG["active_members"].get(member_id)
        if not data:
            return "Unknown"
        
        current_time = datetime.now(AMSTERDAM_TZ)
        
        if data.get("weekend_delayed", False):
            # For weekend delayed members, show time until activation or time since activation
            activation_time = datetime.fromisoformat(data.get("activation_time"))
            if activation_time.tzinfo is None:
                activation_time = activation_time.replace(tzinfo=AMSTERDAM_TZ)
            else:
                activation_time = activation_time.astimezone(AMSTERDAM_TZ)
            
            if current_time < activation_time:
                # Not yet activated - show time until activation
                time_until_activation = activation_time - current_time
                hours = int(time_until_activation.total_seconds() // 3600)
                minutes = int((time_until_activation.total_seconds() % 3600) // 60)
                seconds = int(time_until_activation.total_seconds() % 60)
                return f"Activates in {hours}h {minutes}m {seconds}s"
            else:
                # Activated - show remaining time from activation
                expiry_time = activation_time + timedelta(hours=24)
                time_remaining = expiry_time - current_time
        else:
            # Normal member - calculate from role_added_time
            role_added_time = datetime.fromisoformat(data["role_added_time"])
            if role_added_time.tzinfo is None:
                role_added_time = role_added_time.replace(tzinfo=AMSTERDAM_TZ)
            else:
                role_added_time = role_added_time.astimezone(AMSTERDAM_TZ)
            
            expiry_time = role_added_time + timedelta(hours=24)
            time_remaining = expiry_time - current_time
        
        if time_remaining.total_seconds() <= 0:
            return "Expired"
        
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        seconds = int(time_remaining.total_seconds() % 60)
        
        return f"{hours}h {minutes}m {seconds}s"
        
    except Exception as e:
        print(f"Error calculating time for member {member_id}: {str(e)}")
        return "Error"

@bot.tree.command(name="timedautorole", description="Configure timed auto-role for new members (24h fixed duration)")
@app_commands.describe(
    action="Enable/disable, check status, or list active members",
    role="Role to assign to new members (required when enabling)"
)
async def timed_auto_role_command(
    interaction: discord.Interaction,
    action: str,
    role: discord.Role | None = None
):
    """Configure the timed auto-role system with fixed 24-hour duration"""
    
    # Check permissions
    if not interaction.guild or not interaction.user.guild_permissions.manage_roles:
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
            
            # Update configuration (duration is fixed at 24 hours)
            AUTO_ROLE_CONFIG["enabled"] = True
            AUTO_ROLE_CONFIG["role_id"] = role.id
            AUTO_ROLE_CONFIG["duration_hours"] = 24  # Fixed duration
            
            # Save configuration
            await bot.save_auto_role_config()
            
            await interaction.response.send_message(
                f"✅ **Auto-role system enabled!**\n"
                f"• **Role:** {role.mention}\n"
                f"• **Duration:** 24 hours (fixed)\n"
                f"• **Weekend handling:** Enabled (roles for weekend joiners activate on Monday)\n\n"
                f"New members will automatically receive this role for 24 hours.",
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
                weekend_pending_count = len(AUTO_ROLE_CONFIG.get("weekend_pending", {}))
                
                status_message = f"✅ **Auto-role system is ENABLED**\n"
                if role:
                    status_message += f"• **Role:** {role.mention}\n"
                else:
                    status_message += f"• **Role:** Not found (ID: {AUTO_ROLE_CONFIG['role_id']})\n"
                status_message += f"• **Duration:** 24 hours (fixed)\n"
                status_message += f"• **Active members:** {active_count}\n"
                status_message += f"• **Weekend pending:** {weekend_pending_count}\n"
                status_message += f"• **Weekend handling:** Enabled"
            else:
                status_message = "❌ **Auto-role system is DISABLED**"
            
            await interaction.response.send_message(status_message, ephemeral=True)
            
        elif action.lower() == "list":
            if not AUTO_ROLE_CONFIG["enabled"]:
                await interaction.response.send_message("❌ Auto-role system is disabled. No active members to display.", ephemeral=True)
                return
            
            if not AUTO_ROLE_CONFIG["active_members"]:
                await interaction.response.send_message("📝 No members currently have temporary roles.", ephemeral=True)
                return
            
            # Build the list of active members with precise time remaining
            member_list = []
            
            for member_id, data in AUTO_ROLE_CONFIG["active_members"].items():
                try:
                    # Get member info
                    guild = interaction.guild
                    if not guild:
                        continue
                        
                    member = guild.get_member(int(member_id))
                    if not member:
                        continue
                    
                    # Get precise remaining time
                    time_display = get_remaining_time_display(member_id)
                    member_list.append(f"• {member.display_name} - {time_display}")
                        
                except Exception as e:
                    print(f"Error processing member {member_id}: {str(e)}")
                    continue
            
            if not member_list:
                await interaction.response.send_message("📝 No valid members found with temporary roles.", ephemeral=True)
                return
            
            # Create the response message
            role = interaction.guild.get_role(AUTO_ROLE_CONFIG["role_id"]) if interaction.guild and AUTO_ROLE_CONFIG["role_id"] else None
            role_name = role.name if role else "Unknown Role"
            
            list_message = f"📋 **Active Temporary Role Members**\n"
            list_message += f"**Role:** {role_name}\n"
            list_message += f"**Duration:** 24 hours (fixed)\n\n"
            list_message += "\n".join(member_list[:20])  # Limit to 20 members to avoid message length issues
            
            if len(member_list) > 20:
                list_message += f"\n\n*...and {len(member_list) - 20} more members*"
            
            await interaction.response.send_message(list_message, ephemeral=True)
            
        else:
            await interaction.response.send_message("❌ Invalid action. Use 'enable', 'disable', 'status', or 'list'.", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error configuring auto-role: {str(e)}", ephemeral=True)

@timed_auto_role_command.autocomplete('action')
async def action_autocomplete(interaction: discord.Interaction, current: str):
    actions = ['enable', 'disable', 'status', 'list']
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
        
        # Add special note for US100 & GER40
        if pair.upper() in ['US100', 'GER40']:
            signal_message += f"\n\n**Please note that prices on US100 & GER40 vary a lot from broker to broker, so it is possible that the current price in our signal is different than the current price with your broker. Execute this signal within a 5 minute window of this trade being sent and please manually recalculate the pip value for TP1/2/3 & SL depending on your broker's current price.**"
        
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
        await interaction.response.send_message(f"❌ Error sending stats: {str(e)}", ephemeral=True)

# Web server for health checks
async def web_server():
    """Simple web server for health checks"""
    async def health_check(request):
        return web.Response(text="Bot is running!", status=200)
    
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 5000)
        await site.start()
        print("Web server started on port 5000")
    except Exception as e:
        print(f"Failed to start web server: {e}")

async def main():
    """Main async function to run both the web server and Discord bot"""
    # Check if Discord token is available
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables")
        return
    
    # Start web server
    print("Starting web server...")
    await web_server()
    
    # Start Discord bot
    print("Starting Discord bot...")
    try:
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        print(f"Error starting Discord bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
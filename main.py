import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio
from aiohttp import web

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
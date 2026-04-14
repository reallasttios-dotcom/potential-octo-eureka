import discord
from discord.ext import commands
import asyncio
import os
import aiosqlite
from datetime import datetime
from dotenv import load_dotenv
import time
import traceback

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = ["!", "?", "m"]

COGS = [
    "cogs.emojihandler",
    "cogs.imaging_cog",
    "cogs.activity",
    "cogs.tiktok",
    "cogs.emoji",
    "cogs.antinuke",
    "cogs.anon",
    "cogs.utility",
    "cogs.debate",
    "cogs.appeal",
    "cogs.self",
    "cogs.snipe",
    "cogs.antibot",
    "cogs.tempvoice",
    # "cogs.invite_logger", # Merged into server_logging
    "cogs.starboard",
    "cogs.rolecounter",
    "cogs.fun",
    "cogs.translate",
    "cogs.channel",
    "cogs.embed",
    "cogs.help",
    "cogs.moderation",
    "cogs.boost_tracker",
    "cogs.server_config",
    "cogs.admin",
    "cogs.leveling",
    "cogs.verification",
    "cogs.tickets",
    "cogs.bump",
    "cogs.prefix_manager",
    "cogs.image_manipulation",
    "cogs.afk",
    "cogs.server_logging",
    "cogs.reactionroles",
]


class MeridianBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix=self._get_prefix, intents=intents, help_command=None)
        self.db = None
        self.start_time = None

    async def _get_prefix(self, bot, message):
        default_prefixes = PREFIX[:]
        if not message.guild:
            return default_prefixes
        try:
            async with self.db.execute(
                "SELECT serverprefix FROM prefix WHERE guild = ?", (str(message.guild.id),)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row["serverprefix"]:
                    return [row["serverprefix"]] + default_prefixes
        except Exception:
            pass
        return default_prefixes

    async def setup_hook(self):
        print(f"[{time.strftime('%H:%M:%S')}] Setting up DB...")
        self.db = await aiosqlite.connect("mainDB.sqlite")
        self.db.row_factory = aiosqlite.Row
        await self.init_db()
        print(f"[{time.strftime('%H:%M:%S')}] DB ready.")

        # Ensure necessary directories exist
        for directory in ["logs", "logs/exports", "logs/backups", "logs/archives", "config"]:
            os.makedirs(directory, exist_ok=True)

        total = len(COGS)
        for idx, cog in enumerate(COGS, 1):
            start = time.perf_counter()
            print(f"[{time.strftime('%H:%M:%S')}] Loading {cog} ({idx}/{total})...")
            
            try:
                # Optional: add a timeout (e.g., 30 seconds per cog)
                await asyncio.wait_for(self.load_extension(cog), timeout=30.0)
                elapsed = (time.perf_counter() - start) * 1000
                print(f"[{time.strftime('%H:%M:%S')}] ✅ Loaded {cog} in {elapsed:.0f}ms")
            
            except asyncio.TimeoutError:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ TIMEOUT loading {cog} ( >30s )")
            
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed {cog}: {type(e).__name__}: {e}")
                traceback.print_exc()   # full stack trace

        try:
            synced = await self.tree.sync()
            print(f"[{time.strftime('%H:%M:%S')}] ✅ Synced {len(synced)} application commands.")
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] ❌ Failed to sync application commands: {type(e).__name__}: {e}")
            traceback.print_exc()

        print(f"[{time.strftime('%H:%M:%S')}] Setup complete.")

    async def init_db(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS levels (
                id TEXT PRIMARY KEY, user TEXT, guild TEXT,
                xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
                totalXP INTEGER DEFAULT 0, streakDays INTEGER DEFAULT 0,
                lastMessageDate TEXT, globalMultiplier REAL DEFAULT 1.0
            )""",
            "CREATE TABLE IF NOT EXISTS prefix (serverprefix TEXT, guild TEXT PRIMARY KEY)",
            """CREATE TABLE IF NOT EXISTS settings (
                guild TEXT PRIMARY KEY, levelUpMessage TEXT,
                customXP INTEGER, customCooldown INTEGER,
                globalMultiplier REAL DEFAULT 1.0,
                decayEnabled INTEGER DEFAULT 0,
                decayDays INTEGER DEFAULT 30,
                decayRate REAL DEFAULT 0.05
            )""",
            "CREATE TABLE IF NOT EXISTS channel (guild TEXT PRIMARY KEY, channel TEXT)",
            "CREATE TABLE IF NOT EXISTS xp_toggle (guild TEXT PRIMARY KEY, enabled INTEGER DEFAULT 1)",
            "CREATE TABLE IF NOT EXISTS blacklistTable (guild TEXT, typeId TEXT, type TEXT, id TEXT PRIMARY KEY)",
            # Leveling extras
            "CREATE TABLE IF NOT EXISTS xp_ignored_channels (guild TEXT, channel_id TEXT, PRIMARY KEY (guild, channel_id))",
            "CREATE TABLE IF NOT EXISTS xp_role_multipliers (guild TEXT, role_id TEXT, multiplier REAL, PRIMARY KEY (guild, role_id))",
            "CREATE TABLE IF NOT EXISTS xp_boost_channels (guild TEXT, channel_id TEXT, multiplier REAL, PRIMARY KEY (guild, channel_id))",
            "CREATE TABLE IF NOT EXISTS xp_user_multipliers (guild TEXT, user_id TEXT, multiplier REAL, PRIMARY KEY (guild, user_id))",
            "CREATE TABLE IF NOT EXISTS xp_log (id INTEGER PRIMARY KEY AUTOINCREMENT, guild TEXT, user_id TEXT, delta INTEGER, reason TEXT, timestamp TEXT)",
            "CREATE TABLE IF NOT EXISTS xp_user_blacklist (guild TEXT, user_id TEXT, PRIMARY KEY (guild, user_id))",
            # Snipe opt-out
            "CREATE TABLE IF NOT EXISTS snipe_optout (guild TEXT, user_id TEXT, PRIMARY KEY (guild, user_id))",
            # AFK
            "CREATE TABLE IF NOT EXISTS afk (guild TEXT, user_id TEXT, reason TEXT, since REAL, PRIMARY KEY (guild, user_id))",
            # Moderation DB tables (replaces mod_data.json)
            """CREATE TABLE IF NOT EXISTS warns (
                id TEXT PRIMARY KEY, guild TEXT, user_id TEXT,
                reason TEXT, moderator_id TEXT, timestamp TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS mod_notes (
                id TEXT PRIMARY KEY, guild TEXT, user_id TEXT,
                text TEXT, moderator_id TEXT, timestamp TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS mod_actions (
                id TEXT PRIMARY KEY, guild TEXT, user_id TEXT,
                type TEXT, reason TEXT, duration TEXT,
                moderator_id TEXT, timestamp TEXT
            )""",
            "CREATE TABLE IF NOT EXISTS muteroles (guild TEXT PRIMARY KEY, role_id TEXT)",
            "CREATE TABLE IF NOT EXISTS hardmutes (guild TEXT, user_id TEXT, role_ids TEXT, PRIMARY KEY (guild, user_id))",
            # Starboard
            "CREATE TABLE IF NOT EXISTS starboard_messages (guild TEXT, message_id TEXT, starboard_message_id TEXT, PRIMARY KEY (guild, message_id))",
            "CREATE TABLE IF NOT EXISTS starboard_ignored_channels (guild TEXT, channel_id TEXT, PRIMARY KEY (guild, channel_id))",
            # Bump
            "CREATE TABLE IF NOT EXISTS bump_log (guild TEXT, user_id TEXT, count INTEGER DEFAULT 0, PRIMARY KEY (guild, user_id))",
            "CREATE TABLE IF NOT EXISTS bump_schedule (guild TEXT PRIMARY KEY, next_bump_time REAL)",
            # Anon
            "CREATE TABLE IF NOT EXISTS anon_bans (guild TEXT, user_id TEXT, PRIMARY KEY (guild, user_id))",
            "CREATE TABLE IF NOT EXISTS anon_log (id INTEGER PRIMARY KEY AUTOINCREMENT, guild TEXT, message_id TEXT, user_id TEXT, content TEXT, timestamp TEXT)",
            "CREATE TABLE IF NOT EXISTS anon_cooldowns (guild TEXT, user_id TEXT, last_post REAL, PRIMARY KEY (guild, user_id))",
            # TempVoice
            "CREATE TABLE IF NOT EXISTS tempvoice_channels (channel_id TEXT PRIMARY KEY, owner_id TEXT, guild_id TEXT)",
            # Reaction roles
            "CREATE TABLE IF NOT EXISTS reaction_roles (guild TEXT, message_id TEXT, emoji TEXT, role_id TEXT, PRIMARY KEY (guild, message_id, emoji))",
        ]
        for query in queries:
            await self.db.execute(query)
        await self.db.commit()

    async def on_ready(self):
        if not self.start_time:
            self.start_time = datetime.utcnow()
        print(f"🔱 Meridian Online | {self.user} | {len(self.guilds)} guilds")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            seconds = round(error.retry_after)
            embed = discord.Embed(
                description=f"⏱ Slow down! Try again in **{seconds}s**.",
                color=0xED4245
            )
            await ctx.reply(embed=embed, delete_after=6)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="🔒 You don't have permission to do that.",
                color=0xED4245
            )
            await ctx.reply(embed=embed, delete_after=6)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="🔒 I don't have the required permissions for that.",
                color=0xED4245
            )
            await ctx.reply(embed=embed, delete_after=6)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(description="❌ Member not found.", color=0xED4245)
            await ctx.reply(embed=embed, delete_after=6)
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                description="🔒 You don't have permission to use this command.",
                color=0xED4245
            )
            await ctx.reply(embed=embed, delete_after=6)
        elif isinstance(error, commands.CommandInvokeError):
            print(f"[ERROR] {ctx.command}: {error.original}")
        else:
            print(f"[ERROR] {ctx.command}: {error}")

    async def close(self):
        if self.db:
            await self.db.close()
        await super().close()


bot = MeridianBot()


async def main():
    async with bot:
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("❌ Error: No DISCORD_TOKEN found in .env file.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Meridian safely...")

import asyncio
import signal

from discord import app_commands
from discord.ext import commands
import discord
from loguru import logger
from r6rcog import R6RCog
import os
import db
import config
from rank_cog import RankCog


class R6STR(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            activity=discord.Game(name="rainbow6turkiye.com | !r6r "),
            intents=discord.Intents(guilds=True, members=True, emojis=True, integrations=True, webhooks=False,
                                    invites=True, voice_states=False, messages=True, reactions=True, typing=True,message_content=True)
        )

        self.config: config.Config = None

        # add shutdown signal handlers
        signal.signal(signal.SIGINT, self.shutdown_signal_handler)
        signal.signal(signal.SIGTERM, self.shutdown_signal_handler)

    async def setup_hook(self) -> None:
        await db.init()
        self.config = await config.Config.create()
        await self.add_cog(R6RCog(self, self.config))
        await self.add_cog(RankCog(self, self.config))

        self.tree.copy_global_to(guild=discord.Object(id=615450809974521861))
        await self.tree.sync()

    async def clean_shutdown(self):
        await db.close()
        await self.close()
        logger.info("Clean shutdown completed")

    def shutdown_signal_handler(self, signum, frame):
        print("interrupt received")
        task = asyncio.get_running_loop().create_task(self.clean_shutdown())


if __name__ == '__main__':
    if os.environ["ACTIVE"].lower() == "true":
        bot = R6STR()
        bot.run(os.environ["BOT_TOKEN"])

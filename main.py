import asyncio
import signal

from discord.ext import commands
import discord
from loguru import logger
from r6rcog import R6RCog
import os
import db
import config


class R6STR(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            activity=discord.Game(name="rainbow6turkiye.com | !r6r "),
            intents=discord.Intents(guilds=True, members=True, emojis=True, integrations=False, webhooks=False,
                                    invites=True, voice_states=False, messages=True, reactions=True, typing=True)
        )

        self.first_connect: bool = True
        self.config: config.Config = None

        # add shutdown signal handlers
        signal.signal(signal.SIGINT, self.shutdown_signal_handler)
        signal.signal(signal.SIGTERM, self.shutdown_signal_handler)

    async def on_connect(self):
        if self.first_connect is False:
            return
        else:
            self.first_connect = False
            await db.init()
            self.config = await config.Config.create()
            self.add_cog(R6RCog(self, self.config))

    async def clean_shutdown(self):
        await db.close()
        await self.logout()
        logger.info("Clean shutdown completed")

    def shutdown_signal_handler(self, signum, frame):
        print("interrupt received")
        task = asyncio.get_running_loop().create_task(self.clean_shutdown())


if __name__ == '__main__':
    bot = R6STR()
    bot.run(os.environ["BOT_TOKEN"])

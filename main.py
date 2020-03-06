from discord.ext import commands
import os

owner_ids = [109079148533657600, 491148317552803851]
bot = commands.Bot(command_prefix='!r6r ', owner_ids=owner_ids)

bot.load_extension('maincog')
bot.run(os.environ["BOT_TOKEN"])

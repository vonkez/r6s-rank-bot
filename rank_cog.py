import os
from asyncio import Task

import discord
from discord import AppCommandType, app_commands
from discord.ext import commands
from loguru import logger

from config import Config
from rank_controller import RankController
from stat_providers.multi_provider import MultiProvider
from stat_providers.r6stats import R6Stats
from stat_providers.stat_provider import Platform
from stat_providers.statsdb import StatsDB

"""
Slash commands 
"""


class RankCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config, ) -> None:
        provider = os.environ["PROVIDER"]
        self.config = config
        self.bot = bot
        self.controller = RankController(bot, config)

        logger.info("RankCog initialized")

    @app_commands.command(name="kayıt", description="Rank rolü almak için kayıt yapar")
    @app_commands.choices(platform=[
        discord.app_commands.Choice(name='PC', value='pc'),
        discord.app_commands.Choice(name='Xbox', value='xbox'),
        discord.app_commands.Choice(name='Playstation', value='ps4'),
    ])
    @app_commands.describe(nickname='Oyun-içi isminiz', platform='Oynadığınız platform')
    @app_commands.guild_only()
    async def kayit_command(self, interaction: discord.Interaction, nickname: str, platform: str = 'pc') -> None:
        platform_enum = Platform[platform.upper()]
        await self.controller.kayit(interaction, nickname, platform_enum, interaction.user)

    @app_commands.command(name="güncelle", description="Rank günceller")
    @app_commands.guild_only()
    async def guncelle_command(self, interaction: discord.Interaction) -> None:
        await self.controller.guncelle(interaction)

    @app_commands.command(name="profil", description="Profili görüntüler")
    @app_commands.guild_only()
    async def profil_command(self, interaction: discord.Interaction) -> None:
        await self.controller.profil(interaction)

    @app_commands.command(name="sil", description="Rank kaydını sil")
    @app_commands.guild_only()
    async def sil_command(self, interaction: discord.Interaction) -> None:
        await self.controller.sil(interaction)

    @app_commands.command(name="yoket", description="Kayıt yokedici ┌( ͝° ͜ʖ͡°)=ε/̵͇̿̿/’̿’̿ ̿  (Admin+)")
    @app_commands.describe(discord_id='Silinecek kullanıcının discord id\'si')
    @app_commands.guild_only()
    @app_commands.checks.has_role(615455120246702081)
    async def yoket_command(self, interaction: discord.Interaction, discord_id: str) -> None:
        await self.controller.yoket(interaction, int(discord_id))

import copy
import datetime
import os
from typing import Optional, List

import discord
from discord import Member, Guild, Role, Interaction
from discord.ext import commands
from discord.ext.commands import MemberNotFound
from loguru import logger

from config import Config
from embed import Color, MessageEmbed, ProfileEmbed, AnonymousMessageEmbed
from models import DBUser
from stat_providers.multi_provider import MultiProvider
from stat_providers.r6stats import R6Stats
from stat_providers.sapi import SApi
from stat_providers.stat_provider import Platform, Player
from stat_providers.statsdb import StatsDB

"""
Controller for new slash commands
"""
class RankController():
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        provider = os.environ["PROVIDER"]
        self.config = config
        self.bot = bot
        if provider == "MULTI":
            self.stat_provider = MultiProvider()
        elif provider == "STATSDB":
            self.stat_provider = StatsDB()
        elif provider == "R6STATS":
            self.stat_provider = R6Stats()
        elif provider == "SAPI":
            self.stat_provider = SApi()
        logger.info("RankController initialized")

    async def kayit(self, interaction: discord.Interaction, nickname: str, platform: Platform, member: discord.Member):
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()
        if db_user is not None:
            embed = MessageEmbed(interaction,
                                 message=f"Zaten `{db_user.r6_nick}` nickiyle açılmış bir kayıdınız bulunuyor.",
                                 color=Color.RED)
            await embed.send_error()
            return

        db_user: DBUser = await DBUser.filter(r6_nick=nickname).first()
        if db_user is not None:
            msg = f"Nick çakışması kayıtlı kullanıcı: {db_user.dc_id} - r6: {db_user.r6_nick}, kayıt olmaya çalışan: {interaction.user.mention}"
            logger.warning(msg)
            await self.log(msg)
            embed = MessageEmbed(interaction,
                                 message=f"`{db_user.r6_nick}` nickiyle açılmış bir kayıt bulunuyor. **Sizin olmayan nicklerle kayıt olmak yasaktır.** Eğer bu nick size aitse `#ticket` kanalından ticket oluşturunuz.")
            await embed.send()
            return

        player: Player = await self.stat_provider.get_player(nickname, platform)
        db_user = DBUser.create_from_player(interaction, player)

        confirmation_embed = ProfileEmbed(interaction, db_user,
                                          message="Yukarıdaki bilgiler size aitse onaylayın.")
        confirmed: bool = await confirmation_embed.ask_confirmation()

        if not confirmed:
            cancel_embed = MessageEmbed(interaction, message="İşlem iptal edildi.", color=Color.RED)
            await cancel_embed.send(followup=True)
            return

        await self.update_roles(db_user)
        await db_user.save()

        success_embed = ProfileEmbed(interaction, db_user, "Kayıdınız tamamlanmıştır.")
        await success_embed.send(followup=True)

    async def sil(self, interaction: discord.Interaction):
        db_user: DBUser = await DBUser.filter(dc_id=interaction.user.id).first()

        if db_user is None:
            embed = MessageEmbed(interaction,
                                 message=f'Kaydınız bulunamadı. Sil komutunu kullanmak için kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        confirmation_embed = ProfileEmbed(interaction, db_user, "Kayıt silme işlemini onaylıyor musunuz?")
        confirmed: bool = await confirmation_embed.ask_confirmation()
        if confirmed:
            await self.clear_roles(interaction, db_user)
            await db_user.delete()
            embed = MessageEmbed(interaction, message=f'Kaydınız başarıyla silinmiştir.')
            await embed.send(followup=True)
            return
        else:
            cancel_embed = MessageEmbed(interaction, message="İşlem iptal edildi.")
            await cancel_embed.send_error()

    async def guncelle(self, interaction: discord.Interaction):
        db_user: DBUser = await DBUser.filter(dc_id=interaction.user.id).first()
        original_db_user: DBUser = copy.deepcopy(db_user)

        if db_user is None:
            embed = MessageEmbed(interaction,
                                 message=f'Kaydınız bulunamadı. Güncellemeden önce kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        player: Player = await self.stat_provider.get_player(db_user.r6_nick, db_user.platform)

        if interaction.user.id == db_user.dc_id:
            db_user.update_from_player(player, True)
        else:
            db_user.update_from_player(player, False)

        await self.update_roles(db_user)
        await db_user.save()

        success_embed = ProfileEmbed(interaction, db_user, message="Profiliniz güncellenmiştir.",
                                     old_db_user=original_db_user)
        await success_embed.send()

    async def profil(self, interaction: discord.Interaction):
        db_user: DBUser = await DBUser.filter(dc_id=interaction.user.id).first()

        if db_user is None:
            embed = MessageEmbed(interaction,
                                 message=f'Kaydınız bulunamadı. Profil komutunu kullanmak için kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        db_user.last_command = datetime.datetime.today()
        db_user.inactive = False
        await db_user.save()

        success_embed = ProfileEmbed(interaction, db_user)
        await success_embed.send()

    async def yoket(self, interaction: discord.Interaction, discord_id: int):
        db_user: DBUser = await DBUser.filter(dc_id=discord_id).first()

        if db_user is None:
            embed = MessageEmbed(interaction,
                                 message=f'Kayıt bulunamadı.')
            await embed.send_error()
            return
        member_left = False
        try:
            await self.clear_roles(interaction, db_user)
        except:
            member_left = True
        await db_user.delete()

        embed = MessageEmbed(interaction,
                             message=f'Kayıt başarıyla silinmiştir{"(Kullanıcı sunucuyu terketmiş)" if member_left else ""}.')
        await embed.send()
        return

    async def clear_roles(self, interaction: Interaction, db_user: DBUser) -> None:
        guild: Guild = interaction.guild
        member: Optional[Member] = guild.get_member(db_user.dc_id)

        if member is None:
            raise MemberNotFound(None)

        rank_role_ids = await self.config.get_rank_roles()
        platform_role_ids = await self.config.get_platform_roles()

        rank_roles: List[Role] = [guild.get_role(role_id) for role_id in rank_role_ids]
        platform_roles: List[Role] = [guild.get_role(role_id) for role_id in platform_role_ids]

        roles_to_remove: List[Role] = []

        for role in member.roles:
            if role in rank_roles or role in platform_roles:
                roles_to_remove.append(role)

        await member.remove_roles(*roles_to_remove)

    async def update_roles(self, db_user: DBUser) -> None:
        guild: Guild = self.bot.guilds[0]
        member: Optional[Member] = guild.get_member(db_user.dc_id)

        if member is None:
            raise MemberNotFound(None)

        rank_role_id = await self.config.get_rank_role(db_user.rank_short)
        rank_role_ids = await self.config.get_rank_roles()

        platform_role_id = await self.config.get_platform_role(db_user.platform)
        platform_role_ids = await self.config.get_platform_roles()

        rank_roles: List[Role] = [guild.get_role(role_id) for role_id in rank_role_ids]
        rank_role: Role = guild.get_role(rank_role_id)

        platform_roles: List[Role] = [guild.get_role(role_id) for role_id in platform_role_ids]
        platform_role: Role = guild.get_role(platform_role_id)

        roles_to_add: List[Role] = []
        roles_to_remove: List[Role] = []

        if rank_role not in member.roles:
            roles_to_add.append(rank_role)
        if platform_role not in member.roles:
            roles_to_add.append(platform_role)

        for role in rank_roles:
            if role != rank_role and role in member.roles:
                roles_to_remove.append(role)

        for role in platform_roles:
            if role != platform_role and role in member.roles:
                roles_to_remove.append(role)

        await member.remove_roles(*roles_to_remove)
        await member.add_roles(*roles_to_add)

    async def log(self, msg: str, color: int = Color.GREEN, important: bool = False):
        """
        Sends msg to private log TextChannel.
        """
        log_channel_id = await self.config.get_log_channel()
        if log_channel_id is None:
            logger.error("Log channels is not set.")
            return

        channel = self.bot.get_channel(log_channel_id)
        if channel is None:
            logger.error("Log channel could not be found.")
            return

        embed = AnonymousMessageEmbed(msg, color)

        if important:
            await channel.send("@everyone", embed=embed)
        else:
            await channel.send(embed=embed)

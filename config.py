import discord
import os
from loguru import logger
from models import Ban, AllowedChannel, RankRoles, PlatformRoles, Configs
from stat_providers import RankShort, Platform
from typing import List, Union, Optional


class RoleNotFound(Exception):
    pass


class Config:
    _admins: List[int]

    # Using factory method for async constructor
    @classmethod
    async def create(cls) -> 'Config':

        self = Config()

        self._admins = [int(_id) for _id in os.environ["BOT_ADMINS"].split(",")]

        # Create empty configs if it doesn't exists
        rank_roles = await RankRoles.first()
        if rank_roles is None:
            await RankRoles.create()

        platform_roles = await PlatformRoles.first()
        if platform_roles is None:
            await PlatformRoles.create()

        configs = await Configs.first()
        if configs is None:
            await Configs.create(frequency=5)
        logger.info("Config initialized")
        return self

    # region admin
    async def is_admin(self, user: Union[discord.Member, discord.User]) -> bool:
        return user.id in self._admins
    # endregion

    # region ban
    async def add_banned(self, discord_user: Union[discord.Member, discord.User]) -> bool:
        if await self.is_banned(discord_user):
            return False
        await Ban.create(discord_id=discord_user.id)
        return True

    async def remove_banned(self, discord_user: Union[discord.Member, discord.User]) -> bool:
        if not await self.is_banned(discord_user):
            return False
        await Ban.filter(discord_id=discord_user.id).delete()
        return True

    async def is_banned(self, discord_user: Union[discord.Member, discord.User]) -> bool:
        return await Ban.filter(discord_id=discord_user.id).exists()
    # endregion

    # region Allowed channel
    async def add_allowed_channel(self, channel: discord.TextChannel) -> bool:
        if await self.is_channel_allowed(channel):
            return False
        await AllowedChannel.create(channel_id=channel.id)
        return True

    async def remove_allowed_channel(self, channel: discord.TextChannel) -> bool:
        if not await self.is_channel_allowed(channel):
            return False
        await AllowedChannel.filter(channel_id=channel.id).delete()
        return True

    async def is_channel_allowed(self, channel: discord.TextChannel) -> bool:
        return await AllowedChannel.filter(channel_id=channel.id).exists()
    # endregion

    # region roles
    async def set_rank_role(self, role: RankShort, discord_role: discord.Role) -> bool:
        rank_roles = await RankRoles.first()
        setattr(rank_roles, role.value, discord_role.id)
        await rank_roles.save()
        return True

    async def get_rank_role(self, role: RankShort) -> int:
        rank_roles = await RankRoles.first()
        role_id = getattr(rank_roles, role.value)
        if role_id is None:
            raise RoleNotFound()
        return role_id

    async def get_rank_roles(self) -> List[int]:
        rank_roles = await RankRoles.first()
        ids = [getattr(rank_roles, rank.value) for rank in RankShort]
        if None in ids:
            raise RoleNotFound()
        return ids

    async def set_platform_role(self, role: Platform, discord_role: discord.Role) -> bool:
        platform_roles = await PlatformRoles.first()
        setattr(platform_roles, role.value, discord_role.id)
        await platform_roles.save()
        return True

    async def get_platform_role(self, role: Platform) -> int:
        platform_roles = await PlatformRoles.first()
        role_id = getattr(platform_roles, role.value)
        if role_id is None:
            raise RoleNotFound()
        return role_id

    async def get_platform_roles(self) -> List[int]:
        platform_roles = await PlatformRoles.first()
        ids = [getattr(platform_roles, platform.value) for platform in Platform]
        if None in ids:
            raise RoleNotFound()
        return ids
    # endregion

    # region other
    async def set_log_channel(self, channel: discord.TextChannel) -> bool:
        configs = await Configs.first()
        configs.log_channel = channel.id
        await configs.save()
        return True

    async def get_log_channel(self) -> Optional[int]:
        configs = await Configs.first()
        return configs.log_channel

    async def set_guild(self, guild: discord.Guild) -> bool:
        configs = await Configs.first()
        configs.guild = guild.id
        await configs.save()
        return True

    async def get_guild(self) -> Optional[int]:
        configs = await Configs.first()
        return configs.guild

    async def set_frequency(self, days: int) -> bool:
        configs = await Configs.first()
        configs.frequency = days
        await configs.save()
        return True

    async def get_frequency(self) -> Optional[int]:
        configs = await Configs.first()
        return configs.frequency

    # endregion

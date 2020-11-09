from discord.ext import commands
from discord.ext.commands import CheckFailure, BadArgument, NotOwner


from config import Config
from stat_providers import Platform


class ChannelNotAllowed(CheckFailure):
    pass


class UserBanned(CheckFailure):
    pass


def bot_channel_only():
    async def predicate(ctx: commands.Context):
        config: Config = ctx.bot.config
        is_admin: bool = await config.is_admin(ctx.author)
        is_channel_allowed: bool = await config.is_channel_allowed(ctx.channel)
        if is_admin or is_channel_allowed:
            return True
        else:
            raise ChannelNotAllowed(f"Command is not allowed in this channel.", ctx.author, ctx.channel)

        # logger.warning(author.id + " tried to use command in wrong channel" + ctx.command.name)
        # return ctx.channel.id == ctx.cog.configs[ctx.guild.id]['bot_channel']
        # x = ctx.channel.id == ctx.cog.configs[ctx.guild.id]['bot_channel']
        # if x:
        #     return x
        # else:
        #     raise commands.CommandError('wrong_channel')
    return commands.check(predicate)


def admin_only():
    async def predicate(ctx: commands.Context):
        config: Config = ctx.bot.config
        is_admin: bool = await config.is_admin(ctx.author)
        if is_admin:
            return True
        else:
            raise NotOwner(f"{ctx.author} tried to use admin command")
    return commands.check(predicate)


def not_banned():
    async def predicate(ctx: commands.Context):
        config: Config = ctx.bot.config
        is_banned: bool = await config.is_banned(ctx.author)
        if is_banned:
            raise UserBanned(f"{ctx.author} tried to use command while banned")
        return not is_banned
    return commands.check(predicate)


def platform_converter(argument: str):
    try:
        platform = Platform[argument.upper()]
    except KeyError:
        raise BadArgument(f"Can't convert {argument} to Platform")

    return platform

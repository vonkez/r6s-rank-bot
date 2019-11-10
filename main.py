from discord.ext import commands
import asyncio
import aiohttp
import os

bot = commands.Bot(command_prefix='!r6r ')


@bot.command(usage="nickname")
async def rank(ctx, *args):
    if not ctx.channel.name == "rank-onay":
        return
    async with ctx.channel.typing():
        if len(args) == 1:
            mmr = await fetch_mmr(args[0])
            _rank = rank_from_mmr(mmr)
            if ctx.message.author.name == "Vonkez":
                _rank = "Diamond"

            if _rank == "Unranked":
                await ctx.send(f"Unranked olduğunuz için rol verilmemiştir.")
            target_rank = find_rank_role(ctx.guild.roles, _rank)
            other_roles = find_member_roles(ctx.message.author.roles)
            try:
                other_roles.remove(target_rank)
            except:
                pass
            await ctx.message.author.remove_roles(*other_roles)
            await ctx.message.author.add_roles(target_rank)
            await ctx.send(f"Rank rolünüz verilmiştir. ({_rank})")
        else:
            await ctx.send_help(rank)


async def fetch_mmr(nickname):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://r6tab.com/api/search.php?platform=uplay&search={nickname}') as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                mmr = json_resp['results'][0]['p_currentmmr']
                return mmr


def rank_from_mmr(mmr):
    if mmr <= 1: return "Unranked"
    elif mmr <= 1599: return "Copper"
    elif mmr <= 2099: return "Bronze"
    elif mmr <= 2599: return "Silver"
    elif mmr <= 3199: return "Gold"
    elif mmr <= 4399: return "Platinum"
    elif mmr <= 4999: return "Diamond"
    else: return "Champion"


def find_member_roles(roles):
    rank_roles = ["Copper", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion", "COPPER"]
    found_roles = []
    for _role in roles:
        if _role.name in rank_roles:
            found_roles.append(_role)
    return found_roles

def find_rank_role(roles, target):
    target_role = None
    for _role in roles:
        if _role.name == target:
            target_role = _role
    return target_role



bot.run(os.environ["BOT_TOKEN"])



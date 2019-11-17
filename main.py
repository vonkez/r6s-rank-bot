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
            nickname = args[0]

            # search player
            found_player = await search_player(nickname)

            # handling zero results
            if found_player is None:
                await ctx.send(f"`{nickname}` bulunamadı, doğru yazdığınızdan emin olun.")
                return

            player = await fetch_player(found_player['id'])

            if player is None:
                await ctx.send(f"Bilinmeyen bir hata oluştu <@109079148533657600> ile iletişime geçin.")

            player_rank = rank_from_mmr(player['mmr'])

            # very important part
            if ctx.message.author.name == "Vonkez":
                if ctx.message.author.discriminator == "2508":
                    player_rank = "Diamond"


            # find new role and remove old role
            target_role = find_rank_role(ctx.guild.roles, player_rank)
            other_roles = find_member_roles(ctx.message.author.roles)
            try:
                other_roles.remove(target_role)
            except:
                pass
            await ctx.message.author.remove_roles(*other_roles)

            # skip roleless ranks
            if target_role is None:
                await ctx.send(f"{player_rank} olduğunuz için rol verilmemiştir.")
                return

            # add new role
            await ctx.message.author.add_roles(target_role)

            # response
            await ctx.send(f"{ctx.message.author.mention} rank rolünüz verilmiştir. ({player['name']} -> {player_rank})")
        else:
            await ctx.send_help(rank)


async def search_player(nickname):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://r6tab.com/api/search.php?platform=uplay&search={nickname}') as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                try:
                    result = {}
                    result['id'] = json_resp['results'][0]['p_id']
                    result['level'] = json_resp['results'][0]['p_level']
                    result['mmr'] = json_resp['results'][0]['p_currentmmr']
                    result['name'] = json_resp['results'][0]['p_name']
                    return result
                except KeyError:
                    return None


async def fetch_player(_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://r6tab.com/api/player.php?p_id={_id}') as resp:
            if resp.status == 200:
                json_resp = await resp.json()
                if json_resp['playerfound'] != True:
                    return None
                try:
                    result = {}
                    result['mmr'] = json_resp['p_EU_currentmmr']
                    result['name'] = json_resp['p_name']
                    result['level'] = json_resp['p_level']
                    return result
                except KeyError:
                    return None


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
    rank_roles = ["Unranked", "Copper", "Bronze", "Silver", "Gold", "Platinum", "Diamond", "Champion", "COPPER"]
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




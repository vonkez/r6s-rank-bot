from discord.ext import commands
import discord
import asyncio
import aiohttp
import datetime
import os
import time

bot = commands.Bot(command_prefix='!r6r ')


@bot.command(usage="nickname")
async def rank(ctx, *args):
    # 0x259C34 yeşil
    # 0xB2283D kırmızı
    # 0x4AA8FF mavi

    # Reaction check
    def check(reaction, user):
        return user == ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')

    # Channel check
    if not ctx.channel.name == "rank-onay":
        return


    async with ctx.channel.typing():
        if len(args) == 1:
            nickname = args[0]
            fake_mention = ctx.message.author.name + "#" + ctx.message.author.discriminator

            # search player
            found_player = await search_player(nickname)

            # handling zero results
            if found_player is None:
                embed = create_error_embed(fake_mention, f"`{nickname}` bulunamadı, doğru yazdığınızdan emin olun.")
                await ctx.send(embed=embed)
                return

            # Fetch detailed information
            player = await fetch_player(found_player['id'])

            if player is None:
                embed = create_error_embed(fake_mention, "Bilinmeyen bir hata oluştu <@109079148533657600> ile iletişime geçin.")
                await ctx.send(embed=embed)
                return

            # Convert mmr to rank
            player_rank = rank_from_mmr(player['mmr'])

            # region very important part
            if ctx.message.author.name == "Vonkez":
                if ctx.message.author.discriminator == "2508":
                    player_rank = "Diamond"
            if ctx.message.author.name == "Vacthy":
                if ctx.message.author.discriminator == "8602":
                    player_rank = "Diamond"
            # endregion

            # Create confirmation embed
            embed = discord.Embed(colour=discord.Colour(0x4AA8FF), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_thumbnail(url=f"https://ubisoft-avatars.akamaized.net/{player['p_user']}/default_256_256.png")
            embed.set_footer(text="R6S Rank Bot")
            embed.add_field(name="Nickname", value=player['name'], inline=True)
            embed.add_field(name="Rank", value=player_rank, inline=True)
            embed.add_field(name="Level", value=player['level'], inline=True)
            embed.add_field(name=fake_mention,
                            value="**Yukarıdaki bilgiler size aitse ✅, değilse ❌ emojisine tıklayın.**")

            # Send confirmation emebd
            msg = await ctx.send(embed=embed)

            # Add reactions
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')

            # Listen for reply
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if reaction.emoji == str(reaction.emoji) == '✅':

                    #region role
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
                    #endregion

                    # create response embed
                    embed = discord.Embed(colour=discord.Colour(0x259C34),
                                          timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                    embed.set_thumbnail(
                        url=f"https://ubisoft-avatars.akamaized.net/{player['p_user']}/default_256_256.png")
                    embed.set_footer(text="R6S Rank Bot")
                    embed.add_field(name="Discord", value=fake_mention, inline=True)
                    embed.add_field(name="Nickname", value=player['name'], inline=True)
                    embed.add_field(name="Role", value=player_rank, inline=True)
                    embed.add_field(name="R6S Rank Bot", value="**Rolünüz verilmiştir.**")

                    # send response emebd
                    await ctx.send(embed=embed)
                    await msg.clear_reactions()

                if reaction.emoji == str(reaction.emoji) == '❌':
                    embed = create_error_embed(fake_mention, "Talebiniz üzerine rol verme işlemi iptal edilmiştir.")
                    await ctx.send(embed=embed)
                    await msg.clear_reactions()
            except asyncio.TimeoutError:
                embed = create_error_embed(fake_mention, "Verilen süre içerisinde yanıt vermediğiniz için rol verilmedi.")
                await ctx.send(embed=embed)
                await msg.delete()
        else:
            await ctx.send_help(rank)


def create_error_embed(mention, message):
    embed = discord.Embed(colour=discord.Colour(0xB2283D), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
    embed.set_footer(text="R6S Rank Bot")
    embed.add_field(name=mention, value=f"**{message}**")
    return embed


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
                    result['p_user'] = json_resp['p_user']
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


from discord.ext import commands
from db import create_db
import traceback
import datetime
import aiohttp
import asyncio
import discord
import time
import sys
import re

class MainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.colors = {'green': 0x259C34,
                       'red'  : 0xB2283D,
                       'blue' : 0x4AA8FF}
        self.configs = {}
        self.i = 1
        self.update_rate = datetime.timedelta(days=7)
        self.update_task = None

    def bot_channel_only():
        async def predicate(ctx):
            return ctx.channel.id == ctx.cog.configs[ctx.guild.id]['bot_channel']
            x = ctx.channel.id == ctx.cog.configs[ctx.guild.id]['bot_channel']
            if x:
                return x
            else:
                raise commands.CommandError('wrong_channel')
        return commands.check(predicate)



    async def update_loop(self):
        while True:
            await asyncio.sleep(86400)
            guild_id = list(self.configs.keys())[0]
            counter = 0
            await self.log(guild_id, 'Otomatik rank güncelleme başladı.')
            db_users = await self.db.get_all_users()
            today = datetime.date.today()
            for u in db_users:
                time_elapsed = today - u['update_date']
                if time_elapsed > self.update_rate:
                    await self.silent_update(u)
                    await asyncio.sleep(5)
                    counter += 1
            await self.log(guild_id, f'Otomatik rank güncelleme bitti. {counter}/{len(db_users)}')

    # region event listeners
    @commands.Cog.listener()
    async def on_connect(self):
        if self.db is None:
            self.db = await create_db()
            await self.db.create_tables()
        await self.fetch_configs()
        self.update_task = self.bot.loop.create_task(self.update_loop())

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.errors.MissingRequiredArgument) or isinstance(error, commands.errors.TooManyArguments):
            await ctx.send_help(ctx.command)
        elif isinstance(error, commands.NotOwner):
            await self.log(ctx.guild.id, f"{str(ctx.author)} admin komutu kullanmaya çalıştı ({ctx.command})")
        elif isinstance(error, commands.CheckFailure):
            await self.log(ctx.guild.id, f"{str(ctx.author)} yalış kanalda komut kullanmaya çalıştı ({ctx.command})")
        else:
            # Default error message
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    # endregion

    # region user commands

    @commands.command(name='kayıt', ignore_extra=False)
    @bot_channel_only()
    async def u_register(self, ctx, nickname):
        await self.register(ctx, ctx.author, nickname)


    @commands.command(name='güncelle', ignore_extra=False)
    @bot_channel_only()
    async def u_update(self, ctx):
        await self.update(ctx, ctx.author)


    @commands.command(name='profil', ignore_extra=False)
    @bot_channel_only()
    async def u_profile(self, ctx):
        await self.profile(ctx, ctx.author)

    @commands.command(name='sil', ignore_extra=False)
    @bot_channel_only()
    async def u_delete(self, ctx):
        await self.delete(ctx, ctx.author)

    # endregion

    # region admin commands
    @commands.is_owner()
    @commands.group()
    async def admin(self, ctx):
        pass

    @admin.command(name='kayıt', ignore_extra=False)
    async def a_register(self, ctx, nickname, user):
        dc_id = re.search("\d+", user).group()
        user = ctx.guild.get_member(int(dc_id))
        if user:
            await self.register(ctx, user, nickname)
        else:
            error_embed = self.create_message_embed(ctx.author, 'red', 'Aradığınız üye bulunamadı.')
            await ctx.send(embed=error_embed)

    @admin.command(name='güncelle', ignore_extra=False)
    async def a_update(self, ctx, user):
        dc_id = re.search("\d+", user).group()
        user = ctx.guild.get_member(int(dc_id))
        if user:
            await self.update(ctx, user)
        else:
            error_embed = self.create_message_embed(ctx.author, 'red', 'Aradığınız üye bulunamadı.')
            await ctx.send(embed=error_embed)

    @admin.command(name='profil', ignore_extra=False)
    async def a_profile(self, ctx, user):
        dc_id = re.search("\d+", user).group()
        user = ctx.guild.get_member(int(dc_id))
        if user:
            await self.profile(ctx, user)
        else:
            error_embed = self.create_message_embed(ctx.author, 'red', 'Aradığınız üye bulunamadı.')
            await ctx.send(embed=error_embed)

    @admin.command(name='sil', ignore_extra=False)
    async def a_delete(self, ctx, user):
        dc_id = re.search("\d+", user).group()
        user = ctx.guild.get_member(int(dc_id))
        if user:
            await self.delete(ctx, user)
        else:
            error_embed = self.create_message_embed(ctx.author, 'red', 'Aradığınız üye bulunamadı.')
            await ctx.send(embed=error_embed)

    @admin.command()
    async def configure(self, ctx, key, value):
        key = key.lower()
        if key not in self.configs[ctx.guild.id].keys():
            error_message = self.create_message_embed(ctx.author, 'red', f'"{key}" ayarlar arasında bulunamadı.')
            await ctx.send(embed=error_message)
            return

        value_id = re.search("\d+", value)
        if not value_id:
            error_message = self.create_message_embed(ctx.author, 'red', f'"{value}" değerinde bir problem var.')
            await ctx.send(embed=error_message)
            return

        value_id = value_id.group()
        await self.db.update_config(ctx.guild.id, key, int(value_id))
        await self.fetch_configs()
        response = self.create_message_embed(ctx.author, 'green', 'başarılı')
        await ctx.send(embed=response)
        return

        # user: <@!109079148533657600>
        # role: <@&118803033227395079>
        # channel: <#643428835387244585>

    @admin.command()
    async def register_guild(self, ctx):
        await self.db.insert_config(ctx.guild.id)
        await ctx.send(f"{ctx.guild.id} registered to database")
    # endregion

    # region main methods
    async def register(self, ctx, user, nickname):
        db_users = (await self.db.get_users(user.id))
        if db_users:
            error_embed = self.create_message_embed(user, 'red', f'Zaten {db_users[0]["r6_nick"]} nickiyle açılmış bir kayıdınız bulunuyor.')
            await ctx.send(embed=error_embed)
            return

        player = await self.fetch_player(nickname)

        # Check if player found
        if not player:
            error_embed = self.create_message_embed(user, 'red', f"`{nickname}` bulunamadı, doğru yazdığınızdan emin olun.")
            await ctx.send(embed=error_embed)
            return


        confirmation_embed = self.create_profile_embed(user, player['p_user'], player['name'], player['rank'],
                                                       player['level'], player['mmr'], datetime.date.today(), 'blue',
                                                       "Yukarıdaki bilgiler size aitse ✅, değilse ❌ emojisine tıklayın.")
        confirmed = await self.ask_question(ctx, confirmation_embed)

        if not confirmed:
            return

        # assign new role
        roles_assigned = await self.assign_role(user, player['rank'])
        if roles_assigned:

            # add to database
            await self.db.insert_user(user.id, user.name, player['p_id'], player['name'], player['level'],
                                      player['mmr'], datetime.date.today())
            # show result
            result_embed = self.create_profile_embed(user, player['p_user'], player['name'], player['rank'],
                                                    player['level'], player['mmr'], datetime.date.today(), 'blue',
                                                    "Kayıdınız tamamlanmıştır.")
            await ctx.send(embed=result_embed)


    async def update(self, ctx, user):
        # is registered
        db_users = (await self.db.get_users(user.id))
        if not db_users:
            error_embed = self.create_message_embed(user, 'red', f'Kaydınız bulunamadı. Güncellemeden önce kayıt olmanız gerekiyor.')
            await ctx.send(embed=error_embed)
            return

        db_user = db_users[0]

        player = await self.fetch_player(p_id=db_user['r6_id'])

        # assign new role
        roles_assigned = await self.assign_role(user, player['rank'])
        if roles_assigned:
            # update database
            await self.db.update_user(user.id, user.name, player['p_id'], player['name'], player['level'],
                                      player['mmr'], datetime.date.today())

            # show result
            result_embed = self.create_profile_embed(user, player['p_user'], player['name'], player['rank'],
                                                     player['level'], player['mmr'], datetime.date.today(), 'green',
                                                     "Profiliniz güncellenmiştir.")
            await ctx.send(embed=result_embed)


    async def profile(self, ctx, user):
        # is registered
        db_users = (await self.db.get_users(user.id))
        if not db_users:
            error_embed = self.create_message_embed(user, 'red', f'Kaydınız bulunamadı. Profil görüntülemeden önce kayıt olmanız gerekiyor.')
            await ctx.send(embed=error_embed)
            return
        db_user = db_users[0]

        result_embed = self.create_profile_embed(user, db_user['r6_id'], db_user['r6_nick'], self.find_rank(db_user),
                                                 db_user['level'], db_user['mmr'], datetime.date.today(), 'green')
        await ctx.send(embed=result_embed)

    async def delete(self, ctx, user):
        # is registered
        db_users = await self.db.get_users(user.id)
        if not db_users:
            error_embed = self.create_message_embed(user, 'red', f'Kaydınız bulunamadı. Kaydınızı silmek için önce kayıt olmanız gerekiyor.')
            await ctx.send(embed=error_embed)
            return

        db_user = db_users[0]

        # get confirmation
        confirmation_embed = self.create_profile_embed(user, db_user['r6_id'], db_user['r6_nick'], self.find_rank(db_user),
                                                       db_user['level'], db_user['mmr'], datetime.date.today(), 'blue',
                                                       "Kaydınız silme işlemini onaylıyorsanız ✅, onaylamıyorsanız ❌ emojisine tıklayın.")
        confirmed = await self.ask_question(ctx, confirmation_embed)

        if not confirmed:
            return

        # remove roles
        roles_to_remove = [role for role in user.roles if role.id in self.configs[user.guild.id].values()]
        await user.remove_roles(*roles_to_remove)

        # remove from db
        await self.db.delete_user(user.id)

        # response
        result_embed = self.create_message_embed(user, 'green', 'Kaydınız başarıyla silinmiştir.')
        await ctx.send(embed=result_embed)

    async def silent_update(self, db_user):
        player = await self.fetch_player(p_id=db_user['r6_id'])
        guild = self.bot.get_guild(list(self.configs.keys())[0])
        user = guild.get_member(db_user['dc_id'])

        # assign new role
        roles_assigned = await self.assign_role(user, player['rank'])
        if roles_assigned:
            # update database
            await self.db.update_user(db_user['dc_id'], db_user['dc_nick'], db_user['r6_id'], db_user['r6_nick'], player['level'],
                                      player['mmr'], datetime.date.today())

            # log result
            await self.log(guild.id, f"{str(user)} - ({db_user['r6_nick']}), MMR: {db_user['mmr']} -> {player['mmr']}")

    async def fetch_configs(self):
        config_columns = await self.db.get_config_columns()

        config_records = await self.db.get_all_configs()
        for config_record in config_records:
            guild_id = config_record['guild_id']
            self.configs[guild_id] = {}
            for config in config_columns:
                self.configs[guild_id][config] = config_record[config]

    # endregion


    # region helpers
    async def update_all(self):
        a = self.db.get_all_users()
        print(a)

    async def ask_question(self, ctx, embed):
        def check(reaction, user):
            return user == ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')

        # Send question
        msg = await ctx.send(embed=embed)

        # Add reactions
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')

        # Listen for reply
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if reaction.emoji == str(reaction.emoji) == '✅':
                # await msg.clear_reactions()
                return True
            if reaction.emoji == str(reaction.emoji) == '❌':
                # await msg.clear_reactions()
                embed = self.create_message_embed(ctx.author, 'red', "İşleminiz iptal edildi.")
                await ctx.send(embed=embed)
                return False
        except asyncio.TimeoutError:
            embed = self.create_message_embed(ctx.author, 'red', "Verilen süre içerisinde yanıt vermediğiniz için işleminiz iptal edildi.")
            await ctx.send(embed=embed)
            return False

    def create_message_embed(self, user, color, message):
        avatar = str(user.avatar_url)

        embed = discord.Embed(colour=discord.Colour(self.colors[color]),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        embed.set_author(name=str(user), icon_url=avatar)
        embed.set_footer(text="R6S Rank Bot")
        embed.add_field(name="R6S Rank Bot", value=f"**{message}**")
        return embed

    def create_profile_embed(self, user, p_user, r6_name, rank, level, mmr, ud, color, message=None):
        avatar = str(user.avatar_url)

        embed = discord.Embed(colour=discord.Colour(self.colors[color]),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        embed.set_author(name=str(user), icon_url=avatar)
        embed.set_thumbnail(url=f"https://ubisoft-avatars.akamaized.net/{p_user}/default_256_256.png")
        embed.set_footer(text="R6S Rank Bot")
        embed.add_field(name="Nickname", value=r6_name, inline=True)
        embed.add_field(name="Rank", value=rank, inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="MMR", value=mmr, inline=True)
        embed.add_field(name="Update Date", value=ud, inline=True)
        embed.add_field(name="\u200B", value="\u200B", inline=True)

        if message:
            embed.add_field(name="R6S Rank Bot",
                            value=f"**{message}**", inline=False)
        return embed

    def find_rank(self, player):
        if player.get('currentrank', 1) == 0:
            return "Unranked"
        mmr = player['mmr']
        if mmr <= 1:return "Unranked"
        elif mmr <= 1599:return "Copper"
        elif mmr <= 2099:return "Bronze"
        elif mmr <= 2599:return "Silver"
        elif mmr <= 3199:return "Gold"
        elif mmr <= 4399:return "Platinum"
        elif mmr <= 4999:return "Diamond"
        else: return "Champion"

    async def fetch_player(self, nickname=None, p_id=None):
        if p_id is None:
            p_id = await self.fetch_p_id(nickname)
            if not p_id:
                return None

        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://r6tab.com/api/player.php?p_id={p_id}') as resp:
                if resp.status == 200:
                    json_resp = await resp.json()
                    if json_resp['playerfound'] != True:
                        return None
                    try:
                        result = {}
                        result['p_id'] = p_id
                        result['mmr'] = json_resp['p_EU_currentmmr']
                        result['name'] = json_resp['p_name']
                        result['level'] = json_resp['p_level']
                        result['p_user'] = json_resp['p_user']
                        result['currentrank'] = json_resp.get('p_currentrank', 0)
                        result['rank'] = self.find_rank(result)
                        return result
                    except KeyError:
                        return None
                else:
                    raise ConnectionError

    async def fetch_p_id(self, nickname):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://r6tab.com/api/search.php?platform=uplay&search={nickname}') as resp:
                if resp.status == 200:
                    json_resp = await resp.json()
                    try:
                        return json_resp['results'][0]['p_id']
                    except KeyError:
                        return None
                else:
                    raise ConnectionError

    async def assign_role(self, user, rank):
        # find roles to remove and add
        roles_to_remove = [role for role in user.roles if role.id in self.configs[user.guild.id].values()]
        role_to_add = user.guild.get_role(self.configs[user.guild.id][rank.lower()])

        # remove roles
        await user.remove_roles(*roles_to_remove)

        # check if role to add still exists
        if not role_to_add:
            await self.log(user.guild.id, f'{rank} rolü bulunamadı - user: {user}, {user.id}')
            return False

        # add role
        await user.add_roles(role_to_add)
        return True


    async def log(self, guild_id, msg):
        log_channel_id = self.configs[guild_id]['log_channel']
        if log_channel_id:
            channel = self.bot.get_channel(log_channel_id)
            await channel.send(msg)
    # endregion


def setup(bot):
    bot.add_cog(MainCog(bot))

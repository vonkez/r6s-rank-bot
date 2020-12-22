import copy
import datetime
import traceback
from asyncio import Task, CancelledError
from math import ceil
from typing import Optional, List

from discord import Guild, Member, Role, TextChannel
from discord.ext import commands
from discord.ext.commands import NotOwner, CommandInvokeError, MissingRequiredArgument, CommandNotFound, \
    MemberNotFound, TooManyArguments, BadArgument
from loguru import logger
import discord

import sys
import asyncio
from embed import ProfileEmbed, MessageEmbed, ConfirmationTimeout, AutoUpdateEmbed, NicknameNoticeEmbed, \
    AnonymousMessageEmbed, Color
from models import DBUser
from stat_providers import Platform, R6Stats, Player, PlayerNotFound, RateLimitExceeded, RankShort
from utils import bot_channel_only, platform_converter, admin_only, not_banned, ChannelNotAllowed, UserBanned
from config import Config, RoleNotFound

"""
Stats

ef160d8b-8e2e-4eb6-ad36-5487b7c6b774
"""


class R6RCog(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.update_loop_frequency: int = 21600   # 6 hours
        self.config = config
        self.bot = bot
        self.stat_provider = R6Stats()
        self.loop_task = self.bot.loop.create_task(self.update_loop())
        self.update_task: Task = None
        logger.info("R6RCog initialized")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, CommandInvokeError):
            error = error.original
        if isinstance(error, PlayerNotFound):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken {error.args[0]} nicknameni kullanarak "
                        f"PlayerNotFound hatası aldı.")
        elif isinstance(error, MissingRequiredArgument):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken MissingRequiredArgument hatası aldı.")
        elif isinstance(error, TooManyArguments):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken TooManyArguments hatası aldı.")

        elif isinstance(error, CommandNotFound):
            logger.info(f"{ctx.author} {ctx.channel} kanalında CommandNotFound hatası aldı.")
        elif isinstance(error, ConnectionError):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken ConnectionError hatası aldı.")
            await self.log(f"{ctx.author} {ctx.command} komutunu kullanırken ConnectionError hatası aldı.", Color.RED,
                           False)
        elif isinstance(error, RateLimitExceeded):
            logger.error(f"{ctx.author} {ctx.command} komutunu kullanırken RateLimitExceeded hatası aldı.")
            await self.log(f"{ctx.author} {ctx.command} komutunu kullanırken RateLimitExceeded hatası aldı.", Color.RED,
                           True)
        elif isinstance(error, ConfirmationTimeout):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken ConfirmationTimeout hatası aldı")
        elif isinstance(error, MemberNotFound):
            logger.error(f"{ctx.author} {ctx.command} komutunu kullanırken MemberNotFound hatası aldı.")
            await self.log(f"{ctx.author} {ctx.command} komutunu kullanırken MemberNotFound hatası aldı.", Color.RED,
                           True)
        elif isinstance(error, BadArgument):
            logger.info(f"{ctx.author} {ctx.command} komutunu kullanırken BadArgument hatası aldı.")
        elif isinstance(error, RoleNotFound):
            logger.error(f"{ctx.author} {ctx.command} komutunu kullanırken RoleNotFound hatası aldı.")
            await self.log(f"{ctx.author} {ctx.command} komutunu kullanırken RoleNotFound hatası aldı.", Color.RED,
                           True)
        elif isinstance(error, NotOwner) or isinstance(error, ChannelNotAllowed):
            pass
        else:
            await self.log(f"{ctx.author} {ctx.command} komutunu kullanırken beklenmedik bir hata aldı.", Color.RED,
                           True)
            logger.error(f"{ctx.author} {ctx.command} komutunu kullanırken beklenmedik bir hata aldı.")
            logger.error("+global error handler ")
            logger.error(error)
            logger.error('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    async def update_loop(self):
        while True:
            await asyncio.sleep(self.update_loop_frequency)
            self.update_task = self.bot.loop.create_task(self.update_all())

    # region groups
    @bot_channel_only()
    @not_banned()
    @commands.group()
    async def r6r(self, ctx: commands.Context):
        pass

    @r6r.error
    async def r6r_error(self, ctx: commands.Context, error):
        if isinstance(error, ChannelNotAllowed):
            msg = f"{ctx.author}, {ctx.channel} kanalında komut kullanmaya çalıştı"
            logger.info(msg)
            await self.log(msg, Color.RED)
        elif isinstance(error, UserBanned):
            msg = f"{ctx.author}, {ctx.channel} kanalında banlıyken komut kullanmaya çalıştı"
            logger.info(msg)
            error_embed = MessageEmbed(ctx, "Botu kullanmaktan banlı olduğunuz için bu komutu kullanamassınız.")
            await error_embed.send_error()

    @admin_only()
    @r6r.group()
    async def admin(self, ctx):
        pass

    @admin.error
    async def admin_error(self, ctx, error):
        if isinstance(error, NotOwner):
            msg = f"{ctx.author}, {ctx.channel} kanalında yetkisi olmayan komut kullanmaya çalıştı."
            logger.info(msg)
            await self.log(msg, Color.RED)
    # endregions

    # region user commands
    @r6r.command(name="kayıt", ignore_extra=False)
    async def kayit(self, ctx: commands.Context, nickname: str, platform: platform_converter = Platform.PC) -> None:
        await ctx.invoke(self.a_kayit, nickname=nickname, platform=platform, member=ctx.author)

    @kayit.error
    async def kayit_error(self, ctx: commands.Context, error):
        await self.a_kayit_error(ctx, error)

    @r6r.command(name="güncelle", ignore_extra=False)
    async def guncelle(self, ctx: commands.Context) -> None:
        await ctx.invoke(self.a_guncelle, member=ctx.author)

    @guncelle.error
    async def guncelle_error(self, ctx: commands.Context, error):
        await self.a_guncelle_error(ctx, error)

    @r6r.command(ignore_extra=False)
    async def profil(self, ctx: commands.Context) -> None:
        await ctx.invoke(self.a_profil, member=ctx.author)

    @profil.error
    async def profil_error(self, ctx: commands.Context, error):
        await self.a_profil_error(ctx, error)

    @r6r.command(ignore_extra=False)
    async def sil(self, ctx: commands.Context) -> None:
        await ctx.invoke(self.a_sil, member=ctx.author)

    @sil.error
    async def sil_error(self, ctx: commands.Context, error):
        await self.a_sil_error(ctx, error)

    # endregion

    # region admin commands
    @admin.command(name="kayıt")
    async def a_kayit(self, ctx: commands.Context, nickname: str, platform: platform_converter,
                      member: discord.Member) -> None:
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()

        if db_user is not None:
            embed = MessageEmbed(ctx, message=f"Zaten `{db_user.r6_nick}` nickiyle açılmış bir kayıdınız bulunuyor.")
            await embed.send_error()
            return

        db_user: DBUser = await DBUser.filter(r6_nick=nickname).first()
        if db_user is not None:
            msg = f"Nick çakışması kayıtlı kullanıcı: {db_user.dc_id} - r6: {db_user.r6_nick}, kayıt olmaya çalışan: {ctx.author.mention}"
            logger.warning(msg)
            await self.log(msg, Color.RED, True)
            embed = MessageEmbed(ctx, message=f"`{db_user.r6_nick}` nickiyle açılmış bir kayıt bulunuyor. **Sizin olmayan nicklerle kayıt olmak yasaktır.** Eğer bu nick size aitse `#ticket` kanalından ticket oluşturunuz.")
            await embed.send_error()
            return

        player: Player = await self.stat_provider.get_player(nickname, platform)
        db_user = DBUser.create_from_player(ctx, player)

        confirmation_embed = ProfileEmbed(ctx, db_user, message="Yukarıdaki bilgiler size aitse ✅, değilse ❌ emojisine tıklayın.")
        confirmed: bool = await confirmation_embed.ask_confirmation()

        if not confirmed:
            cancel_embed = MessageEmbed(ctx, message="İşlem iptal edildi.")
            await cancel_embed.send_error()
            return

        await self.update_roles(db_user)
        await db_user.save()

        success_embed = ProfileEmbed(ctx, db_user, "Kayıdınız tamamlanmıştır.")
        await success_embed.send()

    @a_kayit.error
    async def a_kayit_error(self, ctx: commands.Context, error):
        if isinstance(error, CommandInvokeError):
            error = error.original
        if isinstance(error, PlayerNotFound):
            error_embed = MessageEmbed(ctx, f"`{error.args[0]}` bulunamadı, doğru yazdığınızdan emin olun.")
        elif isinstance(error, MissingRequiredArgument) or isinstance(error, TooManyArguments) or isinstance(error, BadArgument):
            error_embed = MessageEmbed(ctx, "Komutu yazarken yazım yanlışı yaptınız. `!r6r kayıt <nickname>` veya `!r6r kayıt <nickname> <platform>`")
        elif isinstance(error, ConnectionError):
            error_embed = MessageEmbed(ctx, "Stat sağlayıcına bağlanırken bir hata oluştu. Lütfen biraz sonra tekrar deneyin. Eğer hata devam ediyorsa sunucu yetkililerine bildirin.")
        elif isinstance(error, RateLimitExceeded):
            error_embed = MessageEmbed(ctx, "Bot aşırı yük altında, sonra tekrar deneyin.")
        elif isinstance(error, ConfirmationTimeout):
            error_embed = MessageEmbed(ctx, "Uzun süre cevap vermediğiniz için işleminiz iptal edildi.")
        elif isinstance(error, MemberNotFound) :
            error_embed = MessageEmbed(ctx, "Member bulunamadı. Sunucu yetkililerine bildirin.")
        elif isinstance(error, RoleNotFound):
            error_embed = MessageEmbed(ctx, f"Rol ataması yapılamadı. Sunucu yetkililerine bildirin.")
        else:
            error_embed = MessageEmbed(ctx, "Beklenmedik bir hata ile karşılaşıldı. Sunucu yetkililerine bildirin.")
        await error_embed.send_error()

    @admin.command(name="güncelle")
    async def a_guncelle(self, ctx: commands.Context, member: discord.Member) -> None:
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()
        original_db_user: DBUser = copy.deepcopy(db_user)

        if db_user is None:
            embed = MessageEmbed(ctx, message=f'Kaydınız bulunamadı. Güncellemeden önce kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        player: Player = await self.stat_provider.get_player(db_user.r6_nick, db_user.platform)

        if ctx.author.id == db_user.dc_id:
            db_user.update_from_player(player, True)
        else:
            db_user.update_from_player(player, False)

        await self.update_roles(db_user)
        await db_user.save()

        success_embed = ProfileEmbed(ctx, db_user, message="Profiliniz güncellenmiştir.", old_db_user=original_db_user)
        await success_embed.send()

    @a_guncelle.error
    async def a_guncelle_error(self, ctx: commands.Context, error):
        if isinstance(error, CommandInvokeError):
            error = error.original
        if isinstance(error, PlayerNotFound):
            error_embed = MessageEmbed(ctx, f"{error.args[0]} nicki ile kayıtlısınız. Yeni nicknameinizi kullanarak baştan kayıt olun. `!r6r sil` ardından `!r6r kayıt <nickname>` komutu ile bunu yapabilirsiniz.")
        elif isinstance(error, MissingRequiredArgument) or isinstance(error, TooManyArguments):
            error_embed = MessageEmbed(ctx, "Komutu yazarken yazım yanlışı yaptınız.\n`!r6r güncelle` yazmanız yeterli")
        elif isinstance(error, ConnectionError):
            error_embed = MessageEmbed(ctx, "Stat sağlayıcına bağlanırken bir hata oluştu. Lütfen biraz sonra tekrar deneyin. Eğer hata devam ediyorsa sunucu yetkililerine bildirin.")
        elif isinstance(error, RateLimitExceeded):
            error_embed = MessageEmbed(ctx, "Bot aşırı yük altında, sonra tekrar deneyin.")
        elif isinstance(error, MemberNotFound):
            error_embed = MessageEmbed(ctx, "Member bulunamadı. Sunucu yetkililerine bildirin.")
        else:
            error_embed = MessageEmbed(ctx, "Beklenmedik bir hata ile karşılaşıldı. Sunucu yetkililerine bildirin.")
        await error_embed.send_error()

    @admin.command(name="profil")
    async def a_profil(self, ctx: commands.Context, member: discord.Member) -> None:
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()

        if db_user is None:
            embed = MessageEmbed(ctx, message=f'Kaydınız bulunamadı. Profil komutunu kullanmak için kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        db_user.last_command = datetime.datetime.today()
        db_user.inactive = False
        await db_user.save()

        success_embed = ProfileEmbed(ctx, db_user)
        await success_embed.send()

    @a_profil.error
    async def a_profil_error(self, ctx: commands.Context, error):
        if isinstance(error, CommandInvokeError):
            error = error.original
        elif isinstance(error, MissingRequiredArgument) or isinstance(error, TooManyArguments):
            error_embed = MessageEmbed(ctx, "Komutu yazarken yazım yanlışı yaptınız.\n`!r6r profil` yazmanız yeterli.")
        else:
            error_embed = MessageEmbed(ctx, "Beklenmedik bir hata ile karşılaşıldı. Sunucu yetkililerine bildirin.")

        await error_embed.send_error()

    @admin.command(name="sil")
    async def a_sil(self, ctx: commands.Context, member: discord.Member) -> None:
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()

        if db_user is None:
            embed = MessageEmbed(ctx, message=f'Kaydınız bulunamadı. Sil komutunu kullanmak için kayıt olmanız gerekiyor.')
            await embed.send_error()
            return

        confirmation_embed = ProfileEmbed(ctx, db_user,
                                          "Kayıt silme işlemini onaylıyorsanız ✅, onaylamıyorsanız ❌ emojisine tıklayın.")
        confirmed: bool = await confirmation_embed.ask_confirmation()
        if confirmed:
            await self.clear_roles(ctx, db_user)
            await db_user.delete()
            embed = MessageEmbed(ctx, message=f'Kaydınız başarıyla silinmiştir.')
            await embed.send()
            return
        else:
            cancel_embed = MessageEmbed(ctx, message="İşlem iptal edildi.")
            await cancel_embed.send_error()

    @a_sil.error
    async def a_sil_error(self, ctx: commands.Context, error):
        if isinstance(error, CommandInvokeError):
            error = error.original
        if isinstance(error, MemberNotFound):
            error_embed = MessageEmbed(ctx, "Member bulunamadı. Sunucu yetkililerine bildirin.")
        elif isinstance(error, ConfirmationTimeout):
            error_embed = MessageEmbed(ctx, "Uzun süre cevap vermediğiniz için işleminiz iptal edildi.")
        elif isinstance(error, MissingRequiredArgument) or isinstance(error, TooManyArguments):
            error_embed = MessageEmbed(ctx, "Komutu yazarken yazım yanlışı yaptınız.\n`!r6r sil` yazmanız yeterli.")
        else:
            error_embed = MessageEmbed(ctx, "Beklenmedik bir hata ile karşılaşıldı. Sunucu yetkililerine bildirin.")
        await error_embed.send_error()

    @admin.command()
    async def ban(self, ctx: commands.Context, member: discord.Member) -> None:
        banned = await self.config.is_banned(member)
        if banned:
            embed = MessageEmbed(ctx, "Kullanıcı daha önce banlanmış")
            await embed.send_error()
        else:
            await self.config.add_banned(member)
            db_user = await DBUser.filter(dc_id=member.id).first()
            if db_user is not None:
                await db_user.delete()
            embed = MessageEmbed(ctx, "Kullanıcı banlandı")
            await embed.send()

    @admin.command()
    async def unban(self, ctx: commands.Context, member: discord.Member) -> None:
        banned = await self.config.is_banned(member)
        if not banned:
            embed = MessageEmbed(ctx, "Kullanıcı banlı değil")
            await embed.send_error()
        else:
            await self.config.remove_banned(member)
            embed = MessageEmbed(ctx, "Kullanıcının banı kaldırıldı")
            await embed.send()

    @admin.command()
    async def detay(self, ctx: commands.Context, member: discord.Member) -> None:
        db_user: DBUser = await DBUser.filter(dc_id=member.id).first()
        if db_user is None:
            embed = MessageEmbed(ctx, "Aradığınız kullanıcı bulunamadı")
            await embed.send_error()
            return
        else:
            msg = f"{db_user.dc_id=}\n{db_user.dc_nick=}\n{db_user.ubisoft_id=}\n" \
                  f"{db_user.uplay_id=}\n{db_user.r6_nick=}\n{db_user.kd=}\n" \
                  f"{db_user.level=}\n{db_user.mmr=}\n{db_user.rank=}\n" \
                  f"{db_user.rank_short.value=}\n{db_user.last_update=}\n{db_user.last_command=}\n" \
                  f"{db_user.last_change=}\n{db_user.platform.value=}\n{db_user.inactive=}\n"
            embed = MessageEmbed(ctx, msg)
            await embed.send()

    @admin.command(name="herkesi_güncelle")
    async def herkesi_guncelle(self, ctx: commands.Context) -> None:
        if self.update_task is not None:
            self.update_task.cancel()
        self.update_task = self.bot.loop.create_task(self.update_all())

    @admin.command(name="herkesi_zorla_güncelle")
    async def herkesi_zorla_guncelle(self, ctx: commands.Context) -> None:
        if self.update_task is not None:
            self.update_task.cancel()
        self.update_task = self.bot.loop.create_task(self.update_all(True))

    @admin.command(name="güncelleme_iptal")
    async def guncelleme_iptal(self, ctx: commands.Context) -> None:
        if self.update_task is not None:
            self.update_task.cancel()

    @admin.command(name="rankları_sıfırla")
    async def ranklari_sifirla(self, ctx: commands.Context) -> None:
        embed = MessageEmbed(ctx, "**TÜM KULLANICILARIN RANKLARINI UNRANKED OLARAK DEĞİŞTİRECEKSİN! DEVAM ETMEK İSTİYOR MUSUN?**")
        confirmed = False
        try:
            confirmed = await embed.ask_confirmation()
        except ConfirmationTimeout:
            embed = MessageEmbed(ctx, "Cevap vermedğiniz için işlem iptal edildi.")
            await embed.send_error()
            return

        if confirmed:
            counter = 0
            all_users = await DBUser.all()
            msg = await ctx.send(f"{counter}/{len(all_users)}")
            for user in all_users:
                user.rank = "Unranked"
                user.rank_short = RankShort.UNRANKED
                try:
                    await self.update_roles(user)
                except MemberNotFound:
                    pass
                await user.save()
                await asyncio.sleep(0.2)
                counter += 1
                if counter % 30 == 0:
                    await msg.edit(content=f"{counter}/{len(all_users)}")

            await msg.edit(content=f"{counter}/{len(all_users)}")

            embed = MessageEmbed(ctx, "İşlem tamamlandı.")
            await embed.send()
        else:
            embed = MessageEmbed(ctx, "İşlem iptal edildi.")
            await embed.send_error()

    @admin.command(name="güncelleme_tarihlerini_yay")
    async def guncelleme_tarihlerini_yay(self, ctx: commands.Context) -> None:
        all_users = await DBUser.all()
        frequency = datetime.timedelta(days=await self.config.get_frequency())
        update_loop_frequency = datetime.timedelta(seconds=self.update_loop_frequency)
        today = datetime.datetime.today()

        # Split all users into n parts
        ul = len(all_users)
        n = frequency // update_loop_frequency
        splitted_users = [all_users[i:i + ceil(ul/n)] for i in range(0, ul, ceil(ul/n))]

        embed = MessageEmbed(ctx, f"{ul} adet kullanıcının son güncelleme tarihleri {frequency} boyunca, {update_loop_frequency} aralıklarla dağıtılacak. Devam etmek istiyor musunuz?")
        confirmed = await embed.ask_confirmation()
        if confirmed:
            counter = 0
            msg = await ctx.send(f"{counter}/{ul}")
            for i in range(len(splitted_users)):
                users = splitted_users[i]
                for user in users:
                    user.last_update = today - (update_loop_frequency * i)
                    await user.save()
                    counter += 1
                    if counter % 30 == 0:
                        await msg.edit(content=f"{counter}/{ul}")

            await msg.edit(content=f"{counter}/{ul}")
            embed = MessageEmbed(ctx, "İşlem tamamlandı")
            await embed.send()
        else:
            embed = MessageEmbed(ctx, "İşlem iptal edildi.")
            await embed.send()

    @admin.command(name="inaktif_kontrol")
    async def inaktif_kontrol(self, ctx: commands.Context) -> None:
        guild: Guild = self.bot.guilds[0]
        inactive_users = await DBUser.filter(inactive=True).all()

        total_inactive_users = len(inactive_users)
        activated_users = 0
        left_users = 0
        errors = 0
        counter = 0
        msg = await ctx.send(f"{left_users} ayrıldı - {activated_users} activated - {errors} hata - {counter}/{total_inactive_users}")
        for db_user in inactive_users:
            member: Optional[Member] = guild.get_member(db_user.dc_id)
            if member is None:
                left_users += 1
            else:
                try:
                    player: Player = await self.stat_provider.get_player(db_user.r6_nick, db_user.platform)
                    db_user.update_from_player(player, False)
                except Exception as error:
                    if error is PlayerNotFound:
                        pass
                    else:
                        errors += 1
                        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

                await asyncio.sleep(3)

                if db_user.inactive is False:
                    activated_users += 1
                    await self.update_roles(db_user)
                    await db_user.save()
            counter += 1
            if counter % 5 == 0:
                await msg.edit(content=f"{left_users} ayrıldı - {activated_users} activated - {errors} hata - {counter}/{total_inactive_users}")
        await msg.edit(content=f"{left_users} ayrıldı - {activated_users} activated - {errors} hata - {counter}/{total_inactive_users}")
        await ctx.send("İşlem tamamlandı")

    @admin.command(name="inaktif_sil")
    async def inaktif_sil(self, ctx: commands.Context, gun: int) -> None:
        inactive_users = await DBUser.filter(inactive=True).all()
        today = datetime.datetime.today()
        limit = datetime.timedelta(days=gun)
        selected_inactive_users = [user for user in inactive_users if today - user.last_change > limit]

        embed = MessageEmbed(ctx, f"{len(inactive_users)} inaktif kullanıcı içeisinden {len(selected_inactive_users)} tanesi silinecek. Devam etmek istiyor musunuz? ")
        try:
            confirmed = await embed.ask_confirmation()
        except ConfirmationTimeout:
            embed = MessageEmbed(ctx, "Cevap vermediğiniz için işlem iptal edildi.")
            await embed.send_error()
            return

        if confirmed:
            for user in selected_inactive_users:
                await user.delete()
            embed = MessageEmbed(ctx, f"İşlem tamamlandı, {len(selected_inactive_users)} inaktif kullanıcı başarıyla silindi.")
            await embed.send()
        else:
            embed = MessageEmbed(ctx, "İşlem iptal edildi.")
            await embed.send()

    @admin.command(name="guild_kaydet")
    async def guild_kaydet(self, ctx: commands.Context) -> None:
        pass

    @admin.command(name="kanal_ekle")
    async def kanal_ekle(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        allowed = await self.config.is_channel_allowed(channel)
        if allowed:
            error_embed = MessageEmbed(ctx, "Bu kanal daha önce eklenmiş. *kanal_çıkar* komutu ile kanalı çıkarabilrsiniz.")
            await error_embed.send_error()
            return
        else:
            await self.config.add_allowed_channel(channel)
            embed = MessageEmbed(ctx, "Kanal başarıyla eklendi.")
            await embed.send()

    @admin.command(name="kanal_çıkar")
    async def kanal_cikar(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        allowed = await self.config.is_channel_allowed(channel)
        if not allowed:
            error_embed = MessageEmbed(ctx, "Bu kanal daha önce eklenmedi. *kanal_ekle* komutu ile kanalı ekleyebilirsiniz.")
            await error_embed.send_error()
            return
        else:
            await self.config.remove_allowed_channel(channel)
            embed = MessageEmbed(ctx, "Kanal başarıyla çıkarıldı.")
            await embed.send()

    @admin.command()
    async def rol_ayarla(self, ctx: commands.Context, rol_text: str, rol: discord.Role) -> None:
        try:
            platform: Platform = Platform[rol_text.upper()]
            await self.config.set_platform_role(platform, rol)
            embed = MessageEmbed(ctx, "Platform rolü başarıyla ayarlandı")
            await embed.send()
            return
        except KeyError:
            pass
        try:
            rank: RankShort = RankShort[rol_text.upper()]
            await self.config.set_rank_role(rank, rol)
            embed = MessageEmbed(ctx, "Rank rolü başarıyla ayarlandı")
            await embed.send()
            return
        except KeyError:
            pass

        embed = MessageEmbed(ctx, "Aradığınız rol bulunamadı.")
        await embed.send_error()

    @admin.command()
    async def log_ayarla(self, ctx: commands.Context, channel: discord.TextChannel) -> None:
        await self.config.set_log_channel(channel)
        embed = MessageEmbed(ctx, "Log kanalı başarıyla ayarlandı.")
        await embed.send()

    @admin.command(name="sıklık_ayarla")
    async def sklk_ayarla(self, ctx: commands.Context, gun: int) -> None:
        await self.config.set_frequency(gun)
        embed = MessageEmbed(ctx, "Sıklık başarıyla ayarlandı.")
        await embed.send()
    # endregion

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

    async def clear_roles(self, ctx: commands.Context, db_user: DBUser) -> None:
        guild: Guild = ctx.guild
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

    async def update_all(self, ignore_expiration: bool = False):
        try:
            logger.info(f"Auto update started")
            log_channel_id: int = await self.config.get_log_channel()
            guild: Guild = self.bot.guilds[0]
            log_channel: TextChannel = self.bot.get_channel(log_channel_id)
            frequency = datetime.timedelta(days=await self.config.get_frequency())
            inactive_limit = datetime.timedelta(weeks=5)

            today = datetime.datetime.today()
            all_users: List[DBUser] = await DBUser.all()
            expired_users: List[DBUser] = []
            inactive_users: List[DBUser] = []
            new_inactive_users: List[DBUser] = []
            failed_user_updates: List[DBUser] = []
            important_error_occcured: bool = False

            for user in all_users:
                if user.inactive:
                    inactive_users.append(user)
                elif today - user.last_change > inactive_limit:
                    new_inactive_users.append(user)
                elif ignore_expiration:
                    expired_users.append(user)
                elif today - user.last_update > frequency:
                    expired_users.append(user)

            for user in new_inactive_users:
                user.inactive = True
                await user.save()
                logger.info(f"{user.dc_nick} marked as inactive")

            update_embed = AutoUpdateEmbed(len(all_users), len(expired_users), len(inactive_users) + len(new_inactive_users))
            msg = await log_channel.send(embed=update_embed)

            for i in range(1, len(expired_users)+1):
                db_user = expired_users[i-1]
                original_db_user: DBUser = copy.deepcopy(db_user)
                member: Member = guild.get_member(db_user.dc_id)
                try:
                    if member is None:
                        raise MemberNotFound(None)

                    player: Player = await self.stat_provider.get_player(db_user.r6_nick,
                                                                         db_user.platform)
                    db_user.update_from_player(player, False)
                    await self.update_roles(db_user)
                    await db_user.save()
                    update_embed.update_progress(i)
                    log_message = f"{i}. {db_user.dc_nick} - {db_user.r6_nick} || {db_user.rank} -> {original_db_user.rank}"
                    update_embed.add_log(log_message)
                    logger.info(log_message)


                except PlayerNotFound:
                    successful = await self.send_notice(member, db_user)
                    error_message: str

                    if successful:
                        error_message = f"PlayerNotFound {db_user.r6_nick} - r6: {db_user.r6_nick} - notice sent"
                    else:
                        error_message = f"PlayerNotFound {db_user.r6_nick} - r6: {db_user.r6_nick} - forbidden"

                    logger.warning(error_message)
                    update_embed.add_log(error_message)
                    failed_user_updates.append(db_user)

                    db_user.inactive = True
                    await db_user.save()
                except ConnectionError:
                    logger.error(f"Connection error {db_user.r6_nick}")
                    update_embed.add_log(f"Connection error {db_user.r6_nick}")
                    important_error_occcured = False
                    failed_user_updates.append(db_user)
                except RateLimitExceeded:
                    logger.error(f"RateLimitExceeded error {db_user.r6_nick}")
                    update_embed.add_log(f"RateLimitExceeded error {db_user.r6_nick}")
                    important_error_occcured = True
                    failed_user_updates.append(db_user)
                except MemberNotFound:
                    # Probably left the server
                    logger.warning(f"MemberNotFound error {db_user.r6_nick}")
                    update_embed.add_log(f"MemberNotFound error {db_user.r6_nick}")
                    failed_user_updates.append(db_user)
                    db_user.inactive = True
                    await db_user.save()

                await asyncio.sleep(3)
                if (i % 5 == 0) or (i == len(expired_users)):
                    await msg.edit(embed=update_embed)

            update_embed.add_log("Otomatik güncelleme tamamlandı")
            logger.info("Otomatik güncelleme tamamlandı")
            # update_embed.update_progress(len(expired_users))
            await msg.edit(embed=update_embed)

            if (fails := len(failed_user_updates)) > 0:
                msg = f"{fails} tane kullanıcının güncellemesinden hata oluştu"
                if important_error_occcured:
                    msg += "(Kontrol edilmesi gereken hatalar oluştu)"
                await self.log(msg, Color.RED, important_error_occcured)

        except CancelledError:
            logger.warning("Automatic update cancelled")
            await self.log("Automatic update cancelled")

    async def send_notice(self, member: Member, db_user: DBUser) -> bool:
        notice_embed = NicknameNoticeEmbed(db_user)
        try:
            await member.send("https://discord.gg/gpM5F7Vd8A", embed=notice_embed)
            return True
        except discord.Forbidden:
            return False

    async def log(self, msg: str, color: Color = Color.GREEN, important: bool = False):
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

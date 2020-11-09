import asyncio
import datetime
import time
from enum import Enum
from typing import List

import discord
from discord.ext.commands import Context
from models import DBUser


class ConfirmationTimeout(asyncio.TimeoutError):
    pass


class Color(Enum):
    GREEN = 0x259C34
    RED = 0xB2283D
    BLUE = 0x4AA8FF


class BaseEmbed(discord.Embed):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx: Context = kwargs.get("ctx")

    async def send(self) -> None:
        self.colour = Color.GREEN.value
        await self.ctx.send(embed=self)

    async def send_error(self) -> None:
        self.colour = Color.RED.value
        await self.ctx.send(embed=self)

    async def ask_confirmation(self) -> bool:
        # TODO: Check which message reaction came from
        def check(reaction, user):
            return user == self.ctx.message.author and (str(reaction.emoji) == '✅' or str(reaction.emoji) == '❌')

        self.colour = Color.BLUE.value

        # Send question
        msg = await self.ctx.send(embed=self)

        # Add reactions
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')

        # Listen for reply
        try:
            reaction, user = await self.ctx.bot.wait_for('reaction_add', timeout=30.0, check=check)
            if reaction.emoji == str(reaction.emoji) == '✅':
                # await msg.clear_reactions()
                return True
            if reaction.emoji == str(reaction.emoji) == '❌':
                # await msg.clear_reactions()
                return False

        except asyncio.TimeoutError:
            raise ConfirmationTimeout()


class ProfileEmbed(BaseEmbed):
    def __init__(self, ctx: Context, db_user: DBUser, message: str = None, old_db_user: DBUser = None):
        timestamp = datetime.datetime.utcfromtimestamp(time.time())
        super().__init__(timestamp=timestamp, ctx=ctx)

        avatar_url = str(ctx.author.avatar_url)
        author_str = str(ctx.author)

        if old_db_user is not None:
            rank = db_user.rank if db_user.rank == old_db_user.rank else f"{old_db_user.rank} -> {db_user.rank}"
            kd = f"{db_user.kd:.1f}" if db_user.kd == old_db_user.kd else f"{old_db_user.kd:.1f} -> {db_user.kd:.1f}"
            mmr = str(db_user.mmr) if db_user.mmr == old_db_user.mmr else f"{old_db_user.mmr} -> {db_user.mmr}"
            level = str(db_user.level) if db_user.level == old_db_user.level else f"{old_db_user.level} -> {db_user.level}"
        else:
            rank = db_user.rank
            kd = f"{db_user.kd:.1f}"
            mmr = str(db_user.mmr)
            level = str(db_user.level)
        self.set_author(name=author_str, icon_url=avatar_url)
        self.set_thumbnail(url=f"https://ubisoft-avatars.akamaized.net/{db_user.uplay_id}/default_256_256.png")
        self.set_footer(text="R6S-TR BOT", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.add_field(name="Nickname", value=db_user.r6_nick, inline=True)
        self.add_field(name="Rank", value=rank, inline=True)
        self.add_field(name="Level", value=level, inline=True)
        self.add_field(name="K/D", value=kd, inline=True)
        self.add_field(name="MMR", value=mmr, inline=True)
        self.add_field(name="Platform", value=db_user.platform.name, inline=True)
        self.add_field(name="\u200B", value="\u200B", inline=True)
        if message is not None:
            self.add_field(name="R6S Rank Bot", value=f"**{message}**", inline=False)


class MessageEmbed(BaseEmbed):
    def __init__(self, ctx: Context, message: str):
        timestamp = datetime.datetime.utcfromtimestamp(time.time())
        super().__init__(timestamp=timestamp, ctx=ctx)

        avatar_url = str(ctx.author.avatar_url)
        author_str = str(ctx.author)

        self.set_author(name=author_str, icon_url=avatar_url)
        self.set_footer(text="R6S-TR BOT", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.add_field(name="R6S Rank Bot", value=f"**{message}**")


class NicknameNoticeEmbed(discord.Embed):
    def __init__(self, db_user: DBUser):
        timestamp = datetime.datetime.utcfromtimestamp(time.time())
        super().__init__(timestamp=timestamp)
        self.colour = Color.RED.value
        self.set_author(name="Rainbow Six Siege TR", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.add_field(name="Rainbow Six Siege Nick Değişikliği", value=f"R6S nickinin artık **{db_user.r6_nick}** olmadığını farkettik, bu sebeple rank  rolünü güncelleyemiyoruz. Yeniden kayıt olarak bu problemi çözebilirsin.", inline=False)
        self.add_field(name="Yeniden Kayıt",
                               value='`#rank-onay` kanalına gidin\n`!r6r sil` yazın silme işlemini onaylayın\n`!r6r kayıt <nickname>` yazıp bilgileriniz doğruysa işlemi onaylayın', inline=False)
        self.add_field(name="Destek", value="Destek için `#ticket` kanalından ticket açabilirsin.")
        self.set_footer(text="R6S-TR BOT", icon_url="https://i.hizliresim.com/PURMY6.png")


class AnonymousMessageEmbed(discord.Embed):
    def __init__(self, message: str, color: Color, **kwargs):
        super().__init__(**kwargs, colour=color.value)
        self.set_author(name="Log Message", icon_url="https://i.hizliresim.com/PURMY6.png")
        # self.set_footer(text="R6S-TR BOT", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.description = f"**{message}**"


class AutoUpdateEmbed(discord.Embed):
    def __init__(self, total_users: int, users_to_update: int, inactive_users: int, **kwargs):
        timestamp = datetime.datetime.utcfromtimestamp(time.time())
        super().__init__(timestamp=timestamp, **kwargs)
        self.start_time = datetime.datetime.today()
        self.logs: List[str] = []
        self.total_progress = users_to_update
        self.progress = -1
        self.percent_progress = 0
        self.est_time = None

        self.set_author(name="Otomatik güncelleme", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.set_footer(text="R6S-TR BOT", icon_url="https://i.hizliresim.com/PURMY6.png")
        self.add_field(name="Tüm kullanıcılar", value=str(total_users), inline=True)
        self.add_field(name="Güncellenecek kullanıcılar", value=str(users_to_update), inline=True)
        self.add_field(name="İnaktif kullanıcılar", value=str(inactive_users), inline=True)

        self.add_field(name="Log", value=f"```{self.get_last_logs()}```", inline=False)
        self.add_field(name=f"{self.progress}/{self.total_progress} - %{self.percent_progress} - {self.est_time}",
                       value=self.get_progress_bar(), inline=False)

    def update_progress(self, progress: int) -> None:
        self.progress = progress
        self.percent_progress = int(self.progress / self.total_progress * 100)
        elapsed_time = datetime.datetime.today() - self.start_time
        time_per_progress = elapsed_time / progress
        remaining_progress = self.total_progress - self.progress
        remaining_time = time_per_progress * remaining_progress
        self.est_time = datetime.timedelta(seconds=remaining_time.seconds)  # new object is created to get rid of microseconds
        self.update_fields()

    def add_log(self, log_message: str) -> None:
        self.logs.append(log_message)
        self.update_fields()

    def get_last_logs(self) -> str:
        return '\n'.join(self.logs[-5:])

    def get_progress_bar(self) -> str:
        filled_amount = int(self.percent_progress*0.35)
        empty_amount = 35-filled_amount
        bar = "◁" + "█"*filled_amount + "─"*empty_amount + "▷"
        return bar

    def update_fields(self) -> None:
        self.remove_field(-1)
        self.remove_field(-1)
        self.add_field(name="Log", value=f"```\n{self.get_last_logs()}```", inline=False)
        self.add_field(name=f"{self.progress}/{self.total_progress} - %{self.percent_progress} - {self.est_time}",
                       value=self.get_progress_bar(), inline=False)

        #print(self.get_last_logs().__repr__())
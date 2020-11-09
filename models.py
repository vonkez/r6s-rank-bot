from discord.ext.commands import Context
from tortoise import fields
from tortoise.models import Model
from stat_providers import Platform, Player, RankShort
from datetime import datetime


class DBUser(Model):
    dc_id = fields.BigIntField(pk=True)
    dc_nick = fields.TextField()
    ubisoft_id = fields.TextField()
    uplay_id = fields.TextField()
    r6_nick = fields.TextField()
    kd = fields.FloatField()
    level = fields.IntField(null=True)
    mmr = fields.IntField()
    rank = fields.TextField()
    rank_short = fields.CharEnumField(RankShort)
    last_update = fields.DatetimeField()
    last_command = fields.DatetimeField()
    last_change = fields.DatetimeField()
    platform = fields.CharEnumField(Platform)
#    banned = fields.BooleanField()
    inactive = fields.BooleanField()

    def update_from_player(self, player: Player, is_from_command: bool):
        if is_from_command:
            self.last_command = datetime.today()
            self.inactive = False
        if (self.mmr != player.mmr) or (self.rank != player.rank):
            self.last_change = datetime.today()
            self.inactive = False
        self.ubisoft_id = player.ubisoft_id
        self.uplay_id = player.uplay_id
        self.kd = player.kd
        self.level = player.level
        self.mmr = player.mmr
        self.rank = player.rank
        self.rank_short = player.rank_short
        self.last_update = datetime.today()

    @staticmethod
    def create_from_player(ctx: Context, player: Player) -> 'DBUser':
        db_user = DBUser(
            dc_id=ctx.author.id,
            dc_nick=ctx.author.name,
            ubisoft_id=player.ubisoft_id,
            uplay_id=player.uplay_id,
            r6_nick=player.name,
            kd=player.kd,
            level=player.level,
            mmr=player.mmr,
            rank=player.rank,
            rank_short=player.rank_short,
            last_update=datetime.today(),
            last_command=datetime.today(),
            last_change=datetime.today(),
            platform=player.platform,
            inactive=False
        )
        return db_user


class Ban(Model):
    discord_id = fields.BigIntField(pk=True)


class AllowedChannel(Model):
    channel_id = fields.BigIntField(pk=True)


class RankRoles(Model):
    unranked = fields.BigIntField(null=True)
    copper = fields.BigIntField(null=True)
    bronze = fields.BigIntField(null=True)
    silver = fields.BigIntField(null=True)
    gold = fields.BigIntField(null=True)
    platinum = fields.BigIntField(null=True)
    diamond = fields.BigIntField(null=True)
    champions = fields.BigIntField(null=True)


class PlatformRoles(Model):
    pc = fields.BigIntField(null=True)
    ps4 = fields.BigIntField(null=True)
    xbox = fields.BigIntField(null=True)


class Configs(Model):
    guild = fields.BigIntField(null=True)
    log_channel = fields.BigIntField(null=True)
    frequency = fields.IntField(null=True)

    class Meta:
        table = "new_configs"

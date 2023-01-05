import os

from loguru import logger
from siegeapi import Auth

from stat_providers.stat_provider import StatProvider, PlayerNotFound, Player, RankShort, Platform


class SApi(StatProvider):
    def __init__(self):
        self.auth = Auth(os.environ["UBI_EMAIL"], os.environ["UBI_PASS"], creds_path="creds.json")
        logger.info("SApi initialized")

    async def get_player(self, nickname: str, platform: Platform) -> Player:
        try:
            sapi_player = await self.auth.get_player(name=nickname, platform=self.convert_enum(platform))
            await sapi_player.load_playtime()
            await sapi_player.load_ranked_v2()

            player = Player()
            player.name = sapi_player.name
            player.level = sapi_player.level
            player.platform = platform
            player.uplay_id = sapi_player.id
            player.ubisoft_id = sapi_player.id  # ??
            player.avatar_146 = sapi_player.profile_pic_url_146
            player.avatar_256 = sapi_player.profile_pic_url_256
            player.mmr = sapi_player.ranked_profile.rank_points
            player.rank = sapi_player.ranked_profile.rank
            player.rank_short = RankShort[player.rank.split(" ")[0].upper()]
            player.rank_no = sapi_player.ranked_profile.rank_id

            try:
                player.kd = round(sapi_player.ranked_profile.kills / sapi_player.ranked_profile.deaths, 2)
            except:
                player.kd = 0

            return player
        except Exception as e:
            if e.args[0] == "No results":
                raise PlayerNotFound(nickname)
            else:
                raise e

    def convert_enum(self, platform: Platform) -> str:
        if platform is Platform.PC:
            return "uplay"
        elif platform is Platform.XBOX:
            return "xbl"
        elif platform is Platform.PS4:
            return "psn"

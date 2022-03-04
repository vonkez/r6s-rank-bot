import base64
import os
import time
from typing import Dict

import aiohttp
from loguru import logger

from stat_providers.rate_limiter import RateLimitExceeded
from stat_providers.stat_provider import StatProvider, PlayerNotFound, Player, RankShort, Platform


class StatsDB(StatProvider):

    def __init__(self):
        token_string = os.environ["STATSDB_ID"] + ":" + os.environ["STATSDB_PW"]
        token_bytes = token_string.encode("utf-8")
        self.AUTH_TOKEN: str = base64.b64encode(token_bytes).decode()
        self.SEASON: str = os.environ["R6_SEASON"]
        self.headers: Dict[str, str] = {'Authorization': 'Basic ' + self.AUTH_TOKEN}
        self.limit_remaining: int = 500
        self.reset_timestamp: int = 0
        logger.info("StatsDB initialized")

    async def get_player(self, nickname: str, platform: Platform) -> Player:
        platform_value = self.convert_enum(platform)
        json = await self.fetch_player(platform_value, nickname)
        player = self.player_from_json(json)
        player.platform = platform
        return player

    def player_from_json(self, json) -> Player:
        player = Player()
        player.name = json["payload"]["user"]["nickname"]
        player.level = int(json["payload"]["preview"][2]["value"])
        player.kd = float(json["payload"]["preview"][0]["value"])
        player.uplay_id = json["payload"]["user"]["avatar"][38:74]
        player.ubisoft_id = json["payload"]["user"]["id"]
        player.avatar_146 = json["payload"]["user"]["smallAvatar"]
        player.avatar_256 = json["payload"]["user"]["avatar"]
        player.mmr = int(json["payload"]["stats"]["seasonal"]["ranked"]["mmr"])
        player.rank_no = int(json["payload"]["stats"]["seasonal"]["ranked"]["rank"])
        player.rank = self.rank_no_to_rank(player.rank_no)
        # player.rank_image: str

        rank_short_str = player.rank.split()[0]
        player.rank_short = RankShort[rank_short_str.upper()]
        return player

    async def fetch_player(self, platform: str, nickname: str):
        if self.limit_remaining < 5:
            if self.reset_timestamp < time.time():
                self.limit_remaining = 500
            else:
                logger.warning("StatsDB ratelimit exceeded")
                raise RateLimitExceeded()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"https://api.statsdb.net/r6/{platform}/player/{nickname}") as resp:
                try:
                    self.limit_remaining = int(resp.headers["x-rate-limit-remaining"])
                    self.reset_timestamp = int(resp.headers["x-rate-limit-reset"])
                except:
                    logger.info("StatDB missing ratelimit header")
                    pass

                if resp.status == 200:
                    json_resp = await resp.json()
                    return json_resp
                elif resp.status == 404:
                    raise PlayerNotFound(nickname)
                elif resp.status == 429:
                    logger.critical("StatsDB ratelimit exceeded")
                    raise RateLimitExceeded()
                else:
                    logger.error("StatsDB request failed")
                    logger.error("Request info:" + str(resp.request_info))
                    logger.error("Status:" + str(resp.status))

                    try:
                        logger.error("text: " + await resp.text())
                    except:
                        logger.error("Can't print text")
                    raise ConnectionError()

    def rank_no_to_rank(self, rank_no: int) -> str:
        """
        0: Unranked
        1: copper 5
        5: copper 1
        6: bronze 5
        10: bronze 1
        11: silver 5
        15: silver 1
        16: gold 3
        17: gold 2
        18: gold 1
        19: plat 3
        20: plat 2
        21: plat 1
        22: dia 3
        23: dia 2
        24: dia 1
        25: champ
        """
        if rank_no == 0: return "Unranked"
        if rank_no == 1: return "Copper V"
        if rank_no == 2: return "Copper IV"
        if rank_no == 3: return "Copper III"
        if rank_no == 4: return "Copper II"
        if rank_no == 5: return "Copper I"
        if rank_no == 6: return "Bronze V"
        if rank_no == 7: return "Bronze IV"
        if rank_no == 8: return "Bronze III"
        if rank_no == 9: return "Bronze II"
        if rank_no == 10: return "Bronze I"
        if rank_no == 11: return "Silver V"
        if rank_no == 12: return "Silver IV"
        if rank_no == 13: return "Silver III"
        if rank_no == 14: return "Silver II"
        if rank_no == 15: return "silver I"
        if rank_no == 16: return "Gold III"
        if rank_no == 17: return "Gold II"
        if rank_no == 18: return "Gold I"
        if rank_no == 19: return "Platinum III"
        if rank_no == 20: return "Platinum II"
        if rank_no == 21: return "Platinum I"
        if rank_no == 22: return "Diamond III"
        if rank_no == 23: return "Diamond II"
        if rank_no == 24: return "Diamond I"
        if rank_no == 25: return "Champions"
        else:
            raise Exception("Rank no conversion failed.")

    def convert_enum(self, platform: Platform) -> str:
        if platform is Platform.PC:
            return "pc"
        elif platform is Platform.XBOX:
            return "xbox"
        elif platform is Platform.PS4:
            return "playstation"

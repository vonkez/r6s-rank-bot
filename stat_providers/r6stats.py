import os
from typing import Dict

import aiohttp
from loguru import logger

from stat_providers.rate_limiter import RateLimiter
from stat_providers.stat_provider import StatProvider, PlayerNotFound, Player, RankShort, Platform


class R6Stats(StatProvider):
    def __init__(self):
        self.API_KEY: str = os.environ["R6STATS_API_KEY"]
        self.SEASON: str = os.environ["R6_SEASON"]
        self.headers: Dict[str, str] = {'Authorization': 'Bearer ' + self.API_KEY}
        self.limiter: RateLimiter = RateLimiter(55)
        logger.info("R6Stats initialized")

    async def fetch_seasonal(self, nickname, platform: str):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                    f"https://api2.r6stats.com/public-api/stats/{nickname}/{platform}/seasonal") as resp, self.limiter:
                if resp.status == 200:
                    json_resp = await resp.json()
                    return json_resp
                elif resp.status == 404:
                    raise PlayerNotFound(nickname)
                else:
                    logger.error("R6Stats generic request failed")
                    logger.error("Request info:" + str(resp.request_info))
                    logger.error("Status:" + str(resp.status))

                    try:
                        logger.error("text: " + await resp.text())
                    except:
                        logger.error("Can't print text")

                    try:
                        logger.error("json: " + await resp.json())
                    except:
                        logger.error("Can't print json")
                    raise ConnectionError()

    async def fetch_generic(self, nickname, platform: str):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(
                    f"https://api2.r6stats.com/public-api/stats/{nickname}/{platform}/generic") as resp, self.limiter:
                if resp.status == 200:
                    json_resp = await resp.json()
                    return json_resp
                elif resp.status == 404:
                    raise PlayerNotFound(nickname)
                else:
                    logger.error("R6Stats seasonal request failed")
                    logger.error("Request info:" + str(resp.request_info))
                    logger.error("Status:" + str(resp.status))

                    try:
                        logger.error("text: " + await resp.text())
                    except:
                        logger.error("Can't print text")

                    try:
                        logger.error("json: " + await resp.json())
                    except:
                        logger.error("Can't print json")
                    raise ConnectionError()

    async def get_player(self, nickname: str, platform: Platform) -> Player:
        seasonal_json = await self.fetch_seasonal(nickname, platform.value)
        generic_json = await self.fetch_generic(nickname, platform.value)
        seasonal_player: Player = self.player_from_seasonal(seasonal_json)
        generic_player: Player = self.player_from_generic(generic_json)
        merged_player: Player = self.merge_players(seasonal_player, generic_player)
        return merged_player

    def merge_players(self, seasonal_player: Player, generic_player: Player) -> Player:
        seasonal_player.kd = generic_player.kd
        seasonal_player.level = generic_player.level
        return seasonal_player

    def player_from_generic(self, generic_json) -> Player:
        player = Player()
        player.name = generic_json['username']
        player.uplay_id = generic_json['uplay_id']
        player.ubisoft_id = generic_json['ubisoft_id']
        player.avatar_146 = generic_json['avatar_url_146']
        player.avatar256 = generic_json['avatar_url_256']
        player.kd = generic_json['stats']['queue']['ranked']['kd']
        player.level = generic_json['progression']['level']
        return player

    def player_from_seasonal(self, seasonal_json) -> Player:
        rank_short_str: str = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['rank_text'].split()[0]
        rank_short: RankShort = RankShort[rank_short_str.upper()]

        # Seasonal K/D
        # kills: int = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['kills']
        # deaths: int = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['deaths']
        # kd: float
        # try:
        #     kd = kills/deaths
        # except ZeroDivisionError:
        #     kd = 0

        player = Player()
        player.name = seasonal_json['username']
        player.platform = Platform[seasonal_json['platform'].upper()]
        player.level = None
        player.kd = None
        # player.kd = kd
        player.uplay_id = seasonal_json['uplay_id']
        player.ubisoft_id = seasonal_json['ubisoft_id']
        player.avatar_146 = seasonal_json['avatar_url_146']
        player.avatar_256 = seasonal_json['avatar_url_256']
        player.mmr = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['mmr']
        player.rank = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['rank_text']
        player.rank_short = rank_short
        player.rank_no = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['rank']
        player.rank_image = seasonal_json['seasons'][self.SEASON]['regions']['emea'][0]['rank_image']
        return player

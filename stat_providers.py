import os
import time
from abc import ABC, abstractmethod

import aiohttp
from loguru import logger
from enum import Enum
from typing import Dict


class Platform(Enum):
    PC = "pc"
    XBOX = "xbox"
    PS4 = "ps4"


class RankShort(Enum):
    UNRANKED = "unranked"
    COPPER = "copper"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    CHAMPIONS = "champions"


class Player:
    name: str
    platform: Platform
    level: int
    kd: float
    uplay_id: str
    ubisoft_id: str
    avatar_146: str
    avatar_256: str
    mmr: int
    rank: str
    rank_short: RankShort
    rank_no: int
    rank_image: str


class PlayerNotFound(Exception):
    pass


class RateLimitExceeded(Exception):
    pass


class StatProvider(ABC):
    @abstractmethod
    async def get_player(self, nickname: str, platform: Platform) -> Player:
        raise NotImplementedError()


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


class RateLimiter:
    """
    A basic async rate limiter that raises exception if it exceeds the limit.
    """
    def __init__(self, limit_per_minute):
        self.tokens = limit_per_minute
        self.token_rate = limit_per_minute
        self.updated_at = time.time()

    async def __aenter__(self):
        if time.time() - self.updated_at > 60:
            self.tokens = self.token_rate
            self.updated_at = time.time()

        if self.tokens > 0:
            self.tokens -= 1
            return True
        else:
            logger.error("Rate limit exceeded")
            raise RateLimitExceeded()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is PlayerNotFound or exc_tb is ConnectionError:
            return
        if exc_type is not None:
            logger.error(exc_type)
            logger.error(exc_val)
            logger.error(exc_tb)

from loguru import logger

from stat_providers.r6stats import R6Stats
from stat_providers.stat_provider import StatProvider, Player, Platform
from stat_providers.statsdb import StatsDB


class MultiProvider(StatProvider):
    def __init__(self):
        self.statsDB = StatsDB()
        self.r6stats = R6Stats()
        logger.info("MultiProvider initialized")

    async def get_player(self, nickname: str, platform: Platform) -> Player:
        logger.info(f"MultiProvider fetching player: {nickname} , {platform.name}")
        try:
            result = await self.statsDB.get_player(nickname, platform)
            logger.info("StatsDB succesfully returned")
            return result
        except Exception as e:
            logger.info(f"StatsDB failed: {type(e).__name__} , {e}")

        try:
            result = await self.r6stats.get_player(nickname, platform)
            logger.info("R6Stats succesfully returned")
            return result
        except Exception as e:
            logger.info(f"R6Stats failed: {type(e).__name__} , {e}")
            raise e

from abc import ABC, abstractmethod

from enum import Enum


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


class StatProvider(ABC):
    @abstractmethod
    async def get_player(self, nickname: str, platform: Platform) -> Player:
        raise NotImplementedError()

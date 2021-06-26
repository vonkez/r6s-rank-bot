import time

from loguru import logger

from stat_providers.stat_provider import PlayerNotFound


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
        if exc_type is PlayerNotFound or exc_type is ConnectionError:
            return
        if exc_type is not None:
            logger.error(exc_type)
            logger.error(exc_val)
            logger.error(exc_tb)


class RateLimitExceeded(Exception):
    pass

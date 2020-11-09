import os

from loguru import logger
from tortoise import Tortoise
import ssl


async def init() -> None:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]
    db_password = os.environ["DB_PASSWORD"]
    db_port = int(os.environ["DB_PORT"])
    db_user = os.environ["DB_USER"]

    await Tortoise.init(
        config={
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "database": db_name,
                        "host": db_host,
                        "password": db_password,
                        "port": db_port,
                        "user": db_user,
                        "ssl": ssl_ctx
                    }
                }
            },
            "apps": {
                "models": {
                    "models": ["models"],
                    "default_connection": "default",
                }
            }

        }
    )

    await Tortoise.generate_schemas(safe=True)
    logger.info("Connected to database")


async def close():
    await Tortoise.close_connections()

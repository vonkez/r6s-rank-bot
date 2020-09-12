import os
import atexit
import asyncpg


async def create_db():
    db = DB()
    await db._init()
    return db


class DB:
    async def _init(self):
        DATABASE_URL = os.environ['DATABASE_URL']
        self.pool = await asyncpg.create_pool(DATABASE_URL + "?sslmode=require", min_size=2, max_size=5)
        atexit.register(self.disconnect)
        print("Connected to database")

    async def create_tables(self):
        async with self.pool.acquire() as con:

            # Create configs table
            await con.execute("""
                CREATE TABLE IF NOT EXISTS configs(
                guild_id bigint PRIMARY KEY,
                bot_channel bigint,
                log_channel bigint,
                unranked bigint,
                copper bigint,
                bronze bigint,
                silver bigint,
                gold bigint,
                platinum bigint,
                diamond bigint,
                champions bigint);""")

            # Create users table
            await con.execute("""
                CREATE TABLE IF NOT EXISTS users(
                dc_id bigint PRIMARY KEY,
                dc_nick text,
                r6_id text,
                r6_nick text,
                level int,
                mmr int,
                update_date date);""")

    async def update_config(self, guild_id: int, setting: str, value: int):
        async with self.pool.acquire() as con:
            await con.execute(f"""
                UPDATE configs SET
                {setting}=$1
                WHERE guild_id=$2;""",
                value, guild_id)

    async def insert_config(self, guild_id):
        async with self.pool.acquire() as con:
            await con.execute("""
                INSERT INTO configs(guild_id)
                VALUES ($1);""",
                guild_id)

    async def get_config(self, guild_id):
        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM configs WHERE guild_id = $1;", guild_id)
            return rows[0]

    async def get_all_configs(self):
        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM configs;")
            return rows

    async def get_config_columns(self):
        async with self.pool.acquire() as con:
            row = await con.fetch("SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'configs';")
            config_columns = []
            for column in row:  # TODO: fix naming
                config_columns.append(column['column_name'])
            config_columns.remove('guild_id')
            return config_columns

    async def insert_user(self, dc_id, dc_nick, r6_id, r6_nick, level, mmr, update_date):
        async with self.pool.acquire() as con:
            await con.execute("""
                INSERT INTO users(dc_id, dc_nick, r6_id, r6_nick, level, mmr, update_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7);""",
                dc_id, dc_nick, r6_id, r6_nick, level, mmr, update_date)

    async def update_user(self, dc_id, dc_nick, r6_id, r6_nick, level, mmr, update_date):
        async with self.pool.acquire() as con:
            await con.execute("""
            UPDATE users SET
            dc_nick = $1,
            r6_id = $2,
            r6_nick = $3,
            level = $4,
            mmr = $5,
            update_date = $6
            WHERE dc_id = $7;""",
            dc_nick, r6_id, r6_nick, level, mmr, update_date, dc_id)

    async def delete_user(self, dc_id):
        async with self.pool.acquire() as con:
            await con.execute(f"DELETE FROM users WHERE dc_id = $1;", dc_id)


    async def get_users(self, dc_id):
        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM users WHERE dc_id = $1", dc_id)
            return rows

    async def get_all_users(self):
        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM users")
            return rows

    def disconnect(self):
        self.pool.terminate()
        print("Database connection closed")

from types import SimpleNamespace
import aiohttp
import time
import os

class R6Tab():
    # broken
    def __init__(self):
        self.limiter = RateLimiter(20)

    async def search(self, nickname):
        timestamp = int(time.time())
        results = []
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://r6.apitab.com/search/uplay/{nickname}?u={timestamp}') as resp, self.limiter:
                json_resp = await resp.json()
                if resp.status == 200:
                    if not json_resp['players']:
                        return results
                    for k, v in json_resp['players'].items():
                        player = SimpleNamespace(name=v['profile']['p_name'],
                                                 uplay_id=v['profile']['p_user'],
                                                 platform=v['profile']['p_platform'],
                                                 level=v['stats']['level'],
                                                 mmr=v['ranked']['EU_mmr'],
                                                 rank_no=v['ranked']['EU_rank'],
                                                 rank_short=find_rank(v['ranked']['EU_mmr'], v['ranked']['rank']))
                        results.append(player)
                    return results
                else:
                    print(json_resp)
                    raise ConnectionError

    async def player(self, r6_id, update):
        timestamp = int(time.time())
        player = None
        if update:
            url = f'https://r6.apitab.com/player/{r6_id}?u={timestamp}'
        else:
            url = f'https://r6.apitab.com/update/{r6_id}?u={timestamp}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp, self.limiter:
                json_resp = await resp.json()
                if resp.status == 200:
                    player = SimpleNamespace(name=json_resp['player']['p_name'],
                                             platform=json_resp['player']['p_platform'],
                                             uplay_id=json_resp['player']['p_user'],
                                             level=json_resp['stats']['level'],
                                             avatar_146=f"https://ubisoft-avatars.akamaized.net/{json_resp['player']['p_user']}/default_146_146.png",
                                             avatar256=f"https://ubisoft-avatars.akamaized.net/{json_resp['player']['p_user']}/default_256_256.png",
                                             mmr=json_resp['ranked']['EU_mmr'],
                                             max_mmr=json_resp['ranked']['EU_maxmmr'],
                                             rank_no=json_resp['ranked']['EU_rank'],
                                             rank_text=json_resp['ranked']['EU_rankname'],
                                             rank_short=json_resp['ranked']['EU_rankname'].split()[0])
                    return player
                else:
                    print(json_resp)
                    raise ConnectionError

    async def get_player(self, nickname=None, r6_id=None, update=None):
        if not r6_id:
            result = (await self.search(nickname))[0]
            if not result:
                return None
            nickname = result.uplay_id
        player = await self.player(nickname, True)
        result.__dict__.update(player.__dict__)
        return result


class R6Stats:
    def __init__(self):
        self.API_KEY = os.environ["R6STATS_API_KEY"]
        self.headers = {'Authorization': 'Bearer ' + self.API_KEY}
        self.limiter = RateLimiter(55)

    async def generic(self, nickname):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"https://api2.r6stats.com/public-api/stats/{nickname}/pc/generic") as resp, self.limiter:
                if resp.status == 200:
                    json_resp = await resp.json()
                    player = SimpleNamespace(name=json_resp['username'],
                                             uplay_id=json_resp['uplay_id'],
                                             ubisoft_id=json_resp['ubisoft_id'],
                                             avatar_146=json_resp['avatar_url_146'],
                                             avatar256=json_resp['avatar_url_256'],
                                             level=json_resp['progression']['level'])
                    return player
                elif resp.status == 404 or resp.status == 500:
                    return None
                else:
                    print("R6STATS GENERIC REQUEST FAIL")
                    print("Request info: " + resp.request_info)
                    print(f"Status: {resp.status}")
                    print(f"Status: {resp.cookies}")
                    print(f"Status: {resp.text()}")
                    try:
                        print(await resp.json())
                    except:
                        pass
                    raise ConnectionError

    async def seasonal(self, nickname):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"https://api2.r6stats.com/public-api/stats/{nickname}/pc/seasonal") as resp, self.limiter:
                json_resp = await resp.json()
                if resp.status == 200:
                    player = SimpleNamespace(name=json_resp['username'],
                                             platform=json_resp['platform'],
                                             uplay_id=json_resp['uplay_id'],
                                             ubisoft_id=json_resp['ubisoft_id'],
                                             avatar_146=json_resp['avatar_url_146'],
                                             avatar256=json_resp['avatar_url_256'],
                                             mmr=json_resp['seasons']['steel_wave']['regions']['emea'][0]['mmr'],
                                             max_mmr=json_resp['seasons']['steel_wave']['regions']['emea'][0]['max_mmr'],
                                             rank_text=json_resp['seasons']['steel_wave']['regions']['emea'][0]['rank_text'],
                                             rank_no=json_resp['seasons']['steel_wave']['regions']['emea'][0]['rank'],
                                             rank_image=json_resp['seasons']['steel_wave']['regions']['emea'][0]['rank_image'],
                                             rank_short=json_resp['seasons']['steel_wave']['regions']['emea'][0]['rank_text'].split()[0])
                    return player
                elif resp.status == 404 or resp.status == 500:
                    return None
                else:
                    print("R6STATS SEASONAL REQUEST FAIL")
                    print("Request info: " + resp.request_info)
                    print(f"Status: {resp.status}")
                    print(f"Status: {resp.cookies}")
                    print(f"Status: {resp.text()}")
                    try:
                        print(await resp.json())
                    except:
                        pass
                    raise ConnectionError

    async def get_player(self, nickname, r6_id=None, update=None):
        generic_player = await self.generic(nickname)
        if not generic_player:
            return None
        seasonal_player = await self.seasonal(nickname)

        # merge results
        generic_player.__dict__.update(seasonal_player.__dict__)

        return generic_player

def find_rank(mmr, rank_no):
    if rank_no == 0:
        return "Unranked"
    if mmr <= 1:return "Unranked"
    elif mmr <= 1599:return "Copper"
    elif mmr <= 2099:return "Bronze"
    elif mmr <= 2599:return "Silver"
    elif mmr <= 3199:return "Gold"
    elif mmr <= 4399:return "Platinum"
    elif mmr <= 4999:return "Diamond"
    else: return "Champion"

class RateLimiter:
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
            raise Exception('Rate limit !!')

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(exc_type)
            print(exc_val)
            print(exc_tb)


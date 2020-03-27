from types import SimpleNamespace
import aiohttp
import time

class R6Tab():
    async def search(self, nickname):
        timestamp = int(time.time())
        results = []
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://r6.apitab.com/search/uplay/{nickname}?u={timestamp}') as resp:
                json_resp = await resp.json()
                print(json_resp)
                if resp.status == 200:
                    for k, v in json_resp['players'].items():
                        player = SimpleNamespace(name=v['profile']['p_name'],
                                                 id=v['profile']['p_user'],
                                                 level=v['stats']['level'],
                                                 mmr=v['ranked']['EU_mmr'],
                                                 rank_no=v['ranked']['rank'],
                                                 rank=find_rank(v['ranked']['EU_mmr'], v['ranked']['rank']))
                        results.append(player)
                    return results
                else:
                    raise ConnectionError

    async def player(self, r6_id, update):
        timestamp = int(time.time())
        player = None
        if update:
            url = f'https://r6.apitab.com/player/{r6_id}?u={timestamp}'
        else:
            url = f'https://r6.apitab.com/update/{r6_id}?u={timestamp}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                json_resp = await resp.json()
                print(json_resp)
                if resp.status == 200:
                    if json_resp['found']:
                        player = SimpleNamespace(name=json_resp['player']['p_name'],
                                                 id=json_resp['player']['p_user'],
                                                 level=json_resp['stats']['level'],
                                                 mmr=json_resp['ranked']['EU_mmr'],
                                                 rank_no=json_resp['ranked']['rank'],
                                                 rank=find_rank(json_resp['ranked']['EU_mmr'], json_resp['ranked']['rank']))
                    return player
                else:
                    raise ConnectionError

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

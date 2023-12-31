import requests
import aiohttp
import json
from datetime import datetime, timedelta
import pytz
import time


timeformat = "%Y-%m-%dT%H:%M:%S%z"
#report_id
#report_type
#report_type[]
#
#killer_ship_category
#
#victim_ship_category
#user_id
#user_id[]
#guild_id
#guild_id[]
#total_participants
#battle_type
#battle_type[]
#date_killed[between]
#date_killed[between]
#date_killed[gt]
#date_killed[gte]
#date_killed[lt]
#date_killed[lte]
#isk[between]
#isk[gt]
#isk[gte]
#isk[lt]
#isk[lte]

def args4dic(c):
    ret = []
    for k, v in c.items():
        if k in ['order[isk]', 'order[date_killed]']:
            assert v in ['asc', 'desc'], f'unknown order: {v}'
            add = f'{k}={v}'
        elif k in ['killer_corp', 'victim_corp']:
            add = f'{k}={v.upper()}'
        elif k in ['region']:
            add = f'{k}={v.capitalize()}'
        elif k in ['killer_ship_type', 'victim_ship_type', 'killer_name', 'killer_full_name', 'victim_name', 'victim_full_name', 'system' ,'constellation']:
            add = f'{k}={v}'
        else:
            assert False, f'unknown key: {k}'
        ret.append(add)
    return '&'.join(ret)

class getcsv:
    def __init__(self, c):
        self.args = args4dic(c)
        self.page = 1
        self.done = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.done:
            raise StopAsyncIteration
        else:
            url = f'https://echoes.mobi/api/killmails?page={self.page}&{self.args}'
            print(url)
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    txt = await resp.text()
            if len(txt) < 4:
                self.done = True
                raise StopAsyncIteration
            self.page += 1
            return [x.split(',') for x in txt.split('\n') if len(x) > 2]

class getdic:
    def __init__(self, c):
        self.getter = getcsv(c)
        self.error = False
        self.exceptions = []
        try:
            self.data = []
            self.started = False
        except StopAsyncIteration:
            self.error = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.started:
            self.data = await self.getter.__anext__()
            self.keys = self.data.pop(0)
            self.started = True
            return await self.__anext__()
        if self.error:
            raise StopAsyncIteration
        if self.data:
            v = self.data.pop(0)
            if len(self.keys) != len(v):
                self.exceptions.append(v)
                return await self.__anext__()
            try:
                tmp = {}
                key = None
                for j in zip(self.keys,v):
                    if j[0] == 'isk' and j[1] == '"':
                        key = 'isk'
                    kv = j[0]
                    if key:
                        kv = key
                        key = j[0]
                    if kv == 'date_killed':
                        date = datetime.strptime(j[1], timeformat)
                        tmp[kv] = date
                    else:
                        tmp[kv] = j[1]
            except:
                self.exceptions.append(v)
                return await self.__anext__()
            return tmp
        else:
            self.data = await self.getter.__anext__()
            return await self.__anext__()

if __name__ == '__main__':
    cfg = {'order[date_killed]': 'desc', 'killer_name': 'Crubrus', 'killer_ship_type' : 'Daredevil'}
    o = getdic(cfg)
    today = datetime.now(pytz.utc)
    start_date = today - timedelta(days=today.weekday())
    limit = 3
    ret = {}
    for i in o:
        n = int((start_date - i['date_killed']).days/7)
        if n > limit:
            break
        if n not in ret:
            ret[n] = 0
        ret[n] += float(i['isk'])
    print(ret)


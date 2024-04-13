import aiohttp, asyncio
from tabulate import tabulate

from .account import Account
from .aave import Aave
from .compound import Compound
from .moonwell import Moonwell
from .utils import get_eth_price, async_retry


class Checker:
    def __init__(self, accs: list[Account]) -> None:
        self.accs = accs
        self.w3 = accs[0].w3
        self.eth_price = get_eth_price()

    @async_retry
    async def check_acc(self, acc: Account) -> dict:
        # aave_dep = Aave(acc).deposited_amount
        # moonwell_dep = Moonwell(acc).deposited_amount
        # compound_dep = Compound(acc).deposited_amount

        acc_value = 0
        async with aiohttp.ClientSession() as session:
            for i in range(5):
                params = {
                    'module': 'account',
                    'action': 'txlist',
                    'address': acc.address,
                    'sort': 'desc',
                    'apikey': 'GDRS5ZFMEI9S57U7G5GSMX3BP14P168FGV', # key from zkflow🤷‍♂️
                    'page': i,
                    'offset': 500
                }
                r: aiohttp.ClientResponse = await session.get('https://api.basescan.org/api', params=params)
                if r.status == 200 and not 'NOTOK' in await r.text():
                    for tx in (await r.json())['result']:
                        acc_value += float(tx['value']) / 10**18
                    if len((await r.json())['result']) < 500:
                        break
                else:
                    raise Exception(f'Ошибка чекера, ответ: {await r.text()}')
        acc.traded_value = acc_value

        return {
            '№': acc.index,
            'Адрес': f'{acc.address[:5]}...{acc.address[-5:]}',
            'OKX Адрес': f'{acc.okx_address[:5]}...{acc.okx_address[-5:]}' if acc.okx_address else 'Нет',
            'Транз': self.w3.eth.get_transaction_count(acc.address),
            'Объём': f'{acc_value:.2f} ETH (${acc_value*self.eth_price:.0f})',
            'Баланс': f'{acc.ether_balance:.5f} ETH (${acc.ether_balance*self.eth_price:.2f})',
            # 'Деп в Aave': f'{aave_dep:.5f} ETH (${aave_dep*self.eth_price:.2f})',
            # 'Деп в Compound': f'{compound_dep:.5f} ETH (${compound_dep*self.eth_price:.2f})',
            # 'Деп в Moonwell': f'{moonwell_dep:.5f} ETH (${moonwell_dep*self.eth_price:.2f})',
        }

    async def run(self) -> None:
        tasks = [asyncio.create_task(self.check_acc(acc)) for acc in self.accs]
        result = await asyncio.gather(*tasks)
        print(tabulate(result, headers='keys', tablefmt='rounded_grid'))

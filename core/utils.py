import time, random, requests, asyncio
from loguru import logger

from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware

from settings import RPC, MAX_GWEI, RETRY_COUNT


def sleep(min: int, max: int) -> None:
    time_sleep = random.randint(min, max)
    logger.info(f"Сплю {time_sleep} сек...")
    time.sleep(time_sleep)

def get_eth_price() -> float:
    r = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT')
    return float(r.json()['price'])

def check_gas(func: callable) -> callable:
    w3 = Web3(HTTPProvider(RPC), middlewares=[geth_poa_middleware])
    gas = w3.eth.gas_price / 10**9
    def wrapper(*args, **kwargs):
        while True:
            if gas > MAX_GWEI:
                logger.warning(f"Высокий газ: {gas:.2f} > {MAX_GWEI:.2f}")
                sleep(20, 30)
            else:
                logger.info(f"Газ в норме: {gas:.2f} < {MAX_GWEI:.2f}")
                break
        return func(*args, **kwargs)
    return wrapper

def retry(func):
    def wrapper(*args, **kwargs):
        for i in range(1, RETRY_COUNT+1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if args and hasattr(args[0], '__class__'): 
                    logger.error(f'({args[0].__class__.__name__ }.{func.__name__} {i}/{RETRY_COUNT}): {e}')
                else:
                    logger.error(f'({func.__name__} {i}/{RETRY_COUNT}): {e}')
                if i != RETRY_COUNT:
                    sleep(20, 30)
    return wrapper

def async_retry(func):
    async def wrapper(*args, **kwargs):
        for i in range(1, RETRY_COUNT+1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if args and hasattr(args[0], '__class__'): 
                    logger.error(f'({args[0].__class__.__name__ }.{func.__name__} {i}/{RETRY_COUNT}): {e}')
                else:
                    logger.error(f'({func.__name__} {i}/{RETRY_COUNT}): {e}')
                if i != RETRY_COUNT:
                    time_sleep = random.randint(20, 30)
                    logger.info(f"Сплю {time_sleep} сек...")
                    await asyncio.sleep(time_sleep)
    return wrapper
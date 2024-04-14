import datetime, sys, random, asyncio
from loguru import logger
from questionary import Choice, select

from core.account import Account
from core.aave import Aave
from core.compound import Compound
from core.moonwell import Moonwell
from core.seamless import Seamless
from core.okx import OKX
from core.checker import Checker
from core.utils import sleep
from config import PRIVATE_KEYS, OKX_ADDRESSES
from settings import *


def main() -> None:
    module = select(
        message='Выберите модуль: ',
        instruction='(используйте стрелочки для навигации)',
        choices=[
            Choice('1️⃣  Aave', Aave),
            Choice('2️⃣  Compound', Compound),
            Choice('3️⃣  Moonwell', Moonwell),
            Choice('4️⃣  Seamless', Seamless),
            Choice('🎲 Рандомный dApp', 'random'),
            Choice('📊 Чекер', 'checker'),
            Choice('❌ Выход', 'exit')
        ],
        qmark="\n❓ ",
        pointer="👉 "
    ).ask()
    if module == 'checker':
        return
    if module == 'exit' or module is None:
        exit()
    for acc in accs:
        if acc.ether_balance < 0.001:
            if acc.deposited_balance > 0.001:
                logger.warning(f'{acc.info} Найдено {acc.deposited_balance:.2f} ETH в пуле! Пытаюсь вывести...')
                acc.withdraw_from_pool()
                sleep(15, 25)
            else:
                if WITHDRAW_FROM_OKX and USE_OKX:
                    OKX(acc.info).withdraw(acc.address, random.uniform(*AMOUNT_TO_WITHDRAW_FROM_OKX), 'ETH', 'Base')
                else:
                    logger.warning(f'{acc.info} Недостаточно ETH! Вывод с ОКХ или USE_OKX отключён, пропускаю аккаунт...')
                    continue
        
        target = random.uniform(*TARGET_VALUE)
        while acc.traded_value < target:
            if module == 'random':
                random.choice([Aave, Compound, Moonwell, Seamless])(acc).run()
            else:
                module(acc).run()
            logger.debug(f'Теперь объём: {acc.traded_value:.2f} ETH | Таргет: {target:.2f} ETH')

        if WITHDRAW_TO_OKX:
            acc.withdraw_to_okx()
        logger.success(f'{acc.info} Аккаунт завершён 🏁 | Объём: {acc.traded_value:.2f} ETH')
        sleep(*SLEEP_BETWEEN_ACCS)


if __name__ == "__main__":
    logger.remove()
    format='<white>{time:HH:mm:ss}</white> | <bold><level>{level: <7}</level></bold> | <level>{message}</level>'
    logger.add(sink=sys.stdout, format=format)
    logger.add(sink=f'logs/{datetime.datetime.today().strftime("%Y-%m-%d")}.log', format=format)

    while True:
        try:
            accs = [Account(i, key) for i, key in enumerate(PRIVATE_KEYS, 1)]
            for i, okx_address in enumerate(OKX_ADDRESSES):
                accs[i].okx_address = okx_address
            asyncio.run(Checker(accs).run())
            main()
        except Exception as e:
            logger.critical(e)
        except (KeyboardInterrupt, SystemExit):
            print('\n👋👋👋')
            exit()

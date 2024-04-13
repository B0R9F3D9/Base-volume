from loguru import logger

from web3.contract import Contract

from .account import Account
from .utils import sleep, check_gas, retry
from config import MOONWELL_CONTRACT_ADDRESS, MOONWELL_TOKEN_ADDRESS, MOONWELL_ABI


class Moonwell:
    def __init__(self, acc: Account) -> None:
        self.acc = acc
        self.w3 = acc.w3
        self.contract: Contract = self.w3.eth.contract(address=MOONWELL_CONTRACT_ADDRESS, abi=MOONWELL_ABI)
        self.token_contract: Contract = self.w3.eth.contract(address=MOONWELL_TOKEN_ADDRESS, abi=MOONWELL_ABI)

    @property
    def deposited_amount(self) -> float:
        return self.token_contract.functions.balanceOf(self.acc.address).call() / 49.26 / 10**8

    @retry
    @check_gas
    def deposit(self) -> None:
        amount_wei = self.w3.eth.get_balance(self.acc.address) - int(0.0003*10**18) # -1$
        if amount_wei < 0.001*10**18: # мин сумма для депа 0.001 ETH
            raise Exception(f'{self.acc.info} Недостаточно ETH для депозита!')
        logger.info(f"{self.acc.info} Делаю депозит {amount_wei/10**18:.5f} ETH в Moonwell...")
        tx_data = self.acc.get_tx_data(amount_wei)
        txn = self.contract.functions.mint(self.acc.address).build_transaction(tx_data)
        self.acc.send_txn(txn)

    @retry
    @check_gas
    def withdraw(self) -> float | None:
        amount = self.deposited_amount
        if amount < 0.0001: # 0.0001 ETH
            raise Exception(f'{self.acc.info} Депозит в Moonwell не найден!')
        logger.info(f'{self.acc.info} Делаю вывод {amount:.5f} ETH из Moonwell...')
        tx_data = self.acc.get_tx_data()
        txn = self.token_contract.functions.redeem(int(amount*49.26*10**8)).build_transaction(tx_data)
        self.acc.send_txn(txn)
        return amount

    def run(self) -> None:
        if self.deposited_amount >= 0.0001: # 0.0001 ETH
            self.withdraw()
            sleep(15, 25)
        self.deposit()
        sleep(15, 25)
        traded_value = self.withdraw()
        sleep(15, 25)
        if traded_value is not None:
            self.acc.traded_value += traded_value

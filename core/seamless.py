from loguru import logger

from web3.contract import Contract

from .account import Account
from .utils import sleep, check_gas, retry
from config import SEAMLESS_CONTRACT_ADDRESS, SEAMLESS_TOKEN_ADDRESS, SEAMLESS_ABI, ERC20_ABI


class Seamless:
    def __init__(self, acc: Account) -> None:
        self.acc = acc
        self.w3 = acc.w3
        self.contract: Contract = self.w3.eth.contract(address=SEAMLESS_CONTRACT_ADDRESS, abi=SEAMLESS_ABI)
        self.token_contract: Contract = self.w3.eth.contract(address=SEAMLESS_TOKEN_ADDRESS, abi=ERC20_ABI)

    @property
    def deposited_amount(self) -> int:
        return self.token_contract.functions.balanceOf(self.acc.address).call() / 10**18

    @retry
    @check_gas
    def deposit(self) -> None:
        amount_wei = self.w3.eth.get_balance(self.acc.address) - (0.0003*10**18) # -1$
        if amount_wei < 0.001*10**18: # мин деп 0.001 ETH
            raise Exception(f'{self.acc.info} Недостаточно ETH для депозита!')
        logger.info(f"{self.acc.info} Делаю депозит {amount_wei/10**18:.5f} ETH в Seamless...")
        tx_data = self.acc.get_tx_data(int(amount_wei))
        txn = self.contract.functions.depositETH(
            "0x8F44Fd754285aa6A2b8B9B97739B79746e0475a7", # constant
            self.acc.address,
            0
        ).build_transaction(tx_data)
        self.acc.send_txn(txn)

    @retry
    @check_gas
    def withdraw(self) -> float | None:
        amount = self.deposited_amount
        if amount < 0.0001: # 0.0001 ETH
            raise Exception(f'{self.acc.info} Депозит в Seamless не найден')
        logger.info(f'{self.acc.info} Делаю вывод {amount:.5f} ETH из Seamless...')
        tx_data = self.acc.get_tx_data()
        txn = self.contract.functions.withdrawETH(
            "0x8F44Fd754285aa6A2b8B9B97739B79746e0475a7", # constant
            int(amount*10**18),
            self.acc.address
        ).build_transaction(tx_data)
        self.acc.send_txn(txn)
        return amount

    def run(self) -> None:
        self.acc.approve(SEAMLESS_TOKEN_ADDRESS, SEAMLESS_CONTRACT_ADDRESS)
        if self.deposited_amount >= 0.0001: # 0.0001 ETH
            self.withdraw()
            sleep(15, 25)
        self.deposit()
        sleep(15, 25)
        traded_value = self.withdraw()
        sleep(15, 25)
        if traded_value is not None:
            self.acc.traded_value += traded_value

from loguru import logger

from web3.contract import Contract

from .account import Account
from .utils import sleep, check_gas, retry
from config import COMPOUND_CONTRACT_ADDRESS, COMPOUND_TOKEN_ADDRESS, COMPOUND_ABI


class Compound:
    def __init__(self, acc: Account) -> None:
        self.acc = acc
        self.w3 = acc.w3
        self.token_contract: Contract = self.w3.eth.contract(address=COMPOUND_TOKEN_ADDRESS, abi=COMPOUND_ABI)
    
    @property
    def deposited_amount(self) -> float:
        return self.token_contract.functions.balanceOf(self.acc.address).call() / 10**18
    
    @property
    def compound_allowed(self) -> bool:
        return self.token_contract.functions.isAllowed(self.acc.address, COMPOUND_CONTRACT_ADDRESS).call()
    
    @retry
    @check_gas
    def allow_compound(self) -> None:
        logger.info(f'{self.acc.info} Делаю разрешение для Compound...')
        tx_data = self.acc.get_tx_data()
        txn = self.token_contract.functions.allow(COMPOUND_CONTRACT_ADDRESS, True).build_transaction(tx_data)
        self.acc.send_txn(txn)
        sleep(10, 15)

    @retry
    @check_gas
    def deposit(self) -> None:
        amount_wei = self.w3.eth.get_balance(self.acc.address) - (0.0003*10**18) # -1$
        if amount_wei < 0.001*10**18: # мин сумма депа 0.001 ETH
            raise Exception(f'{self.acc.info} Недостаточно ETH для депозита!')
        logger.info(f"{self.acc.info} Делаю депозит {amount_wei/10**18:.5f} ETH в Compound...")

        data = '0x555029a6' + \
            '0000000000000000000000000000000000000000000000000000000000000040' + \
            '0000000000000000000000000000000000000000000000000000000000000080' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '414354494f4e5f535550504c595f4e41544956455f544f4b454e000000000000' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '0000000000000000000000000000000000000000000000000000000000000020' + \
            '0000000000000000000000000000000000000000000000000000000000000060' + \
            '00000000000000000000000046e6b214b524310239732d51387075e0e70970bf' + \
            f'000000000000000000000000{self.acc.address[2:].lower()}' + \
            f'{int(amount_wei):064x}'

        txn = self.acc.get_tx_data(int(amount_wei)) | {
            'to': COMPOUND_CONTRACT_ADDRESS,
            'data': data
        }
        self.acc.send_txn(txn)

    @retry
    @check_gas
    def withdraw(self) -> float | None:
        amount = self.deposited_amount
        if amount < 0.0001: # 0.0001 ETH
            raise Exception(f'{self.acc.info} Депозит в Compound не найден')
        logger.info(f'{self.acc.info} Делаю вывод {amount:.5f} ETH из Compound...')

        data = '0x555029a6' + \
            '0000000000000000000000000000000000000000000000000000000000000040' + \
            '0000000000000000000000000000000000000000000000000000000000000080' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '414354494f4e5f57495448445241575f4e41544956455f544f4b454e00000000' + \
            '0000000000000000000000000000000000000000000000000000000000000001' + \
            '0000000000000000000000000000000000000000000000000000000000000020' + \
            '0000000000000000000000000000000000000000000000000000000000000060' + \
            '00000000000000000000000046e6b214b524310239732d51387075e0e70970bf' + \
            f'000000000000000000000000{self.acc.address[2:].lower()}' + \
            f'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
        
        txn = self.acc.get_tx_data() | {
            'to': COMPOUND_CONTRACT_ADDRESS,
            'data': data
        }
        self.acc.send_txn(txn)
        return amount

    def run(self) -> None:
        if self.compound_allowed == False:
            self.allow_compound()
        if self.deposited_amount >= 0.0001: # 0.0001 ETH
            self.withdraw()
            sleep(15, 25)
        self.deposit()
        sleep(15, 25)
        traded_value = self.withdraw()
        sleep(15, 25)
        if traded_value is not None:
            self.acc.traded_value += traded_value

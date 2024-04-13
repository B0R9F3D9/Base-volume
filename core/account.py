import time, random
from loguru import logger

from web3 import Web3, HTTPProvider
from web3.contract import Contract
from web3.exceptions import TransactionNotFound
from web3.middleware import geth_poa_middleware
from eth_account import Account as EthereumAccount

from core.utils import sleep, retry, check_gas
from .okx import OKX
from settings import RPC, EXPLORER, AMOUNT_TO_SAVE, USE_OKX
from config import ERC20_ABI


class Account:
    def __init__(self, index: int, private_key: str) -> None:
        self.index = index
        self.private_key = private_key
        self.account = EthereumAccount.from_key(private_key)
        self.w3 = Web3(HTTPProvider(RPC), middlewares=[geth_poa_middleware])
        self.address = self.w3.to_checksum_address(self.account.address)
        self.info = f'[№{self.index} - {self.address[:5]}...{self.address[-5:]}]'
        self.traded_value = 0

    @property
    def ether_balance(self) -> float:
        return self.w3.eth.get_balance(self.address) / 10**18
    
    @property
    def deposited_balance(self) -> float:
        from .aave import Aave
        from .compound import Compound
        from .moonwell import Moonwell
        self.aave_dep = Aave(self).deposited_amount
        self.moonwell_dep = Moonwell(self).deposited_amount
        self.compound_dep = Compound(self).deposited_amount
        return self.aave_dep + self.moonwell_dep + self.compound_dep

    def get_tx_data(self, value: int = 0) -> dict:
        return {
            "from": self.address,
            "value": value,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "gasPrice": self.w3.eth.gas_price,
            "chainId": self.w3.eth.chain_id
        }
    
    def send_txn(self, txn: dict) -> str | None:
        txn['gas'] = self.w3.eth.estimate_gas(txn)
        signed_txn = self.w3.eth.account.sign_transaction(txn, self.private_key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        return self.wait_txn(txn_hash.hex())

    def wait_txn(self, hash: str) -> str | None:
        start_time = time.time()
        while True:
            try:
                receipts: dict = self.w3.eth.get_transaction_receipt(hash)
                status = receipts.get("status")
                if status == 1:
                    logger.success(f"{self.info} Транзакция успешна! {EXPLORER+hash}"); return hash
                elif status is None:
                    time.sleep(0.5)
                else:
                    raise Exception(f"{self.info} Транзакция не удалась! {EXPLORER+hash}"); return
            except TransactionNotFound:
                if time.time() - start_time > 45: # макс время ожидания 45сек
                    raise Exception(f"{self.info} Транзакция не найдена! {EXPLORER+hash}"); return
                time.sleep(1)

    @retry
    @check_gas
    def approve(self, token: str, spender: str) -> None:
        amount = 2**256 - 1 # аппрув на анлим
        contract: Contract = self.w3.eth.contract(address=token, abi=ERC20_ABI)
        allowance = contract.functions.allowance(self.address, spender).call()
        if allowance >= 2**255:
            logger.info(f"{self.info} Аппрув уже есть, пропускаю...")
            return
        logger.info(f'{self.info} Делаю аппрув...')
        tx_data = self.get_tx_data()
        txn = contract.functions.approve(spender, amount).build_transaction(tx_data)
        self.send_txn(txn)
        sleep(5, 10)

    @retry
    @check_gas
    def withdraw_to_okx(self) -> None:
        if self.okx_address is None: 
            logger.info(f'{self.info} ОКХ адрес не задан!')
            return
        self.okx_address = self.w3.to_checksum_address(self.okx_address)
        amount_wei = self.w3.eth.get_balance(self.address) - (random.uniform(*AMOUNT_TO_SAVE) * 10**18)
        logger.info(f'{self.info} Делаю вывод {amount_wei/10**18:.5f} ETH на адрес ОКХ - {self.okx_address}')
        txn = self.get_tx_data(int(amount_wei)) | {"to": self.okx_address, 'data': '0x'}
        hash = self.send_txn(txn)
        if hash and USE_OKX:
            OKX(self.info).wait_for_deposit('ETH', 'Base', hash)

    @retry
    @check_gas
    def withdraw_from_pool(self) -> None:
        from .aave import Aave
        from .compound import Compound
        from .moonwell import Moonwell
        for dapp in [Moonwell(self), Aave(self), Compound(self)]:
            if dapp.deposited_amount > 0.0001: # 0.0001 ETH
                logger.info(f'{self.info} Найдено {dapp.deposited_amount:.5f} ETH в {dapp.__class__.__name__}!')
                dapp.withdraw()

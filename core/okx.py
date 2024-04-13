import hmac, base64
import requests
from hashlib import sha256
from datetime import datetime, timezone
from loguru import logger

from .utils import retry, sleep
from settings import OKX_API_KEY, OKX_API_SECRET, OKX_PASSPHRASE

MESSAGES = {
    '58207': 'адрес не добавлен в белый список',
    '58350': 'недостаточно баланса',
    'Pending withdrawal': 'Вывод в очереди...',
    'Withdrawal in progress': 'Вывод в процессе...'
}


class OKX:
    def __init__(self, acc_info: str) -> None:
        self.info = acc_info

    def make_request(self, url: str, method: str = "GET", **kwargs) -> dict:
         with requests.Session() as session:
             with session.request(method, url, **kwargs) as resp:
                if resp.status_code != 200:
                    raise Exception(f'Ошибка {resp.status_code} при попытке выполнить запрос, ответ: {resp.text()}')
                return resp.json()
 
    def get_headers(self, request_path: str, method: str = "GET", body: str = "") -> dict:
        try:
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            prehash_string = timestamp + method.upper() + request_path[19:] + body
            secret_key_bytes = OKX_API_SECRET.encode('utf-8')
            signature = hmac.new(secret_key_bytes, prehash_string.encode('utf-8'), sha256).digest()
            encoded_signature = base64.b64encode(signature).decode('utf-8')
            return {
                "Content-Type": "application/json",
                "OK-ACCESS-KEY": OKX_API_KEY,
                "OK-ACCESS-SIGN": encoded_signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
                "x-simulated-trading": "0"
            }
        except Exception as error:
            raise Exception(f'Не получилось сформировать заголовки: {error}')
        
    def get_currencies(self, ccy: str) -> list[dict]:
        url = 'https://www.okx.cab/api/v5/asset/currencies'
        params = {'ccy': ccy}
        headers = self.get_headers(f'{url}?ccy={ccy}')
        return (self.make_request(url=url, headers=headers, params=params))['data']

    @retry
    def withdraw(self, address: str, amount: float, token_symbol: str, chain: str) -> bool:
        '''Возвращает True когда вывод завершён или False если вывод не удался'''
        addr = f'{address[:5]}...{address[-5:]}'
        ccy = [result for result in self.get_currencies(ccy=token_symbol) if result['chain'] == f'{token_symbol}-{chain}']
        if len(ccy) == 0:
            logger.error(f'{self.info} Такой вывод невозможен: {token_symbol}-{chain}')
            return False
        ccy = ccy[0]

        if not ccy['canWd']: 
            logger.error(f'{self.info} Вывод {token_symbol}-{chain} отключён'); return False
        if not float(ccy['minWd']) <= amount-float(ccy['maxFee']) <= float(ccy['maxWd']):
            logger.error(f'{self.info} Сумма вывода вне допустимого диапазона'); return False

        logger.info(f'{self.info} Вывожу {amount:.4f} {token_symbol}-{chain} на адрес {addr}')
        body = {
            "ccy": ccy['ccy'],
            "amt": amount,
            "dest": "4",
            "toAddr": address,
            "fee": ccy['minFee'],
            "chain": ccy['chain'],
        }
        url = 'https://www.okx.cab/api/v5/asset/withdrawal'
        headers = self.get_headers(request_path=url, method="POST", body=str(body))
        resp = self.make_request(url=url, method='POST', data=str(body), headers=headers)

        code = resp['code']
        if code != '0':
            message = MESSAGES[code] if code in MESSAGES.keys() else f'ошибка - {code}'
            logger.error(f'{self.info} Вывод не удался: {message}!')
            return False
        
        withdraw_id = resp['data'][0]['wdId']
        while True:
            status =  self.get_withdraw_status(withdraw_id)
            if status in MESSAGES.keys():
                logger.info(f'{self.info} {MESSAGES[status]}')
            elif status == 'Withdrawal complete':
                logger.success(f'{self.info} Вывел {amount:.4f} {token_symbol}-{chain} на адрес {addr}')
                return True
            else:
                logger.error(f'{self.info} Неизвестный статус вывода: {status}')
                return False
            sleep(20, 25)

    def get_withdraw_status(self, withdraw_id: str | int) -> str:
        '''Возвращает: статус вывода'''
        url = f'https://www.okx.cab/api/v5/asset/deposit-withdraw-status?wdId={withdraw_id}'
        headers =  self.get_headers(request_path=url)
        return (self.make_request(url=url, headers=headers))['data'][0]['state']
    
    @retry
    def wait_for_deposit(self, token_symbol: str, chain: str, tx_hash: str) -> bool:
        '''Возвращает True когда депозит завершен или False если депозит отклонён'''
        ccys = self.get_currencies(ccy=token_symbol)
        ccys = [ccy for ccy in ccys if ccy['chain'] == f'{token_symbol}-{chain}']

        if len(ccys) == 0:
            logger.error(f'{self.info} Токен {token_symbol}-{chain} не найден')
            return False
        else:
            ccy = ccys[0]

        need_confirms = ccy['minWdUnlockConfirm'] 
        while True:
            status =  self.get_deposit_status(token_symbol, tx_hash)
            if status == None:
                logger.info(f'{self.info} Депозит пока не найден...')
            elif status == True and not isinstance(status, int):
                logger.success(f'{self.info} Депозит получен!')
                return True
            elif type(status) == int and type(status) != bool:
                logger.info(f'{self.info} Ожидание подтверждений - {status}/{need_confirms}')
            else:
                logger.error(f'{self.info} Депозит отклонён!')
                return False
            sleep(20, 25)

    def get_deposit_status(self, token_symbol: str, tx_hash: str) -> int | bool | None:
        '''Возвращает статус депозита: число подтверждений(int) если депозит в процессе,
        True если депозит завершен, False если депозит отклонён или None если депозит не найден'''
        url = f'https://www.okx.cab/api/v5/asset/deposit-history?ccy={token_symbol}'
        headers =  self.get_headers(request_path=url)
        resp =  self.make_request(url=url, headers=headers)

        deposits = [deposit for deposit in resp['data'] if deposit['txId'] == tx_hash]
        if len(deposits) == 0: return None
        
        deposit = deposits[0]
        if deposit['state'] == '2': return True
        elif deposit['state'] in ['0', '1']: return int(deposit['actualDepBlkConfirm'])
        else: return False


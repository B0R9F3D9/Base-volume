# Мин, Макс цель по объёму (в ETH)
TARGET_VALUE: tuple[float, float] = (0.12, 0.13)

# Мин, Макс время задержки между аккаунтами (в секундах)
SLEEP_BETWEEN_ACCS: tuple[int, int] = (30, 60)

# Перемешивать кошельки (Да, Нет)
SHUFFLE_ACCS: bool = True

# Макс цена газа в сети Base
MAX_GWEI: float = 0.2

# Количество попыток для выполнения действия
RETRY_COUNT: int = 3

RPC: str = 'https://base-mainnet.public.blastapi.io'
EXPLORER: str = 'https://basescan.org/tx/'


# Использовать OKX (Да, Нет)
USE_OKX: bool = True

# Выводить средства из OKX (если False, то кошельки без баланса будут пропускаться)
WITHDRAW_FROM_OKX: bool = False
# Мин, Макс сумма для вывода с ОКХ (в ETH)
AMOUNT_TO_WITHDRAW_FROM_OKX: tuple[float, float] = (0.011, 0.02)

# Выводить баланс минус `AMOUNT_TO_SAVE` на OKX (Да, Нет)
WITHDRAW_TO_OKX: bool = True
# Мин, Макс сумма для сохранения на балансе (в ETH)
AMOUNT_TO_SAVE: tuple[float, float] = (0.001, 0.002)

# OKX !Keep it secret!
OKX_API_KEY: str = '' 
OKX_API_SECRET: str = ''
OKX_PASSPHRASE: str = ''

import json


with open('data/pkeys.txt', 'r') as file:
    PRIVATE_KEYS = [x.strip() for x in file.readlines()]

with open('data/okx_addresses.txt', 'r') as file:
    OKX_ADDRESSES = [x.strip() for x in file.readlines()]

with open('data/abi/erc20.json', 'r') as file:
    ERC20_ABI = json.load(file)

with open('data/abi/aave.json', 'r') as file:
    AAVE_ABI = json.load(file)

with open('data/abi/compound.json', 'r') as file:
    COMPOUND_ABI = json.load(file)

with open('data/abi/moonwell.json', 'r') as file:
    MOONWELL_ABI = json.load(file)

with open('data/abi/seamless.json', 'r') as file:
    SEAMLESS_ABI = json.load(file)


AAVE_CONTRACT_ADDRESS = '0x18CD499E3d7ed42FEbA981ac9236A278E4Cdc2ee'
AAVE_TOKEN_ADDRESS = '0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7'

COMPOUND_CONTRACT_ADDRESS = '0x78D0677032A35c63D142a48A2037048871212a8C'
COMPOUND_TOKEN_ADDRESS = '0x46e6b214b524310239732D51387075E0e70970bf'

MOONWELL_CONTRACT_ADDRESS = '0x70778cfcFC475c7eA0f24cC625Baf6EaE475D0c9'
MOONWELL_TOKEN_ADDRESS = '0x628ff693426583D9a7FB391E54366292F509D457'

SEAMLESS_CONTRACT_ADDRESS = '0xaeeB3898edE6a6e86864688383E211132BAa1Af3'
SEAMLESS_TOKEN_ADDRESS = '0x48bf8fCd44e2977c8a9A744658431A8e6C0d866c'

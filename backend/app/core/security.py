import hashlib


def hash_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def mask_account(account: str) -> str:
    return account[:2] + "****" + account[-2:]
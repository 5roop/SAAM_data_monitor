from secrets import hashes, salt

def pass_to_hash(password: str):
    import hashlib
    return hashlib.sha512(bytes(password.casefold(), "utf-8") + salt).hexdigest()
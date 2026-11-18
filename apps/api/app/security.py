"""Authentication primitives and request throttling."""
import hashlib
import hmac
import os
import secrets
import time
from threading import Lock
from fastapi import HTTPException

def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'

def verify_password(password: str, stored: str) -> bool:
    return hmac.compare_digest(hash_password(password, stored.split(':')[0]), stored)

_windows: dict[str, list[float]] = {}
_lock = Lock()

def limit(key: str, maximum: int = 60) -> None:
    """Redis in deployed mode; bounded local fallback for one-process development."""
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        import redis
        try:
            client = redis.Redis.from_url(redis_url)
            script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
            count = client.eval(script, 1, 'limit:' + hashlib.sha256(key.encode()).hexdigest())
        except redis.RedisError:
            raise HTTPException(503, 'Please try again shortly.')
    else:
        with _lock:
            now = time.monotonic()
            for old in list(_windows):
                if not _windows[old] or _windows[old][-1] < now - 60:
                    del _windows[old]
            entries = [t for t in _windows.get(key, []) if t > now - 60]
            entries.append(now)
            _windows[key] = entries
            count = len(entries)
    if count > maximum:
        raise HTTPException(429, 'Please take a short break and try again.', headers={'Retry-After': '60'})

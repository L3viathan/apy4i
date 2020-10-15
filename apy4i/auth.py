import os
import hmac
import hashlib
from functools import wraps

from quart import request, abort

def signing_secret(signing_secret_env):
    def decorator(afn):
        @wraps(afn)
        async def wrapper(*args, **kwargs):
            body = await request.get_data()
            ts = request.headers.get("X-Slack-Request-Timestamp").encode("utf-8")
            signature = request.headers.get("X-Slack-Signature")
            version = b"v0"
            payload = b":".join((version, ts, body))
            h = hmac.new(
                os.environ.get(signing_secret_env).encode("utf-8"),
                payload,
                hashlib.sha256,
            )
            expected = signature[len(version) + 1 :]
            actual = h.hexdigest()
            if actual != expected:
                abort(401)
            return await afn(*args, **kwargs)
        return wrapper
    return decorator


def github_hmac(github_secret_env):
    def decorator(afn):
        @wraps(afn)
        async def wrapper(*args, **kwargs):
            body = await request.get_data()
            expected = request.headers.get("X-Hub-Signature-256")
            h = hmac.new(
                os.environ.get(github_secret_env).encode("utf-8"),
                body,
                hashlib.sha256,
            )
            actual = h.hexdigest()
            if actual != expected[len("sha256="):]:
                # abort(401)
                return f"Actual: {actual}", "401"
            return await afn(*args, **kwargs)
        return wrapper
    return decorator


def simple_token(token_env):
    def decorator(afn):
        @wraps(afn)
        async def wrapper(*args, **kwargs):
            token = request.headers.get("X-Token")
            if token is None or os.environ.get(token_env) != token:
                abort(401)
            return await afn(*args, **kwargs)
        return wrapper
    return decorator

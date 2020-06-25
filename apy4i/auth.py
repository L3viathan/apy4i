import os
import hmac
import hashlib
from quart import request, abort

def signing_secret(signing_secret_env):
    def decorator(afn):
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
                abort(403)
            return await afn(*args, **kwargs)
        return wrapper
    return decorator


def simple_token(token_env):
    def decorator(afn):
        async def wrapper(*args, **kwargs):
            body = await request.get_data()
            token = request.headers.get("X-Token")
            if os.environ.get(token_env) != token:
                abort(403)
            return await afn(*args, **kwargs)
        return wrapper
    return decorator

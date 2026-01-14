import os
import json
from pymemcache.client.base import Client

MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "memcached")
MEMCACHED_PORT = int(os.getenv("MEMCACHED_PORT", "11211"))

client = Client((MEMCACHED_HOST, MEMCACHED_PORT))

def get_json(key: str):
    val = client.get(key)
    if not val:
        return None
    return json.loads(val.decode("utf-8"))

def set_json(key: str, value, ttl: int = 30):
    client.set(key, json.dumps(value).encode("utf-8"), expire=ttl)

def delete(key: str):
    client.delete(key)

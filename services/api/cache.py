import os
import json
from uuid import UUID
from datetime import date, datetime
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
    def json_serializer(obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    json_data = json.dumps(value, default=json_serializer).encode("utf-8")
    client.set(key, json_data, expire=ttl)

def delete(key: str):
    client.delete(key)
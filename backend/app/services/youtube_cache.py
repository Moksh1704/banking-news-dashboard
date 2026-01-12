import time

_YOUTUBE_CACHE = {
    "data": [],
    "timestamp": 0
}

CACHE_TTL = 15 * 60  # 15 minutes


def get_cached_youtube():
    if time.time() - _YOUTUBE_CACHE["timestamp"] < CACHE_TTL:
        return _YOUTUBE_CACHE["data"]
    return None


def set_cached_youtube(data):
    _YOUTUBE_CACHE["data"] = data
    _YOUTUBE_CACHE["timestamp"] = time.time()

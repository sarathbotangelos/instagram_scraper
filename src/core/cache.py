import json
import os
from typing import Any, Optional

CACHE_FILE = "temp_cache.json"

class FileCache:
    @staticmethod
    def set(key: str, value: Any):
        """Stores a value in the temporary cache file."""
        cache = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                cache = {}
        
        cache[key] = value
        
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=4)

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Retrieves a value from the temporary cache file."""
        if not os.path.exists(CACHE_FILE):
            return None
        
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                return cache.get(key)
        except (json.JSONDecodeError, IOError):
            return None

    @staticmethod
    def clear():
        """Clears the temporary cache file."""
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)

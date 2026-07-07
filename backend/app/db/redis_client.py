class RedisClient:

    def __init__(self):
        self.store = {}

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]
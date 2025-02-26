import threading

class Counter:
    _counter = 1  # Start at 1 for binary (2^0)
    _lock = threading.Lock()

    @classmethod
    def get_next(cls):
        with cls._lock:
            value = cls._counter
            cls._counter *= 2  # Increment by powers of 2
        return value

class CTYPE:
    def __getattr__(self, name):
        if name not in self.__dict__:
            self.__dict__[name] = Counter.get_next()
        return self.__dict__[name]
    
    def collide_with(self, collisiontypes: list):
        mask = 0
        collisiontypes = sorted(collisiontypes)
        for type in collisiontypes:
            mask = mask | type
        return mask

CTYPES = CTYPE()

import shelve

_shelf = shelve.open("apy4i.db")

def shelf(key):
    if key in _shelf:
        return _shelf[key]
    slot = {}
    _shelf[key] = slot
    return slot

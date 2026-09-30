import os
import json

WATCHLIST_PATH = "data/watchlist/watchlist.json"

def get_watchlist() -> set[str]:
    """Returns a set of plate strings from the watchlist.json."""
    if not os.path.exists(WATCHLIST_PATH):
        return set()
    try:
        with open(WATCHLIST_PATH, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(str(item).strip() for item in data)
            return set()
    except Exception:
        return set()

def check_watchlist(plate_text: str) -> bool:
    """Exact string match against the watchlist."""
    watchlist = get_watchlist()
    return plate_text.strip() in watchlist

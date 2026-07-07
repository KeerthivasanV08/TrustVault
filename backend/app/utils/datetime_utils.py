from datetime import datetime


def now_iso():
    return datetime.now().isoformat()


def parse_timestamp(ts: str):
    return datetime.fromisoformat(ts)
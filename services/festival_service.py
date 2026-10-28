from datetime import datetime, timezone
import time
import requests

FESTIVAL_API_URL = "https://indian-festival-api.vercel.app/api/festivals"
CACHE_TTL_SECONDS = 300

_cache = {}


class FestivalServiceError(Exception):
    pass


def _cache_get(key):
    row = _cache.get(key)
    if not row:
        return None
    if row["expires_at"] < time.time():
        _cache.pop(key, None)
        return None
    return row["value"]


def _cache_set(key, value):
    _cache[key] = {"value": value, "expires_at": time.time() + CACHE_TTL_SECONDS}


def _extract_date(record: dict):
    if "date" in record and record["date"]:
        return record["date"]
    date_keys = sorted([k for k in record.keys() if k.startswith("date_")], reverse=True)
    for key in date_keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_record(record: dict):
    festival_date = _extract_date(record)
    local_names = record.get("local_names") if isinstance(record.get("local_names"), dict) else {}
    states = record.get("states") if isinstance(record.get("states"), list) else []
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "date": festival_date,
        "description": record.get("description"),
        "month": record.get("month"),
        "day": record.get("day"),
        "religion": record.get("religion"),
        "states": states,
        "national_holiday": bool(record.get("national_holiday", False)),
        "restricted_holiday": bool(record.get("restricted_holiday", False)),
        "type": record.get("type"),
        "local_names": local_names,
        "also_known_as": record.get("also_known_as") if isinstance(record.get("also_known_as"), list) else [],
        "source": FESTIVAL_API_URL,
    }


def _fetch_from_api(params: dict):
    try:
        response = requests.get(FESTIVAL_API_URL, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FestivalServiceError("Unable to fetch festival data from upstream service.") from exc

    data = response.json()
    if not isinstance(data, dict) or "data" not in data or not isinstance(data["data"], list):
        raise FestivalServiceError("Festival API returned an unexpected response format.")
    return data["data"]


def list_festivals(filters: dict):
    allowed = ("upcoming", "month", "state", "religion", "national_holiday")
    params = {}
    for key in allowed:
        value = filters.get(key)
        if value is not None and value != "":
            params[key] = value

    search_term = (filters.get("q") or "").strip().lower()
    cache_key = "festival-list:" + "&".join([f"{k}={params[k]}" for k in sorted(params.keys())])
    records = _cache_get(cache_key)
    if records is None:
        records = _fetch_from_api(params)
        _cache_set(cache_key, records)

    normalized = [_normalize_record(r) for r in records]
    if search_term:
        normalized = [f for f in normalized if isinstance(f.get("name"), str) and search_term in f["name"].lower()]
    return normalized


def get_festival_by_id(festival_id):
    try:
        target_id = int(festival_id)
    except (ValueError, TypeError):
        return None
    records = list_festivals({})
    for item in records:
        if item.get("id") == target_id:
            return item
    return None


def upcoming_festivals():
    festivals = list_festivals({"upcoming": "true"})
    today = datetime.now(timezone.utc).date()

    def date_key(item):
        value = item.get("date")
        try:
            if value:
                return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            pass
        return datetime.max.date()

    festivals = sorted(festivals, key=date_key)
    future = []
    for fest in festivals:
        date_value = fest.get("date")
        try:
            parsed = datetime.strptime(date_value, "%Y-%m-%d").date() if date_value else None
        except ValueError:
            parsed = None
        if parsed and parsed >= today:
            future.append(fest)
    return future

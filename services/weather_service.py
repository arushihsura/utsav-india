import time
import requests

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_SECONDS = 300

CITIES = {
    "mumbai": {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777},
    "delhi": {"name": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    "jaipur": {"name": "Jaipur", "latitude": 26.9124, "longitude": 75.7873},
    "kolkata": {"name": "Kolkata", "latitude": 22.5726, "longitude": 88.3639},
    "chennai": {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707},
    "bengaluru": {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946},
}

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

_cache = {}


class WeatherServiceError(Exception):
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


def city_to_location(city: str):
    if not city:
        return None
    return CITIES.get(city.strip().lower())


def _code_to_text(code):
    if code is None:
        return "Unknown"
    return WEATHER_CODES.get(code, f"Code {code}")


def get_weather(city: str):
    location = city_to_location(city)
    if location is None:
        supported = [x["name"] for x in CITIES.values()]
        raise WeatherServiceError(f"Unsupported city. Choose one of: {', '.join(supported)}")

    cache_key = f"weather:{location['name']}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
        "current": "temperature_2m,weathercode",
        "timezone": "auto",
        "forecast_days": 7,
    }

    try:
        response = requests.get(WEATHER_URL, params=params, timeout=12)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherServiceError("Unable to fetch weather data from Open-Meteo.") from exc

    payload = response.json()
    daily = payload.get("daily", {})
    days = daily.get("time") if isinstance(daily.get("time"), list) else []
    highs = daily.get("temperature_2m_max") if isinstance(daily.get("temperature_2m_max"), list) else []
    lows = daily.get("temperature_2m_min") if isinstance(daily.get("temperature_2m_min"), list) else []
    rain = (
        daily.get("precipitation_probability_max")
        if isinstance(daily.get("precipitation_probability_max"), list)
        else []
    )
    codes = daily.get("weathercode") if isinstance(daily.get("weathercode"), list) else []

    forecast = []
    for i, day in enumerate(days):
        code = codes[i] if i < len(codes) else None
        forecast.append(
            {
                "date": day,
                "temp_max_c": highs[i] if i < len(highs) else None,
                "temp_min_c": lows[i] if i < len(lows) else None,
                "precipitation_probability": rain[i] if i < len(rain) else None,
                "weather_code": code,
                "weather_text": _code_to_text(code),
            }
        )

    current = payload.get("current", {}) if isinstance(payload.get("current"), dict) else {}
    current_code = current.get("weathercode")
    normalized = {
        "city": location["name"],
        "coordinates": {"latitude": location["latitude"], "longitude": location["longitude"]},
        "current": {
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "weather_code": current_code,
            "weather_text": _code_to_text(current_code),
        },
        "forecast": forecast,
        "source": "Open-Meteo Forecast API (https://api.open-meteo.com/v1/forecast)",
    }
    _cache_set(cache_key, normalized)
    return normalized

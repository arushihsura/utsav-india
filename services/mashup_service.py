from datetime import datetime, timezone

from services.festival_service import get_festival_by_id
from services.weather_service import get_weather


def _planning_suggestion(forecast_for_date: dict):
    if not forecast_for_date:
        return (
            "Reliable forecast is not available yet for the selected date. "
            "Check again closer to the celebration date."
        )
    precipitation = forecast_for_date.get("precipitation_probability")
    weather_text = forecast_for_date.get("weather_text", "current conditions")
    if precipitation is None:
        return (
            f"Weather indicates '{weather_text}'. Precipitation probability is unavailable, "
            "so keep both indoor and outdoor options ready."
        )
    if precipitation >= 60:
        return (
            f"Precipitation probability is {precipitation}%. Consider an indoor celebration backup "
            "or covered venue."
        )
    if precipitation <= 30:
        return (
            f"Precipitation probability is {precipitation}%. Outdoor plans may be suitable "
            "based on this forecast."
        )
    return (
        f"Precipitation probability is {precipitation}%. Conditions are mixed; keep a flexible plan "
        "with indoor and outdoor options."
    )


def build_festival_plan(festival_id: int, city: str, selected_date: str = None):
    festival = get_festival_by_id(festival_id)
    if festival is None:
        return None, None, "Festival not found."

    weather = get_weather(city)
    festival_date = festival.get("date")
    plan_date = selected_date or festival_date

    forecast_for_date = None
    if plan_date:
        for day in weather["forecast"]:
            if day.get("date") == plan_date:
                forecast_for_date = day
                break

    date_in_forecast_window = False
    if plan_date:
        try:
            date_in_forecast_window = any(x.get("date") == plan_date for x in weather["forecast"])
        except Exception:
            date_in_forecast_window = False

    result = {
        "festival": {
            "id": festival.get("id"),
            "name": festival.get("name"),
            "date": festival_date,
            "description": festival.get("description"),
            "religion": festival.get("religion"),
            "source": festival.get("source"),
        },
        "location": {
            "city": weather["city"],
            "coordinates": weather["coordinates"],
        },
        "selected_date": plan_date,
        "forecast_available_for_selected_date": date_in_forecast_window,
        "forecast_for_selected_date": forecast_for_date,
        "weather_summary": weather["current"],
        "planning_suggestion": _planning_suggestion(forecast_for_date),
        "disclaimer": (
            "Festival dates may vary by regional tradition and source. "
            "Weather-based suggestions are guidance only, not guarantees."
        ),
        "sources": {
            "festival_api": festival.get("source"),
            "weather_api": weather.get("source"),
        },
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    return result, festival, None

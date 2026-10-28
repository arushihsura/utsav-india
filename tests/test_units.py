"""Pure unit tests for backend helper functions (no Flask app/HTTP needed)."""

from database import now_iso
from services.festival_service import _extract_date, _normalize_record
from services.weather_service import _code_to_text, city_to_location
from services.mashup_service import _planning_suggestion


def test_now_iso_format():
    value = now_iso()
    assert value.endswith("Z")
    assert "T" in value
    assert "+00:00" not in value


def test_extract_date_prefers_date_field():
    record = {"date": "2026-11-08", "date_hindu": "2026-11-09"}
    assert _extract_date(record) == "2026-11-08"


def test_extract_date_falls_back_to_date_prefixed_key():
    record = {"date": "", "date_islamic": "2026-05-01"}
    assert _extract_date(record) == "2026-05-01"


def test_extract_date_returns_none_when_missing():
    assert _extract_date({"name": "Festival"}) is None


def test_normalize_record_defaults_missing_fields():
    normalized = _normalize_record({"id": 5, "name": "Pongal"})
    assert normalized["id"] == 5
    assert normalized["states"] == []
    assert normalized["local_names"] == {}
    assert normalized["also_known_as"] == []
    assert normalized["national_holiday"] is False


def test_code_to_text_known_code():
    assert _code_to_text(0) == "Clear sky"


def test_code_to_text_unknown_code():
    assert _code_to_text(123) == "Code 123"


def test_code_to_text_none():
    assert _code_to_text(None) == "Unknown"


def test_city_to_location_case_insensitive():
    location = city_to_location("  MUMBAI  ")
    assert location["name"] == "Mumbai"


def test_city_to_location_unsupported():
    assert city_to_location("Unknown City") is None


def test_city_to_location_empty():
    assert city_to_location("") is None


def test_planning_suggestion_high_rain():
    forecast = {"precipitation_probability": 75, "weather_text": "Slight rain"}
    message = _planning_suggestion(forecast)
    assert "indoor" in message.lower()


def test_planning_suggestion_low_rain():
    forecast = {"precipitation_probability": 10, "weather_text": "Clear sky"}
    message = _planning_suggestion(forecast)
    assert "outdoor" in message.lower()


def test_planning_suggestion_mixed():
    forecast = {"precipitation_probability": 45, "weather_text": "Partly cloudy"}
    message = _planning_suggestion(forecast)
    assert "mixed" in message.lower() or "flexible" in message.lower()


def test_planning_suggestion_missing_probability():
    forecast = {"precipitation_probability": None, "weather_text": "Overcast"}
    message = _planning_suggestion(forecast)
    assert "unavailable" in message.lower()


def test_planning_suggestion_no_forecast():
    message = _planning_suggestion(None)
    assert "not available" in message.lower()

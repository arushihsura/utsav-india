from unittest.mock import patch

MOCK_FESTIVAL = {
    "id": 1,
    "name": "Diwali",
    "date": "2026-11-08",
    "description": "Festival of lights.",
    "religion": "hindu",
    "states": ["All India"],
    "source": "https://indian-festival-api.vercel.app/api/festivals",
}


def mock_weather_response(precipitation):
    return {
        "city": "Mumbai",
        "coordinates": {"latitude": 19.0760, "longitude": 72.8777},
        "current": {
            "time": "2026-10-28T12:00",
            "temperature_c": 31.0,
            "weather_code": 0,
            "weather_text": "Clear sky",
        },
        "forecast": [
            {
                "date": "2026-10-28",
                "temp_max_c": 33.0,
                "temp_min_c": 24.0,
                "precipitation_probability": precipitation,
                "weather_code": 0,
                "weather_text": "Clear sky",
            }
        ],
        "source": "Open-Meteo Forecast API",
    }


def test_mashup_high_rain_indoor_suggestion(client):
    with patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_weather", return_value=mock_weather_response(75)):
        
        res = client.get("/api/mashup/festival-plan?festival_id=1&city=Mumbai&selected_date=2026-10-28")
        assert res.status_code == 200
        data = res.json
        assert data["festival"]["name"] == "Diwali"
        assert data["location"]["city"] == "Mumbai"
        assert data["forecast_available_for_selected_date"] is True
        assert "indoor celebration backup" in data["planning_suggestion"]
        assert "75%" in data["planning_suggestion"]


def test_mashup_dry_outdoor_suggestion(client):
    with patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_weather", return_value=mock_weather_response(15)):
        
        res = client.get("/api/mashup/festival-plan?festival_id=1&city=Mumbai&selected_date=2026-10-28")
        assert res.status_code == 200
        data = res.json
        assert data["forecast_available_for_selected_date"] is True
        assert "Outdoor plans may be suitable" in data["planning_suggestion"]
        assert "15%" in data["planning_suggestion"]


def test_mashup_mixed_conditions_suggestion(client):
    with patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_weather", return_value=mock_weather_response(45)):
        
        res = client.get("/api/mashup/festival-plan?festival_id=1&city=Mumbai&selected_date=2026-10-28")
        assert res.status_code == 200
        data = res.json
        assert data["forecast_available_for_selected_date"] is True
        assert "Conditions are mixed" in data["planning_suggestion"]


def test_mashup_outside_forecast_window(client):
    with patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_festival_by_id", return_value=MOCK_FESTIVAL), \
         patch("services.mashup_service.get_weather", return_value=mock_weather_response(10)):
        
        # Festival date 2026-11-08 is outside the mocked forecast window (2026-10-28)
        res = client.get("/api/mashup/festival-plan?festival_id=1&city=Mumbai&selected_date=2026-11-08")
        assert res.status_code == 200
        data = res.json
        assert data["forecast_available_for_selected_date"] is False
        assert data["forecast_for_selected_date"] is None
        assert "Reliable forecast is not available yet" in data["planning_suggestion"]
        assert "disclaimer" in data
        assert "sources" in data

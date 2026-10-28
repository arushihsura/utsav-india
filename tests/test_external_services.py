from unittest.mock import patch
import requests
from services.festival_service import _fetch_from_api, FestivalServiceError
from services.weather_service import get_weather, WeatherServiceError


def test_festival_api_upstream_network_error(client):
    with patch("services.festival_service.requests.get", side_effect=requests.RequestException("Network timeout")):
        with patch("services.festival_service._cache", {}):
            res = client.get("/api/festivals")
            assert res.status_code == 502
            assert "Unable to fetch festival data" in res.json["error"]


def test_festival_api_malformed_response():
    with patch("services.festival_service.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"something_unexpected": 123}
        try:
            _fetch_from_api({})
            assert False, "Should have raised FestivalServiceError"
        except FestivalServiceError as err:
            assert "unexpected response format" in str(err)


def test_weather_api_upstream_network_error(client):
    with patch("services.weather_service.requests.get", side_effect=requests.RequestException("Connection refused")):
        with patch("services.weather_service._cache", {}):
            res = client.get("/api/weather?city=Mumbai")
            assert res.status_code == 400
            assert "Unable to fetch weather data" in res.json["error"]


def test_mashup_upstream_festival_failure(client):
    with patch("services.festival_service.requests.get", side_effect=requests.RequestException("Down")):
        with patch("services.festival_service._cache", {}):
            res = client.get("/api/mashup/festival-plan?festival_id=1&city=Mumbai")
            # Upstream failure leads to 502
            assert res.status_code in (502, 404)

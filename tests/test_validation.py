from unittest.mock import patch

MOCK_FESTIVAL = {
    "id": 1,
    "name": "Diwali",
    "date": "2026-11-08",
    "religion": "hindu",
    "states": ["All India"],
}


@patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL)
def test_plan_payload_validation(mock_fest, client, user_a):
    # Missing required field
    res_no_city = client.post(
        "/api/plans",
        headers=user_a["auth_header"],
        json={"festival_id": 1, "celebration_date": "2026-11-08"},
    )
    assert res_no_city.status_code == 400
    assert "city is required" in res_no_city.json["error"]

    # Unsupported city
    res_bad_city = client.post(
        "/api/plans",
        headers=user_a["auth_header"],
        json={"festival_id": 1, "city": "Atlantis", "celebration_date": "2026-11-08"},
    )
    assert res_bad_city.status_code == 400
    assert "Unsupported city" in res_bad_city.json["error"]

    # Malformed celebration_date
    res_bad_date = client.post(
        "/api/plans",
        headers=user_a["auth_header"],
        json={"festival_id": 1, "city": "Mumbai", "celebration_date": "08-11-2026"},
    )
    assert res_bad_date.status_code == 400
    assert "YYYY-MM-DD" in res_bad_date.json["error"]

    # Non-integer festival_id
    res_bad_id = client.post(
        "/api/plans",
        headers=user_a["auth_header"],
        json={"festival_id": "not-an-int", "city": "Mumbai", "celebration_date": "2026-11-08"},
    )
    assert res_bad_id.status_code == 400
    assert "must be an integer" in res_bad_id.json["error"]


def test_weather_endpoint_validation(client):
    res_no_city = client.get("/api/weather")
    assert res_no_city.status_code == 400
    assert "city is required" in res_no_city.json["error"]

    res_unknown_city = client.get("/api/weather?city=Gotham")
    assert res_unknown_city.status_code == 400
    assert "Unsupported city" in res_unknown_city.json["error"]


def test_mashup_endpoint_validation(client):
    res_missing_city = client.get("/api/mashup/festival-plan?festival_id=1")
    assert res_missing_city.status_code == 400

    res_missing_id = client.get("/api/mashup/festival-plan?city=mumbai")
    assert res_missing_id.status_code == 400

    res_invalid_id = client.get("/api/mashup/festival-plan?festival_id=xyz&city=mumbai")
    assert res_invalid_id.status_code == 400
    assert "integer" in res_invalid_id.json["error"]


def test_patch_profile_invalid_city(client, user_a):
    res = client.patch(
        "/api/me",
        headers=user_a["auth_header"],
        json={"preferred_city": "Atlantis"},
    )
    assert res.status_code == 400
    assert "Unsupported city" in res.json["error"]

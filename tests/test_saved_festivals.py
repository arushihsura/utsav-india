from unittest.mock import patch

MOCK_FESTIVAL = {
    "id": 1,
    "name": "Diwali",
    "date": "2026-11-08",
    "religion": "hindu",
    "states": ["All India"],
}


@patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL)
def test_saved_festival_crud(mock_fest, client, user_a):
    # 1. SAVE (POST)
    res = client.post("/api/saved-festivals", headers=user_a["auth_header"], json={"festival_id": 1})
    assert res.status_code == 201
    saved_id = res.json["data"]["id"]
    assert res.json["data"]["festival_name"] == "Diwali"
    assert res.json["data"]["festival_id"] == 1

    # 2. DUPLICATE ATTEMPT -> 409
    dup_res = client.post("/api/saved-festivals", headers=user_a["auth_header"], json={"festival_id": 1})
    assert dup_res.status_code == 409
    assert "already saved" in dup_res.json["error"]

    # 3. LIST (GET)
    list_res = client.get("/api/saved-festivals", headers=user_a["auth_header"])
    assert list_res.status_code == 200
    assert list_res.json["count"] == 1
    assert list_res.json["data"][0]["id"] == saved_id

    # 4. GET BY ID
    single_res = client.get(f"/api/saved-festivals/{saved_id}", headers=user_a["auth_header"])
    assert single_res.status_code == 200
    assert single_res.json["data"]["id"] == saved_id

    # 5. DELETE
    del_res = client.delete(f"/api/saved-festivals/{saved_id}", headers=user_a["auth_header"])
    assert del_res.status_code == 200
    assert "deleted" in del_res.json["message"].lower()

    # 6. GET AFTER DELETE -> 404
    get_again = client.get(f"/api/saved-festivals/{saved_id}", headers=user_a["auth_header"])
    assert get_again.status_code == 404


def test_save_festival_validation(client, user_a):
    res_missing = client.post("/api/saved-festivals", headers=user_a["auth_header"], json={})
    assert res_missing.status_code == 400

    res_invalid = client.post("/api/saved-festivals", headers=user_a["auth_header"], json={"festival_id": "abc"})
    assert res_invalid.status_code == 400

    with patch("app.get_festival_by_id", return_value=None):
        res_not_found = client.post("/api/saved-festivals", headers=user_a["auth_header"], json={"festival_id": 9999})
        assert res_not_found.status_code == 404

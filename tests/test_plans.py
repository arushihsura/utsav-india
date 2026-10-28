from unittest.mock import patch


MOCK_DIWALI = {
    "id": 1,
    "name": "Diwali",
    "date": "2026-11-08",
    "description": "Festival of lights.",
    "religion": "hindu",
    "states": ["All India"],
}


@patch("app.get_festival_by_id", return_value=MOCK_DIWALI)
def test_personal_plan_crud_lifecycle(mock_fest, client, user_a):
    # 1. CREATE (POST)
    payload = {
        "festival_id": 1,
        "city": "Mumbai",
        "celebration_date": "2026-11-08",
        "notes": "Buying diyas and sweets with family",
    }
    create_res = client.post("/api/plans", headers=user_a["auth_header"], json=payload)
    assert create_res.status_code == 201
    plan_data = create_res.json["data"]
    plan_id = plan_data["id"]
    assert plan_data["festival_name"] == "Diwali"
    assert plan_data["city"] == "Mumbai"
    assert plan_data["celebration_date"] == "2026-11-08"
    assert plan_data["notes"] == "Buying diyas and sweets with family"

    # 2. READ LIST (GET)
    list_res = client.get("/api/plans", headers=user_a["auth_header"])
    assert list_res.status_code == 200
    assert list_res.json["count"] == 1
    assert list_res.json["data"][0]["id"] == plan_id

    # 3. READ SINGLE (GET)
    get_res = client.get(f"/api/plans/{plan_id}", headers=user_a["auth_header"])
    assert get_res.status_code == 200
    assert get_res.json["data"]["id"] == plan_id

    # 4. REPLACE (PUT)
    put_payload = {
        "festival_id": 1,
        "city": "Jaipur",
        "celebration_date": "2026-11-09",
        "notes": "Celebrating at heritage palace",
    }
    put_res = client.put(f"/api/plans/{plan_id}", headers=user_a["auth_header"], json=put_payload)
    assert put_res.status_code == 200
    assert put_res.json["data"]["city"] == "Jaipur"
    assert put_res.json["data"]["celebration_date"] == "2026-11-09"
    assert put_res.json["data"]["notes"] == "Celebrating at heritage palace"

    # 5. PARTIAL UPDATE (PATCH)
    patch_payload = {"notes": "Updated note: booked sweets"}
    patch_res = client.patch(f"/api/plans/{plan_id}", headers=user_a["auth_header"], json=patch_payload)
    assert patch_res.status_code == 200
    assert patch_res.json["data"]["notes"] == "Updated note: booked sweets"
    assert patch_res.json["data"]["city"] == "Jaipur"

    # 6. DELETE
    del_res = client.delete(f"/api/plans/{plan_id}", headers=user_a["auth_header"])
    assert del_res.status_code == 200
    assert "deleted" in del_res.json["message"].lower()

    # 7. READ AFTER DELETE (404)
    get_after_del = client.get(f"/api/plans/{plan_id}", headers=user_a["auth_header"])
    assert get_after_del.status_code == 404


def test_plan_not_found(client, user_a):
    assert client.get("/api/plans/9999", headers=user_a["auth_header"]).status_code == 404
    assert client.put("/api/plans/9999", headers=user_a["auth_header"], json={
        "festival_id": 1,
        "city": "Mumbai",
        "celebration_date": "2026-11-08"
    }).status_code == 404
    assert client.patch("/api/plans/9999", headers=user_a["auth_header"], json={"city": "Delhi"}).status_code == 404
    assert client.delete("/api/plans/9999", headers=user_a["auth_header"]).status_code == 404

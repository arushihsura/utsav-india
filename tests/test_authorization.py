from unittest.mock import patch

MOCK_FESTIVAL = {
    "id": 1,
    "name": "Diwali",
    "date": "2026-11-08",
    "religion": "hindu",
    "states": ["All India"],
}


@patch("app.get_festival_by_id", return_value=MOCK_FESTIVAL)
def test_ownership_and_isolation(mock_fest, client, user_a, user_b):
    # 1. User A creates a plan
    create_plan_res = client.post(
        "/api/plans",
        headers=user_a["auth_header"],
        json={"festival_id": 1, "city": "Delhi", "celebration_date": "2026-11-08", "notes": "User A secret plan"},
    )
    assert create_plan_res.status_code == 201
    plan_a_id = create_plan_res.json["data"]["id"]

    # 2. User A saves a festival
    save_fest_res = client.post(
        "/api/saved-festivals",
        headers=user_a["auth_header"],
        json={"festival_id": 1},
    )
    assert save_fest_res.status_code == 201
    saved_fest_a_id = save_fest_res.json["data"]["id"]

    # 3. User B CANNOT read User A's plan
    b_read_res = client.get(f"/api/plans/{plan_a_id}", headers=user_b["auth_header"])
    assert b_read_res.status_code == 404

    # 4. User B CANNOT update User A's plan (PUT)
    b_put_res = client.put(
        f"/api/plans/{plan_a_id}",
        headers=user_b["auth_header"],
        json={"festival_id": 1, "city": "Chennai", "celebration_date": "2026-11-08", "notes": "Hijacked"},
    )
    assert b_put_res.status_code == 404

    # 5. User B CANNOT patch User A's plan (PATCH)
    b_patch_res = client.patch(
        f"/api/plans/{plan_a_id}",
        headers=user_b["auth_header"],
        json={"city": "Kolkata"},
    )
    assert b_patch_res.status_code == 404

    # 6. User B CANNOT delete User A's plan
    b_del_res = client.delete(f"/api/plans/{plan_a_id}", headers=user_b["auth_header"])
    assert b_del_res.status_code == 404

    # Verify User A's plan is still intact
    a_read_res = client.get(f"/api/plans/{plan_a_id}", headers=user_a["auth_header"])
    assert a_read_res.status_code == 200
    assert a_read_res.json["data"]["city"] == "Delhi"

    # 7. User B CANNOT read User A's saved festival
    b_read_saved = client.get(f"/api/saved-festivals/{saved_fest_a_id}", headers=user_b["auth_header"])
    assert b_read_saved.status_code == 404

    # 8. User B CANNOT delete User A's saved festival
    b_del_saved = client.delete(f"/api/saved-festivals/{saved_fest_a_id}", headers=user_b["auth_header"])
    assert b_del_saved.status_code == 404

    # 9. Verify lists are completely isolated
    b_plans = client.get("/api/plans", headers=user_b["auth_header"]).json["data"]
    assert len(b_plans) == 0

    b_saved = client.get("/api/saved-festivals", headers=user_b["auth_header"]).json["data"]
    assert len(b_saved) == 0

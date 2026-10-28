from datetime import datetime, timedelta, timezone
import jwt
from auth import decode_app_jwt, AuthError


def test_jwt_generation_and_decode(app, user_a):
    with app.app_context():
        payload = decode_app_jwt(user_a["token"])
        assert payload["sub"] == str(user_a["user"]["id"])
        assert payload["email"] == user_a["user"]["email"]
        assert payload["name"] == user_a["user"]["name"]


def test_missing_auth_header(client):
    res = client.get("/api/me")
    assert res.status_code == 401
    assert "Missing or invalid Authorization header" in res.json["error"]


def test_malformed_auth_header(client):
    res = client.get("/api/me", headers={"Authorization": "Basic 12345"})
    assert res.status_code == 401
    assert "Missing or invalid Authorization header" in res.json["error"]

    res_empty = client.get("/api/me", headers={"Authorization": "Bearer   "})
    assert res_empty.status_code == 401
    assert "Missing token" in res_empty.json["error"]


def test_expired_token(client, app, user_a):
    with app.app_context():
        expired_payload = {
            "sub": str(user_a["user"]["id"]),
            "email": user_a["user"]["email"],
            "name": user_a["user"]["name"],
            "exp": datetime.now(tz=timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(tz=timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, app.config["JWT_SECRET"], algorithm="HS256")

    res = client.get("/api/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json["error"].lower()


def test_invalid_signature_token(client, user_a):
    res = client.get("/api/me", headers={"Authorization": f"Bearer {user_a['token']}invalid"})
    assert res.status_code == 401
    assert "Invalid token" in res.json["error"]


def test_nonexistent_user_token(client, app):
    with app.app_context():
        payload = {
            "sub": "99999",
            "email": "ghost@example.com",
            "name": "Ghost",
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(tz=timezone.utc),
        }
        ghost_token = jwt.encode(payload, app.config["JWT_SECRET"], algorithm="HS256")

    res = client.get("/api/me", headers={"Authorization": f"Bearer {ghost_token}"})
    assert res.status_code == 401
    assert "User not found" in res.json["error"]


def test_me_and_preferences(client, user_a):
    # GET /api/me
    res = client.get("/api/me", headers=user_a["auth_header"])
    assert res.status_code == 200
    assert res.json["email"] == user_a["user"]["email"]
    assert res.json["preferred_city"] is None

    # PATCH /api/me with valid city
    patch_res = client.patch(
        "/api/me",
        headers=user_a["auth_header"],
        json={"preferred_city": "Jaipur"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json["preferred_city"] == "Jaipur"

    # Verify updated
    res2 = client.get("/api/me", headers=user_a["auth_header"])
    assert res2.status_code == 200
    assert res2.json["preferred_city"] == "Jaipur"


def test_google_auth_missing_credential(client):
    res = client.post("/api/auth/google", json={})
    assert res.status_code == 400
    assert "Missing Google credential" in res.json["error"]

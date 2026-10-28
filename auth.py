from datetime import datetime, timedelta, timezone
from functools import wraps
import jwt
from flask import current_app, jsonify, request, g
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from database import get_db, now_iso


class AuthError(Exception):
    pass


def verify_google_id_token(token: str):
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise AuthError("Google OAuth is not configured on the server.")

    try:
        info = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    except Exception as exc:
        raise AuthError("Invalid Google ID token.") from exc

    issuer = info.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise AuthError("Invalid token issuer.")
    return info


def get_or_create_user(google_info: dict):
    db = get_db()
    sub = google_info["sub"]
    email = google_info.get("email", "")
    name = google_info.get("name") or email or "User"
    picture = google_info.get("picture")
    now = now_iso()

    row = db.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
    if row:
        db.execute(
            "UPDATE users SET email = ?, name = ?, picture = ?, updated_at = ? WHERE id = ?",
            (email, name, picture, now, row["id"]),
        )
        db.commit()
        updated = db.execute("SELECT * FROM users WHERE id = ?", (row["id"],)).fetchone()
        return dict(updated)

    db.execute(
        """
        INSERT INTO users (google_sub, email, name, picture, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (sub, email, name, picture, now, now),
    )
    db.commit()
    created = db.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
    return dict(created)


def issue_app_jwt(user: dict):
    exp_minutes = int(current_app.config.get("JWT_EXP_MINUTES", 120))
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=exp_minutes)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "exp": expires_at,
        "iat": datetime.now(tz=timezone.utc),
    }
    token = jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")
    return token, expires_at.isoformat()


def decode_app_jwt(token: str):
    try:
        payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token.") from exc
    return payload


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header."}), 401

        token = header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "Missing token."}), 401

        try:
            payload = decode_app_jwt(token)
        except AuthError as err:
            return jsonify({"error": str(err)}), 401

        user_id = payload.get("sub")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            return jsonify({"error": "User not found."}), 401

        g.current_user = dict(user)
        return view_func(*args, **kwargs)

    return wrapper

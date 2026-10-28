import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, g

from auth import require_auth, verify_google_id_token, get_or_create_user, issue_app_jwt, AuthError
from database import get_db, close_db, init_db, now_iso
from services.festival_service import list_festivals, get_festival_by_id, FestivalServiceError, upcoming_festivals
from services.weather_service import get_weather, WeatherServiceError, CITIES
from services.mashup_service import build_festival_plan

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY", "dev-secret"),
        JWT_SECRET=os.getenv("JWT_SECRET", "dev-jwt-secret"),
        JWT_EXP_MINUTES=int(os.getenv("JWT_EXPIRY_MINUTES") or os.getenv("JWT_EXP_MINUTES", "120")),
        DATABASE_PATH=os.getenv("DATABASE_PATH", "utsav_india.db"),
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID", ""),
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)

    with app.app_context():
        init_db()

    app.teardown_appcontext(close_db)

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/config")
    def get_config():
        google_id = app.config.get("GOOGLE_CLIENT_ID")
        return jsonify(
            {
                "google_oauth_configured": bool(google_id),
                "google_client_id": google_id if google_id else None,
                "supported_cities": [x["name"] for x in CITIES.values()],
            }
        )

    @app.post("/api/auth/google")
    def google_auth():
        payload = request.get_json(silent=True) or {}
        credential = payload.get("credential")
        if not credential:
            return jsonify({"error": "Missing Google credential token."}), 400
        try:
            info = verify_google_id_token(credential)
            user = get_or_create_user(info)
            token, expires_at = issue_app_jwt(user)
        except AuthError as err:
            return jsonify({"error": str(err)}), 401
        return jsonify({"token": token, "expires_at": expires_at, "user": user})

    @app.get("/api/festivals")
    def festivals():
        filters = {
            "upcoming": request.args.get("upcoming"),
            "month": request.args.get("month"),
            "state": request.args.get("state"),
            "religion": request.args.get("religion"),
            "national_holiday": request.args.get("national_holiday"),
            "q": request.args.get("q"),
        }
        try:
            data = list_festivals(filters)
        except FestivalServiceError as err:
            return jsonify({"error": str(err)}), 502
        return jsonify(
            {
                "count": len(data),
                "data": data,
                "notice": "Festival dates may vary by regional tradition and source accuracy.",
            }
        )

    @app.get("/api/festivals/<int:festival_id>")
    def festival_details(festival_id):
        try:
            record = get_festival_by_id(festival_id)
        except FestivalServiceError as err:
            return jsonify({"error": str(err)}), 502
        if record is None:
            return jsonify({"error": "Festival not found."}), 404
        return jsonify(
            {
                "data": record,
                "notice": "Festival dates may vary by regional tradition and source accuracy.",
            }
        )

    @app.get("/api/weather")
    def weather():
        city = request.args.get("city", "")
        if not city:
            return jsonify({"error": "city is required."}), 400
        try:
            data = get_weather(city)
        except WeatherServiceError as err:
            return jsonify({"error": str(err)}), 400
        return jsonify(data)

    @app.get("/api/mashup/festival-plan")
    def festival_plan():
        festival_id = request.args.get("festival_id")
        city = request.args.get("city")
        selected_date = request.args.get("selected_date")
        if not festival_id or not city:
            return jsonify({"error": "festival_id and city are required."}), 400
        try:
            festival_id = int(festival_id)
        except ValueError:
            return jsonify({"error": "festival_id must be an integer."}), 400

        try:
            result, _, err = build_festival_plan(festival_id, city, selected_date)
        except WeatherServiceError as weather_err:
            return jsonify({"error": str(weather_err)}), 400
        except FestivalServiceError as fest_err:
            return jsonify({"error": str(fest_err)}), 502

        if err:
            return jsonify({"error": err}), 404
        return jsonify(result)

    @app.get("/api/me")
    @require_auth
    def me():
        db = get_db()
        user = g.current_user
        pref = db.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user["id"],)).fetchone()
        preferred_city = pref["preferred_city"] if pref else None
        return jsonify(
            {
                "id": user["id"],
                "email": user["email"],
                "name": user["name"],
                "picture": user["picture"],
                "preferred_city": preferred_city,
            }
        )

    @app.patch("/api/me")
    @require_auth
    def update_me():
        payload = request.get_json(silent=True) or {}
        preferred_city = payload.get("preferred_city")
        if preferred_city is not None:
            names = [x["name"].lower() for x in CITIES.values()]
            if preferred_city.lower() not in names:
                return jsonify({"error": "Unsupported city."}), 400
        db = get_db()
        user = g.current_user
        existing = db.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user["id"],)).fetchone()
        now = now_iso()
        if existing:
            db.execute(
                "UPDATE user_preferences SET preferred_city = ?, updated_at = ? WHERE user_id = ?",
                (preferred_city, now, user["id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO user_preferences (user_id, preferred_city, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], preferred_city, now, now),
            )
        db.commit()
        return jsonify({"message": "Profile updated.", "preferred_city": preferred_city})

    @app.get("/api/saved-festivals")
    @require_auth
    def list_saved_festivals():
        db = get_db()
        rows = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, religion, state_scope, created_at
            FROM saved_festivals
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (g.current_user["id"],),
        ).fetchall()
        return jsonify({"count": len(rows), "data": [dict(r) for r in rows]})

    @app.post("/api/saved-festivals")
    @require_auth
    def save_festival():
        payload = request.get_json(silent=True) or {}
        festival_id = payload.get("festival_id")
        if festival_id is None:
            return jsonify({"error": "festival_id is required."}), 400
        try:
            festival_id = int(festival_id)
        except ValueError:
            return jsonify({"error": "festival_id must be an integer."}), 400

        festival = get_festival_by_id(festival_id)
        if festival is None:
            return jsonify({"error": "Festival not found."}), 404

        db = get_db()
        now = now_iso()
        try:
            db.execute(
                """
                INSERT INTO saved_festivals (
                    user_id, festival_id, festival_name, festival_date, religion, state_scope, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    g.current_user["id"],
                    festival["id"],
                    festival.get("name") or "Unknown Festival",
                    festival.get("date"),
                    festival.get("religion"),
                    ",".join(festival.get("states") or []),
                    now,
                ),
            )
            db.commit()
        except Exception:
            return jsonify({"error": "Festival is already saved."}), 409

        row = db.execute(
            "SELECT id, festival_id, festival_name, festival_date, religion, state_scope, created_at FROM saved_festivals WHERE rowid = last_insert_rowid()"
        ).fetchone()
        return jsonify({"message": "Festival saved.", "data": dict(row)}), 201

    @app.get("/api/saved-festivals/<int:saved_id>")
    @require_auth
    def get_saved_festival(saved_id):
        db = get_db()
        row = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, religion, state_scope, created_at
            FROM saved_festivals
            WHERE id = ? AND user_id = ?
            """,
            (saved_id, g.current_user["id"]),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Saved festival not found."}), 404
        return jsonify({"data": dict(row)})

    @app.delete("/api/saved-festivals/<int:saved_id>")
    @require_auth
    def delete_saved_festival(saved_id):
        db = get_db()
        row = db.execute(
            "SELECT id FROM saved_festivals WHERE id = ? AND user_id = ?",
            (saved_id, g.current_user["id"]),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Saved festival not found."}), 404
        db.execute("DELETE FROM saved_festivals WHERE id = ? AND user_id = ?", (saved_id, g.current_user["id"]))
        db.commit()
        return jsonify({"message": "Saved festival deleted."})

    @app.get("/api/plans")
    @require_auth
    def list_plans():
        db = get_db()
        rows = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            FROM personal_plans
            WHERE user_id = ?
            ORDER BY celebration_date ASC, created_at DESC
            """,
            (g.current_user["id"],),
        ).fetchall()
        return jsonify({"count": len(rows), "data": [dict(r) for r in rows]})

    @app.get("/api/plans/<int:plan_id>")
    @require_auth
    def get_plan(plan_id):
        db = get_db()
        row = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            FROM personal_plans
            WHERE id = ? AND user_id = ?
            """,
            (plan_id, g.current_user["id"]),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Plan not found."}), 404
        return jsonify({"data": dict(row)})

    def _validate_plan_payload(payload, partial=False):
        required = [] if partial else ["festival_id", "city", "celebration_date"]
        for key in required:
            if key not in payload:
                return f"{key} is required."
        if "festival_id" in payload:
            try:
                int(payload["festival_id"])
            except (ValueError, TypeError):
                return "festival_id must be an integer."
        if "city" in payload:
            names = [x["name"].lower() for x in CITIES.values()]
            if not isinstance(payload["city"], str) or payload["city"].lower() not in names:
                return "Unsupported city."
        if "celebration_date" in payload:
            try:
                datetime.strptime(payload["celebration_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                return "celebration_date must be in YYYY-MM-DD format."
        return None

    @app.post("/api/plans")
    @require_auth
    def create_plan():
        payload = request.get_json(silent=True) or {}
        err = _validate_plan_payload(payload, partial=False)
        if err:
            return jsonify({"error": err}), 400

        festival_id = int(payload["festival_id"])
        festival = get_festival_by_id(festival_id)
        if festival is None:
            return jsonify({"error": "Festival not found."}), 404

        db = get_db()
        now = now_iso()
        db.execute(
            """
            INSERT INTO personal_plans (
                user_id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.current_user["id"],
                festival["id"],
                festival.get("name") or "Unknown Festival",
                festival.get("date"),
                payload["city"].title(),
                payload["celebration_date"],
                payload.get("notes"),
                now,
                now,
            ),
        )
        db.commit()
        row = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            FROM personal_plans WHERE rowid = last_insert_rowid()
            """
        ).fetchone()
        return jsonify({"message": "Plan created.", "data": dict(row)}), 201

    @app.put("/api/plans/<int:plan_id>")
    @require_auth
    def replace_plan(plan_id):
        payload = request.get_json(silent=True) or {}
        err = _validate_plan_payload(payload, partial=False)
        if err:
            return jsonify({"error": err}), 400
        db = get_db()
        row = db.execute(
            "SELECT id FROM personal_plans WHERE id = ? AND user_id = ?",
            (plan_id, g.current_user["id"]),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Plan not found."}), 404

        festival_id = int(payload["festival_id"])
        festival = get_festival_by_id(festival_id)
        if festival is None:
            return jsonify({"error": "Festival not found."}), 404
        now = now_iso()
        db.execute(
            """
            UPDATE personal_plans
            SET festival_id = ?, festival_name = ?, festival_date = ?, city = ?, celebration_date = ?, notes = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                festival["id"],
                festival.get("name") or "Unknown Festival",
                festival.get("date"),
                payload["city"].title(),
                payload["celebration_date"],
                payload.get("notes"),
                now,
                plan_id,
                g.current_user["id"],
            ),
        )
        db.commit()
        updated = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            FROM personal_plans WHERE id = ? AND user_id = ?
            """,
            (plan_id, g.current_user["id"]),
        ).fetchone()
        return jsonify({"message": "Plan updated.", "data": dict(updated)})

    @app.patch("/api/plans/<int:plan_id>")
    @require_auth
    def patch_plan(plan_id):
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"error": "At least one field is required."}), 400
        err = _validate_plan_payload(payload, partial=True)
        if err:
            return jsonify({"error": err}), 400

        db = get_db()
        existing = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes
            FROM personal_plans WHERE id = ? AND user_id = ?
            """,
            (plan_id, g.current_user["id"]),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Plan not found."}), 404

        updated = dict(existing)
        if "festival_id" in payload:
            festival = get_festival_by_id(int(payload["festival_id"]))
            if festival is None:
                return jsonify({"error": "Festival not found."}), 404
            updated["festival_id"] = festival["id"]
            updated["festival_name"] = festival.get("name") or "Unknown Festival"
            updated["festival_date"] = festival.get("date")
        if "city" in payload:
            updated["city"] = payload["city"].title()
        if "celebration_date" in payload:
            updated["celebration_date"] = payload["celebration_date"]
        if "notes" in payload:
            updated["notes"] = payload.get("notes")

        now = now_iso()
        db.execute(
            """
            UPDATE personal_plans
            SET festival_id = ?, festival_name = ?, festival_date = ?, city = ?, celebration_date = ?, notes = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                updated["festival_id"],
                updated["festival_name"],
                updated["festival_date"],
                updated["city"],
                updated["celebration_date"],
                updated.get("notes"),
                now,
                plan_id,
                g.current_user["id"],
            ),
        )
        db.commit()
        row = db.execute(
            """
            SELECT id, festival_id, festival_name, festival_date, city, celebration_date, notes, created_at, updated_at
            FROM personal_plans WHERE id = ? AND user_id = ?
            """,
            (plan_id, g.current_user["id"]),
        ).fetchone()
        return jsonify({"message": "Plan updated.", "data": dict(row)})

    @app.delete("/api/plans/<int:plan_id>")
    @require_auth
    def delete_plan(plan_id):
        db = get_db()
        row = db.execute(
            "SELECT id FROM personal_plans WHERE id = ? AND user_id = ?",
            (plan_id, g.current_user["id"]),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Plan not found."}), 404
        db.execute("DELETE FROM personal_plans WHERE id = ? AND user_id = ?", (plan_id, g.current_user["id"]))
        db.commit()
        return jsonify({"message": "Plan deleted."})

    @app.get("/api/dashboard/stats")
    @require_auth
    def dashboard_stats():
        db = get_db()
        user_id = g.current_user["id"]
        next_upcoming = None
        festivals_this_month = []
        try:
            upcoming = upcoming_festivals()
            next_upcoming = upcoming[0] if upcoming else None
            festivals_this_month = list_festivals({"month": str(datetime.now(timezone.utc).month)})
        except FestivalServiceError:
            upcoming = []
            festivals_this_month = []

        pref = db.execute("SELECT preferred_city FROM user_preferences WHERE user_id = ?", (user_id,)).fetchone()
        selected_city = pref["preferred_city"] if pref and pref["preferred_city"] else "Mumbai"

        weather_summary = None
        try:
            weather_summary = get_weather(selected_city)
        except WeatherServiceError:
            weather_summary = None

        saved_count = db.execute("SELECT COUNT(*) AS c FROM saved_festivals WHERE user_id = ?", (user_id,)).fetchone()["c"]
        plans = db.execute(
            """
            SELECT id, festival_name, city, celebration_date
            FROM personal_plans
            WHERE user_id = ? AND celebration_date >= date('now')
            ORDER BY celebration_date ASC
            LIMIT 5
            """,
            (user_id,),
        ).fetchall()
        return jsonify(
            {
                "greeting": f"Namaste, {g.current_user['name']}!",
                "next_upcoming_festival": next_upcoming,
                "festivals_this_month_count": len(festivals_this_month),
                "selected_city": selected_city,
                "weather_summary": weather_summary["current"] if weather_summary else None,
                "saved_festivals_count": saved_count,
                "upcoming_plans": [dict(x) for x in plans],
            }
        )

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="0.0.0.0", port=5000, debug=True)

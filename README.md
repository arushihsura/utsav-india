# Utsav India — Indian Festival & Weather Planner
**A Full-Stack Web Mashup & Cultural Travel Planning System**  
*College Lab Project — Web Technologies & Cloud Computing*

---

## 1. Project Overview & Architectural Design

**Utsav India** is a full-stack web application designed to help travelers, families, and cultural enthusiasts plan festival celebrations across India with meteorology intelligence. The application serves as an end-to-end demonstration of:

1. **Web Mashups:** Independent consumption, normalization, and semantic aggregation of two separate third-party services:
   - **Indian Festival API** (`https://indian-festival-api.vercel.app/api/festivals`): Cultural metadata, lunar/regional festival dates, religions, states, and descriptions.
   - **Open-Meteo Forecast API** (`https://api.open-meteo.com/v1/forecast`): Numerical weather forecasts, 7-day high/low temperatures, precipitation probability, and weather condition codes.
2. **Google Identity Services / OpenID Connect:** Identity verification via Google ID token validation.
3. **Application Session Tokens (PyJWT):** Decoupled authentication tokens (`HS256`) issued to authenticated clients with explicit expiry (`exp`) and claims (`sub`, `email`, `name`).
4. **Authorization & Multi-Tenant Data Isolation:** Strict user ownership enforcement on personal resources (saved festivals, celebration plans, preferences).
5. **RESTful Architecture:** Rigorous adherence to HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) and semantic HTTP status codes (`200`, `201`, `400`, `401`, `404`, `409`, `502`).
6. **SQLite Database Persistence:** Structured relational storage for users, preferences, bookmarks, and celebration itineraries.

---

## 2. Technology Stack

- **Backend:** Python 3.12, Flask 3.0.3
- **Database:** SQLite 3 (with foreign key enforcement and cascading deletes)
- **Token Cryptography:** PyJWT 2.9.0 (`HS256`)
- **OAuth Identity Transport:** `google-auth` 2.35.0 (OpenID Connect token verification)
- **HTTP Client & Networking:** Python `requests` 2.32.3
- **Configuration Management:** `python-dotenv` 1.0.1
- **Testing:** `pytest` 8.4.2
- **Frontend:** Semantic HTML5, Vanilla JavaScript (ES6+ async/await), Vanilla CSS3 (Custom Design System with Google Fonts: *Playfair Display* & *Plus Jakarta Sans*)

---

## 3. Directory Structure

```text
utsav_india/
├── app.py                      # Flask factory, route registration, REST API endpoints
├── auth.py                     # Google ID token verification, PyJWT issue/decode, @require_auth decorator
├── database.py                 # SQLite connection lifecycle, schema initialization, ISO timestamps
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment configuration template
├── .gitignore                  # Git exclusions for secrets, databases, and caches
├── README.md                   # Complete lab documentation and viva guide
├── services/
│   ├── festival_service.py     # Indian Festival API client, caching (TTL 300s), record normalization
│   ├── weather_service.py      # Open-Meteo API client, city geocoding mapping, weather code mapping
│   └── mashup_service.py       # Mashup aggregation pipeline and rule-based recommendation engine
├── static/
│   ├── app.js                  # Frontend controllers, modals, API explorer, and state management
│   ├── style.css               # Warm ivory & royal indigo design system, glassmorphism, responsive styles
│   └── hero_banner.jpg         # Festival banner graphic
├── templates/
│   └── index.html              # Single Page Application HTML shell
└── tests/
    ├── conftest.py             # Pytest fixtures, test database, test client, user & token factories
    ├── test_auth.py            # JWT issuance, decoding, expired/corrupt token rejection (401)
    ├── test_authorization.py   # Cross-user isolation and ownership tests (User A vs User B)
    ├── test_external_services.py # Resilience against upstream failures and timeouts (502 / 400)
    ├── test_mashup.py          # Weather-festival aggregation and rule-based suggestion rules
    ├── test_plans.py           # Personal celebration plans CRUD lifecycle (POST, GET, PUT, PATCH, DELETE)
    ├── test_saved_festivals.py # Saved festivals bookmarking, duplicate prevention (409), deletion
    └── test_validation.py      # Request body validation, unsupported city, bad date formats
```

---

## 4. Installation & Local Setup

### Step 1: Clone the Repository & Navigate to Workspace
```bash
cd /path/to/utsav_india
```

### Step 2: Set Up a Python Virtual Environment
```bash
# On Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# On Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to create your local `.env` file:
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env` to configure your secrets:
```ini
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=change-this-flask-session-secret-key-32chars
JWT_SECRET=change-this-jwt-cryptographic-secret-key-64chars
JWT_EXP_MINUTES=120
DATABASE_PATH=utsav_india.db
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
```

### Step 5: Start the Application Server
```bash
python app.py
```
Open your browser and navigate to: `http://localhost:5000`

---

## 5. Google OAuth 2.0 / OpenID Connect Configuration

To enable live Google Sign-In:

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project named `UtsavIndia-Lab`.
3. Under **APIs & Services** &rarr; **OAuth consent screen**:
   - Choose **External** user type.
   - Enter App name (`Utsav India`), User support email, and Developer contact email.
   - Add scopes: `email`, `profile`, `openid`.
4. Under **APIs & Services** &rarr; **Credentials**:
   - Click **Create Credentials** &rarr; **OAuth client ID**.
   - Application type: **Web application**.
   - **Authorized JavaScript origins**:
     - `http://localhost:5000`
     - `http://127.0.0.1:5000`
5. Copy your generated **Client ID** (e.g. `xxxxxxxxxxxx.apps.googleusercontent.com`).
6. Paste the Client ID into your `.env` file under `GOOGLE_CLIENT_ID`.
7. Restart the Flask application.

> [!NOTE]
> If `GOOGLE_CLIENT_ID` is unconfigured, the application clearly indicates this in the topbar and Profile page. Public browsing, festival exploration, weather forecasts, the Festival Planner mashup, and the API Explorer remain fully operable.

---

## 6. How the Festival-Weather Web Mashup Works

The core requirement of this project is the **Festival Planner Mashup**, exposed via:
```http
GET /api/mashup/festival-plan?festival_id=<id>&city=<city>&selected_date=<YYYY-MM-DD>
```

### Data Pipeline & Normalization:
```mermaid
flowchart LR
    A[Client Request] --> B[Mashup Service]
    B --> C[Indian Festival API]
    B --> D[Open-Meteo Weather API]
    C -->|Festival Metadata| E[Normalization Engine]
    D -->|7-Day Hourly/Daily Forecast| E
    E --> F[Rule-Based Suggestion Engine]
    F --> G[Unified JSON Response]
```

1. **Independent Queries:**
   - The server queries `services/festival_service.py` to retrieve the festival record by `festival_id` (cached in-memory for 300s to avoid rate limits).
   - The server queries `services/weather_service.py` for the requested city (mapped to exact coordinates: Mumbai, Delhi, Jaipur, Kolkata, Chennai, Bengaluru).
2. **Date Correlation:**
   - The user selects a celebration date (or defaults to the festival's official date).
   - The engine searches Open-Meteo's 7-day daily forecast array for a matching `date` (`YYYY-MM-DD`).
3. **Rule-Based Decision Logic:**
   - **High Precipitation Risk ($\ge 60\%$):** Alerts the user that rain probability is high; recommends arranging an indoor celebration backup or covered pavilion.
   - **Dry & Favorable Weather ($\le 30\%$):** Recommends outdoor celebration activities (e.g. open-air lighting of diyas, garba dances, terrace gatherings).
   - **Mixed Weather ($31\% - 59\%$):** Advises keeping flexible arrangements with both indoor and outdoor options.
   - **Outside Forecast Window:** If the festival date is beyond the 7-day horizon, the engine notes that reliable short-range numerical forecasts are not yet available, and shows current city conditions for context.
4. **Unified Normalization:** Returns normalized JSON combining festival profile, coordinates, forecast, planning suggestion, disclaimer, and upstream source attributions.

---

## 7. Database Architecture (SQLite)

The relational schema is automatically provisioned on startup via `init_db()` in [`database.py`](file:///c:/Users/arush/OneDrive/Desktop/Misc/campusconnect/utsav_india/database.py):

| Table | Purpose | Primary Key | Foreign Keys & Constraints |
|---|---|---|---|
| `users` | Stores authenticated user identities | `id AUTOINCREMENT` | `google_sub UNIQUE`, `email`, `created_at` |
| `user_preferences` | User settings such as preferred city | `id AUTOINCREMENT` | `user_id UNIQUE REFERENCES users(id) ON DELETE CASCADE` |
| `saved_festivals` | Bookmarked festival IDs per user | `id AUTOINCREMENT` | `UNIQUE(user_id, festival_id)`, `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |
| `personal_plans` | User-created celebration itineraries | `id AUTOINCREMENT` | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |

Foreign key enforcement is enabled on every SQLite connection via:
```sql
PRAGMA foreign_keys = ON;
```

---

## 8. REST API Endpoint Reference

| Method | Endpoint | Auth Required | Description | Status Codes |
|---|---|---|---|---|
| `GET` | `/` | No | Serves Single Page Application (`index.html`) | `200` |
| `GET` | `/api/config` | No | Returns server configuration (OAuth active status, supported cities) | `200` |
| `POST` | `/api/auth/google` | No | Exchanges Google ID token for Application JWT | `200`, `400`, `401` |
| `GET` | `/api/festivals` | No | Lists festivals with query filters (`upcoming`, `month`, `state`, `religion`, `national_holiday`, `q`) | `200`, `502` |
| `GET` | `/api/festivals/<id>` | No | Retrieves detailed festival metadata by ID | `200`, `404`, `502` |
| `GET` | `/api/weather` | No | Retrieves 7-day weather forecast for city (`?city=Mumbai`) | `200`, `400` |
| `GET` | `/api/mashup/festival-plan` | No | **Mashup:** Merges festival & weather with planning advice | `200`, `400`, `404`, `502` |
| `GET` | `/api/me` | **Yes (JWT)** | Retrieves signed-in user profile and preferred city | `200`, `401` |
| `PATCH` | `/api/me` | **Yes (JWT)** | Updates preferred city | `200`, `400`, `401` |
| `GET` | `/api/saved-festivals` | **Yes (JWT)** | Retrieves caller's bookmarked festivals | `200`, `401` |
| `POST` | `/api/saved-festivals` | **Yes (JWT)** | Bookmarks a festival (`{"festival_id": 1}`) | `201`, `400`, `401`, `409` |
| `GET` | `/api/saved-festivals/<id>` | **Yes (JWT)** | Retrieves a single saved festival record by ID | `200`, `401`, `404` |
| `DELETE` | `/api/saved-festivals/<id>` | **Yes (JWT)** | Removes a saved festival | `200`, `401`, `404` |
| `GET` | `/api/plans` | **Yes (JWT)** | Lists caller's celebration plans | `200`, `401` |
| `GET` | `/api/plans/<id>` | **Yes (JWT)** | Retrieves a specific celebration plan | `200`, `401`, `404` |
| `POST` | `/api/plans` | **Yes (JWT)** | Creates a celebration plan | `201`, `400`, `401`, `404` |
| `PUT` | `/api/plans/<id>` | **Yes (JWT)** | Full replacement update of a celebration plan | `200`, `400`, `401`, `404` |
| `PATCH` | `/api/plans/<id>` | **Yes (JWT)** | Partial update of a celebration plan | `200`, `400`, `401`, `404` |
| `DELETE` | `/api/plans/<id>` | **Yes (JWT)** | Deletes a celebration plan | `200`, `401`, `404` |
| `GET` | `/api/dashboard/stats` | **Yes (JWT)** | Computes live dashboard metrics | `200`, `401` |

---

## 9. cURL & Postman Testing Guide

### 1. Fetch Festivals with Filters
```bash
curl -X GET "http://localhost:5000/api/festivals?religion=hindu&month=11"
```

### 2. Fetch City Weather Forecast
```bash
curl -X GET "http://localhost:5000/api/weather?city=Mumbai"
```

### 3. Execute the Festival-Weather Mashup
```bash
curl -X GET "http://localhost:5000/api/mashup/festival-plan?festival_id=1&city=Mumbai&selected_date=2026-11-08"
```

### 4. Test Protected Endpoint Without Token (Verifying 401 Unauthorized)
```bash
curl -i -X GET "http://localhost:5000/api/plans"
# Expected response: HTTP/1.1 401 UNAUTHORIZED
# {"error":"Missing or invalid Authorization header."}
```

### 5. Access Protected Endpoint with Valid JWT
```bash
curl -X GET "http://localhost:5000/api/plans" \
  -H "Authorization: Bearer YOUR_APPLICATION_JWT_HERE"
```

### 6. Create a Celebration Plan (POST)
```bash
curl -X POST "http://localhost:5000/api/plans" \
  -H "Authorization: Bearer YOUR_APPLICATION_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"festival_id": 1, "city": "Jaipur", "celebration_date": "2026-11-08", "notes": "Diwali sweets gathering"}'
```

### 7. Partial Update of Plan (PATCH)
```bash
curl -X PATCH "http://localhost:5000/api/plans/1" \
  -H "Authorization: Bearer YOUR_APPLICATION_JWT_HERE" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated: sweets purchased and venue reserved"}'
```

---

## 10. Conceptual Reference for Lab Evaluation

### A. OAuth 2.0 / OpenID Connect vs. Application JWT
- **Google OpenID Connect (ID Token):** A cryptographically signed identity assertion issued by Google (`accounts.google.com`). Its role is **Authentication** (proving *who* the user is to the backend). The backend validates Google's signature and claims (`sub`, `aud`, `iss`) once during login.
- **Application JWT:** A compact, self-contained token issued by *our Flask backend* using `JWT_SECRET`. Its role is **Authorization & Session State** on subsequent requests to our own API. It prevents making outbound network calls to Google on every API request, reducing latency from ~300ms to <1ms.

### B. Authentication vs. Authorization
- **Authentication (AuthN):** "Who are you?" Validating identity credentials (e.g. verifying Google ID token signature).
- **Authorization (AuthZ):** "What are you allowed to access?" Determining permissions on resources. In Utsav India, ownership checks guarantee that User A cannot read, edit, or delete celebration plans belonging to User B, even if User A provides a valid JWT.

### C. REST Architecture & HTTP Methods
- `GET`: Safe, idempotent retrieval of resource representations without side-effects.
- `POST`: Non-idempotent creation of a subordinate resource (returns `201 Created` with URI/resource payload).
- `PUT`: Idempotent full replacement of the resource state. All required fields must be supplied.
- `PATCH`: Partial modification of specific resource attributes.
- `DELETE`: Idempotent removal of the resource (returns `200 OK` or `204 No Content`).

---

## 11. Automated Testing Suite

The project includes 25 unit and integration tests under `tests/`:

```bash
pytest -v
```

### Coverage Highlights:
- **`tests/test_auth.py`:** JWT generation, signature decoding, expired token rejection (401), malformed headers, missing headers.
- **`tests/test_authorization.py`:** Multi-tenant isolation; verifies User B receives 404 when attempting to read, PUT, PATCH, or DELETE User A's plans or saved festivals.
- **`tests/test_plans.py`:** Complete CRUD lifecycle (POST 201, GET 200, PUT 200, PATCH 200, DELETE 200, 404 handling).
- **`tests/test_saved_festivals.py`:** Bookmarking, uniqueness constraint checking (409 Conflict on duplicate save), deletion.
- **`tests/test_mashup.py`:** Verification of weather-festival correlation, precipitation thresholds ($\ge 60\%$, $\le 30\%$, mixed), and forecast window boundary checking.
- **`tests/test_validation.py`:** Input schema enforcement, invalid cities, malformed dates, non-integer IDs.
- **`tests/test_external_services.py`:** Upstream error resilience (handling 500/timeout from Indian Festival API or Open-Meteo as 502/400).

---

/* ==========================================================================
   UTSAV INDIA — CLIENT APPLICATION JAVASCRIPT
   Full-Stack Cultural & Weather Planning Application
   ========================================================================== */

const state = {
  token: localStorage.getItem("utsav_token") || null,
  config: null,
  me: null,
  festivals: [],
  savedFestivals: [],
  plans: [],
  activeFestivalForModal: null,
  editingPlanId: null,
};

// Weather code to emoji icon helper
function weatherCodeToIcon(code) {
  if (code === 0 || code === 1) return "☀️";
  if (code === 2) return "⛅";
  if (code === 3) return "☁️";
  if (code === 45 || code === 48) return "🌫️";
  if (code >= 51 && code <= 55) return "🌦️";
  if (code >= 61 && code <= 65) return "🌧️";
  if (code >= 71 && code <= 75) return "❄️";
  if (code >= 80 && code <= 82) return "⛈️";
  if (code >= 95) return "⚡";
  return "🌤️";
}

// Format date nicely (e.g. 2026-11-08 -> Nov 8, 2026)
function formatDatePretty(dateStr) {
  if (!dateStr) return "Date TBD";
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const d = new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" });
    }
  } catch (_) {}
  return dateStr;
}

// Toast notification helper
function showToast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.style.borderLeftColor = isError ? "var(--danger)" : "var(--saffron)";
  el.style.display = "block";
  setTimeout(() => {
    el.style.display = "none";
  }, 2800);
}

// Section navigation controller
function setActiveSection(name) {
  document.querySelectorAll(".view-section").forEach((s) => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));

  const targetSection = document.getElementById(`section-${name}`);
  const targetNav = document.getElementById(`nav-${name}`);
  if (targetSection) targetSection.classList.add("active");
  if (targetNav) targetNav.classList.add("active");

  const titleEl = document.getElementById("current-section-title");
  if (titleEl && targetNav) {
    const label = targetNav.querySelector(".nav-label");
    if (label) titleEl.textContent = label.textContent;
  }

  // Close mobile sidebar if open
  document.getElementById("sidebar").classList.remove("open");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Unified API fetcher with timing and error normalization
async function apiFetch(path, opts = {}) {
  const headers = opts.headers || {};
  if (opts.body && typeof opts.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (state.token && opts.sendToken !== false) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  const start = performance.now();
  let response, data;
  try {
    response = await fetch(path, { ...opts, headers });
    const elapsed = Math.round(performance.now() - start);
    try {
      data = await response.json();
    } catch (_) {
      data = { raw: await response.text() };
    }
    return { response, data, elapsed };
  } catch (err) {
    const elapsed = Math.round(performance.now() - start);
    return {
      response: { ok: false, status: 0, statusText: "Network Error" },
      data: { error: err.message || "Network request failed." },
      elapsed,
    };
  }
}

// ==========================================================================
// CONFIGURATION & INITIALIZATION
// ==========================================================================

async function loadConfig() {
  const { data } = await apiFetch("/api/config");
  state.config = data || {};

  const cities = state.config.supported_cities || ["Mumbai", "Delhi", "Jaipur", "Kolkata", "Chennai", "Bengaluru"];
  const citySelectIds = ["planner-city", "weather-city", "plan-city", "edit-plan-city", "preferred-city"];

  citySelectIds.forEach((id) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    cities.forEach((city) => {
      const opt = document.createElement("option");
      opt.value = city;
      opt.textContent = city;
      el.appendChild(opt);
    });
  });

  // Update OAuth status notes in Profile section
  const oauthBadge = document.getElementById("oauth-status-badge");
  const oauthDesc = document.getElementById("oauth-status-desc");
  if (state.config.google_oauth_configured) {
    oauthBadge.textContent = "✅ Google OAuth 2.0 / OpenID Connect Active";
    oauthBadge.style.color = "var(--success)";
    oauthDesc.textContent = `Client ID: ${state.config.google_client_id}`;
  } else {
    oauthBadge.textContent = "⚠️ Google OAuth Unconfigured in .env";
    oauthBadge.style.color = "var(--warning)";
    oauthDesc.innerHTML =
      "To test Google Sign-In with real Google accounts, obtain a Client ID from Google Cloud Console and set <code>GOOGLE_CLIENT_ID</code> in <code>.env</code>. Public features and JWT testing via API Explorer are fully functional.";
  }
}

// ==========================================================================
// USER AUTHENTICATION & PROFILE
// ==========================================================================

async function loadMe() {
  const authContainer = document.getElementById("google-auth-container");
  const userPill = document.getElementById("user-pill");
  const nameEl = document.getElementById("user-display-name");
  const statusEl = document.getElementById("user-display-status");
  const avatarEl = document.getElementById("user-avatar");

  if (!state.token) {
    state.me = null;
    userPill.className = "user-pill guest";
    nameEl.textContent = "Guest User";
    statusEl.textContent = "Not signed in";
    avatarEl.textContent = "👤";

    document.getElementById("profile-name").textContent = "Guest User";
    document.getElementById("profile-email").textContent = "Not signed in";
    document.getElementById("profile-auth-type").textContent = "None";
    document.getElementById("profile-preferred-city-val").textContent = "Not set";
    document.getElementById("profile-avatar-big").textContent = "👤";
    return;
  }

  const { response, data } = await apiFetch("/api/me");
  if (!response.ok) {
    state.token = null;
    localStorage.removeItem("utsav_token");
    loadMe();
    return;
  }

  state.me = data;
  userPill.className = "user-pill authenticated";
  nameEl.textContent = data.name || "Signed-in User";
  statusEl.textContent = data.email || "Active Session";

  if (data.picture) {
    avatarEl.innerHTML = `<img src="${data.picture}" alt="${data.name}" />`;
    document.getElementById("profile-avatar-big").innerHTML = `<img src="${data.picture}" alt="${data.name}" />`;
  } else {
    const initial = (data.name || "U")[0].toUpperCase();
    avatarEl.textContent = initial;
    document.getElementById("profile-avatar-big").textContent = initial;
  }

  document.getElementById("profile-name").textContent = data.name;
  document.getElementById("profile-email").textContent = data.email;
  document.getElementById("profile-auth-type").textContent = "Google OpenID Connect + PyJWT";
  document.getElementById("profile-preferred-city-val").textContent = data.preferred_city || "Default (Mumbai)";

  if (data.preferred_city) {
    document.getElementById("preferred-city").value = data.preferred_city;
  }
}

function initGoogleSignIn() {
  const container = document.getElementById("google-auth-container");
  if (!state.config || !state.config.google_oauth_configured) {
    container.innerHTML = `<span class="badge badge-subtle">OAuth Pending Setup</span>`;
    return;
  }

  if (!window.google || !window.google.accounts || !window.google.accounts.id) {
    setTimeout(initGoogleSignIn, 350);
    return;
  }

  try {
    google.accounts.id.initialize({
      client_id: state.config.google_client_id,
      callback: async (response) => {
        const { response: authResp, data } = await apiFetch("/api/auth/google", {
          method: "POST",
          body: JSON.stringify({ credential: response.credential }),
        });

        if (!authResp.ok) {
          showToast(data.error || "Google sign-in failed.", true);
          return;
        }

        state.token = data.token;
        localStorage.setItem("utsav_token", data.token);
        showToast(`Welcome, ${data.user.name}!`);

        await loadMe();
        await loadDashboard();
        await loadSavedFestivals();
        await loadPlans();
      },
    });

    google.accounts.id.renderButton(container, {
      theme: "outline",
      size: "medium",
      text: "signin_with",
      shape: "pill",
    });
  } catch (err) {
    console.error("Google sign-in initialization error:", err);
  }
}

async function savePreferredCity() {
  if (!state.token) {
    showToast("Please sign in to update preferences.", true);
    return;
  }
  const city = document.getElementById("preferred-city").value;
  const { response, data } = await apiFetch("/api/me", {
    method: "PATCH",
    body: JSON.stringify({ preferred_city: city }),
  });
  if (!response.ok) {
    showToast(data.error || "Unable to update preference.", true);
    return;
  }
  showToast("Preferred city updated!");
  await loadMe();
  await loadDashboard();
}

function logout() {
  state.token = null;
  state.me = null;
  localStorage.removeItem("utsav_token");
  showToast("Logged out successfully.");
  loadMe();
  loadDashboard();
  loadSavedFestivals();
  loadPlans();
}

// ==========================================================================
// DASHBOARD & OVERVIEW
// ==========================================================================

async function loadDashboard() {
  const cardsContainer = document.getElementById("dashboard-cards");
  const plansPreview = document.getElementById("dashboard-plans-preview");
  const weatherPreview = document.getElementById("dashboard-weather-preview");
  const greetingEl = document.getElementById("greeting-text");

  if (!state.token) {
    greetingEl.textContent = "Namaste! Welcome to Utsav India";
    cardsContainer.innerHTML = `
      <div class="kpi-card">
        <div class="kpi-header"><span class="kpi-title">Sign In Required</span><span class="kpi-icon">🔐</span></div>
        <div class="kpi-value" style="font-size: 1.25rem;">Personalized Dashboard</div>
        <div class="kpi-subtitle">Sign in with Google to view personal celebration metrics and plans.</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header"><span class="kpi-title">Public Mashup</span><span class="kpi-icon">🌤️</span></div>
        <div class="kpi-value" style="font-size: 1.25rem;">Live Weather Planner</div>
        <div class="kpi-subtitle">Explore 40+ Indian festivals and 7-day weather forecasts without logging in.</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header"><span class="kpi-title">API Explorer</span><span class="kpi-icon">⚡</span></div>
        <div class="kpi-value" style="font-size: 1.25rem;">Lab Testing Console</div>
        <div class="kpi-subtitle">Test REST endpoints, CRUD methods, and HTTP status codes.</div>
      </div>
    `;

    plansPreview.innerHTML = `<p class="muted">Sign in to schedule and view your upcoming celebration plans.</p>`;
    weatherPreview.innerHTML = `
      <p>Select any Indian city in the <strong>Weather</strong> or <strong>Festival Planner</strong> tab to view live forecasts.</p>
    `;
    return;
  }

  const { response, data } = await apiFetch("/api/dashboard/stats");
  if (!response.ok) {
    cardsContainer.innerHTML = `<div class="card"><p class="muted">${data.error || "Unable to load dashboard."}</p></div>`;
    return;
  }

  greetingEl.textContent = data.greeting || "Namaste!";

  const nextFest = data.next_upcoming_festival;
  const nextFestText = nextFest ? `${nextFest.name}` : "None scheduled";
  const nextFestDate = nextFest ? formatDatePretty(nextFest.date) : "N/A";

  const weather = data.weather_summary;
  const weatherText = weather ? `${weather.temperature_c}°C, ${weather.weather_text}` : "Weather unavailable";
  const weatherIcon = weather ? weatherCodeToIcon(weather.weather_code) : "🌤️";

  cardsContainer.innerHTML = `
    <div class="kpi-card">
      <div class="kpi-header"><span class="kpi-title">Next Festival</span><span class="kpi-icon">🪔</span></div>
      <div class="kpi-value">${nextFestText}</div>
      <div class="kpi-subtitle">${nextFestDate}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-header"><span class="kpi-title">This Month</span><span class="kpi-icon">🏮</span></div>
      <div class="kpi-value">${data.festivals_this_month_count}</div>
      <div class="kpi-subtitle">Festivals happening this month</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-header"><span class="kpi-title">${data.selected_city || "City"} Weather</span><span class="kpi-icon">${weatherIcon}</span></div>
      <div class="kpi-value">${weather ? `${weather.temperature_c}°C` : "N/A"}</div>
      <div class="kpi-subtitle">${weather ? weather.weather_text : "Unavailable"}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-header"><span class="kpi-title">Saved Festivals</span><span class="kpi-icon">⭐</span></div>
      <div class="kpi-value">${data.saved_festivals_count}</div>
      <div class="kpi-subtitle">Bookmarked in your library</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-header"><span class="kpi-title">Upcoming Plans</span><span class="kpi-icon">📅</span></div>
      <div class="kpi-value">${data.upcoming_plans.length}</div>
      <div class="kpi-subtitle">Celebrations scheduled</div>
    </div>
  `;

  // Upcoming plans preview
  if (data.upcoming_plans.length) {
    plansPreview.innerHTML = `
      <ul style="padding-left: 1.25rem; margin: 0; line-height: 1.8;">
        ${data.upcoming_plans
          .map(
            (p) =>
              `<li><strong>${p.festival_name}</strong> in ${p.city} &mdash; <span class="muted">${formatDatePretty(
                p.celebration_date
              )}</span></li>`
          )
          .join("")}
      </ul>
    `;
  } else {
    plansPreview.innerHTML = `
      <p class="muted">No upcoming celebrations scheduled yet.</p>
      <button class="btn btn-sm btn-secondary" onclick="setActiveSection('planner')">Create a Plan</button>
    `;
  }

  // Weather preview
  if (weather) {
    weatherPreview.innerHTML = `
      <div style="display: flex; align-items: center; gap: 1rem;">
        <span style="font-size: 2.2rem;">${weatherIcon}</span>
        <div>
          <h4 style="margin: 0; font-size: 1.2rem;">${data.selected_city}: ${weather.temperature_c}°C</h4>
          <p class="muted" style="margin: 0;">${weather.weather_text}</p>
        </div>
      </div>
    `;
  } else {
    weatherPreview.innerHTML = `<p class="muted">Weather forecast not loaded.</p>`;
  }
}

// ==========================================================================
// INDIAN FESTIVAL EXPLORER
// ==========================================================================

async function loadFestivals() {
  const q = document.getElementById("festival-search").value.trim();
  const month = document.getElementById("festival-month").value;
  const stateFilter = document.getElementById("festival-state").value.trim();
  const religion = document.getElementById("festival-religion").value;
  const nationalHoliday = document.getElementById("festival-national-holiday").checked;

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (month) params.set("month", month);
  if (stateFilter) params.set("state", stateFilter);
  if (religion) params.set("religion", religion);
  if (nationalHoliday) params.set("national_holiday", "true");

  const listEl = document.getElementById("festival-list");
  listEl.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>Searching festivals...</p></div>`;

  const { response, data } = await apiFetch(`/api/festivals?${params.toString()}`);
  if (!response.ok) {
    listEl.innerHTML = `<div class="empty-state card"><p class="muted">${data.error || "Unable to load festivals."}</p></div>`;
    return;
  }

  state.festivals = data.data || [];
  updateFestivalSelectDropdowns();

  if (!state.festivals.length) {
    listEl.innerHTML = `
      <div class="empty-state card">
        <div class="empty-icon">🔍</div>
        <h3>No festivals matched your filters</h3>
        <p class="muted">Try adjusting your search keywords, religion filter, or month selection.</p>
        <button class="btn btn-secondary" onclick="resetFestivalFilters()">Reset Filters</button>
      </div>
    `;
    return;
  }

  listEl.innerHTML = state.festivals.map((f) => renderFestivalCardHtml(f)).join("");
}

function renderFestivalCardHtml(festival) {
  const isSaved = state.savedFestivals.some((s) => s.festival_id === festival.id);
  const religionTag = festival.religion ? `<span class="tag tag-religion">${festival.religion}</span>` : "";
  const holidayTag = festival.national_holiday ? `<span class="tag tag-holiday">National Holiday</span>` : "";
  const dateTag = festival.date ? `<span class="tag tag-date">${formatDatePretty(festival.date)}</span>` : "";

  return `
    <article class="festival-card" id="fest-card-${festival.id}">
      <div>
        <div class="festival-card-top">
          <h3 class="festival-name">${festival.name}</h3>
          <button class="festival-save-btn ${isSaved ? "saved" : ""}" 
                  title="${isSaved ? "Saved" : "Save festival"}" 
                  onclick="toggleSaveFestival(${festival.id})">
            ${isSaved ? "★" : "☆"}
          </button>
        </div>

        <div class="festival-tags">
          ${dateTag}
          ${religionTag}
          ${holidayTag}
        </div>

        <p class="festival-desc">${festival.description || "Traditional celebration observed across Indian communities."}</p>
      </div>

      <div>
        <div class="festival-meta-footer">
          <span>ID: #${festival.id}</span>
          <span>${festival.states && festival.states.length ? festival.states[0] : "All India"}</span>
        </div>

        <div class="festival-actions">
          <button class="btn btn-sm btn-secondary" onclick="openFestivalDetailModal(${festival.id})">View Details</button>
          <button class="btn btn-sm btn-primary" onclick="planFestivalDirect(${festival.id})">Plan Festival 🌤️</button>
        </div>
      </div>
    </article>
  `;
}

function resetFestivalFilters() {
  document.getElementById("festival-search").value = "";
  document.getElementById("festival-month").value = "";
  document.getElementById("festival-state").value = "";
  document.getElementById("festival-religion").value = "";
  document.getElementById("festival-national-holiday").checked = false;
  loadFestivals();
}

function updateFestivalSelectDropdowns() {
  const plannerSel = document.getElementById("planner-festival-select");
  const planFormSel = document.getElementById("plan-festival-select");

  [plannerSel, planFormSel].forEach((sel) => {
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = `<option value="">-- Choose a festival (${state.festivals.length} available) --</option>`;
    state.festivals.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = `${f.name} (${f.date || "Date TBD"})`;
      sel.appendChild(opt);
    });
    if (currentVal) sel.value = currentVal;
  });
}

// ==========================================================================
// FESTIVAL DETAIL MODAL
// ==========================================================================

async function openFestivalDetailModal(festivalId) {
  const modal = document.getElementById("festival-detail-modal");
  const bodyEl = document.getElementById("modal-festival-body");
  const titleEl = document.getElementById("modal-festival-name");

  titleEl.textContent = "Loading Festival...";
  bodyEl.innerHTML = `<div class="loading-state"><div class="spinner"></div></div>`;
  modal.classList.add("open");

  const { response, data } = await apiFetch(`/api/festivals/${festivalId}`);
  if (!response.ok) {
    bodyEl.innerHTML = `<p class="muted">${data.error || "Unable to load festival details."}</p>`;
    return;
  }

  const f = data.data;
  state.activeFestivalForModal = f;
  titleEl.textContent = f.name;

  let localNamesHtml = "None documented";
  if (f.local_names && Object.keys(f.local_names).length) {
    localNamesHtml = Object.entries(f.local_names)
      .map(([lang, name]) => `<strong>${lang.toUpperCase()}:</strong> ${name}`)
      .join(" &bull; ");
  }

  const alsoKnown = f.also_known_as && f.also_known_as.length ? f.also_known_as.join(", ") : "None";
  const statesList = f.states && f.states.length ? f.states.join(", ") : "All India";

  bodyEl.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div class="festival-tags">
        ${f.date ? `<span class="tag tag-date">📅 ${formatDatePretty(f.date)}</span>` : ""}
        ${f.religion ? `<span class="tag tag-religion">🕉️ ${f.religion.toUpperCase()}</span>` : ""}
        ${f.national_holiday ? `<span class="tag tag-holiday">🇮🇳 National Holiday</span>` : ""}
      </div>

      <div>
        <h4 style="margin: 0 0 0.35rem 0; color: var(--royal-indigo);">About this Celebration</h4>
        <p style="margin: 0; line-height: 1.6; color: var(--text-secondary);">${f.description || "No detailed description available."}</p>
      </div>

      <div style="background: var(--surface-muted); padding: 1rem; border-radius: var(--radius-sm); font-size: 0.9rem; line-height: 1.7;">
        <div><strong>Regional Script Names:</strong> ${localNamesHtml}</div>
        <div><strong>Also Known As:</strong> ${alsoKnown}</div>
        <div><strong>Observed In:</strong> ${statesList}</div>
        <div><strong>Calendar Timing:</strong> Month ${f.month || "N/A"}, Day ${f.day || "N/A"}</div>
      </div>

      <div class="api-notice-bar" style="margin: 0;">
        <small>Source: <a href="${f.source || "https://indian-festival-api.vercel.app"}" target="_blank" rel="noopener">Indian Festival API</a>. Festival dates may vary by regional traditions and lunar calendars.</small>
      </div>
    </div>
  `;

  // Bind footer modal action buttons
  document.getElementById("modal-save-action").onclick = () => toggleSaveFestival(f.id);
  document.getElementById("modal-plan-action").onclick = () => {
    closeFestivalDetailModal();
    planFestivalDirect(f.id);
  };
}

function closeFestivalDetailModal() {
  document.getElementById("festival-detail-modal").classList.remove("open");
}

function planFestivalDirect(festivalId) {
  const sel = document.getElementById("planner-festival-select");
  if (sel) {
    sel.value = festivalId;
    triggerFestivalSelectionChange();
  }
  setActiveSection("planner");
}

// ==========================================================================
// FESTIVAL PLANNER (WEB MASHUP)
// ==========================================================================

function triggerFestivalSelectionChange() {
  const festivalId = document.getElementById("planner-festival-select").value;
  if (!festivalId) return;

  const f = state.festivals.find((item) => String(item.id) === String(festivalId));
  if (f && f.date) {
    document.getElementById("planner-date").value = f.date;
  }
}

async function runPlannerMashup() {
  const festivalId = document.getElementById("planner-festival-select").value;
  const city = document.getElementById("planner-city").value;
  const selectedDate = document.getElementById("planner-date").value;
  const resultContainer = document.getElementById("planner-result-container");

  if (!festivalId) {
    showToast("Please choose a festival first.", true);
    return;
  }
  if (!city) {
    showToast("Please select a city.", true);
    return;
  }

  resultContainer.innerHTML = `
    <div class="loading-state card">
      <div class="spinner"></div>
      <p>Building mashup: Querying Indian Festival API & Open-Meteo Weather...</p>
    </div>
  `;

  const params = new URLSearchParams({ festival_id: festivalId, city });
  if (selectedDate) params.set("selected_date", selectedDate);

  const { response, data } = await apiFetch(`/api/mashup/festival-plan?${params.toString()}`);
  if (!response.ok) {
    resultContainer.innerHTML = `
      <div class="card empty-state">
        <h3>Unable to generate mashup plan</h3>
        <p class="muted">${data.error || "An error occurred."}</p>
      </div>
    `;
    return;
  }

  const f = data.festival || {};
  const loc = data.location || {};
  const forecast = data.forecast_for_selected_date;
  const inWindow = data.forecast_available_for_selected_date;
  const current = data.weather_summary || {};

  // Determine recommendation styling class
  let recClass = "forecast-unavailable";
  let recBadgeText = "Forecast Notice";
  if (inWindow && forecast) {
    const rain = forecast.precipitation_probability;
    if (rain !== null && rain !== undefined) {
      if (rain >= 60) {
        recClass = "indoor-backup";
        recBadgeText = "Indoor Venue Advised 🌧️";
      } else if (rain <= 30) {
        recClass = "outdoor-suitable";
        recBadgeText = "Outdoor Celebration Favorable ☀️";
      } else {
        recClass = "mixed-conditions";
        recBadgeText = "Flexible Arrangements Advised ⛅";
      }
    } else {
      recClass = "mixed-conditions";
      recBadgeText = "Weather Guidance";
    }
  }

  resultContainer.innerHTML = `
    <article class="mashup-result-card">
      <div class="mashup-result-header">
        <div class="mashup-header-title">
          <h3>${f.name} &bull; ${loc.city} Celebration</h3>
          <span class="mashup-meta-pill">📅 Date: ${formatDatePretty(data.selected_date)}</span>
          <span class="mashup-meta-pill">📍 Lat ${loc.coordinates ? loc.coordinates.latitude : ""}, Lon ${loc.coordinates ? loc.coordinates.longitude : ""}</span>
        </div>
        <div>
          ${state.token ? `<button class="btn btn-secondary" onclick="quickSavePlanFromMashup(${f.id}, '${loc.city}', '${data.selected_date}')">💾 Save to My Plans</button>` : `<span class="badge badge-subtle">Sign in to save plan</span>`}
        </div>
      </div>

      <div class="mashup-body">
        <div class="mashup-column">
          <div class="mashup-subcard">
            <h4>🏮 Festival Profile</h4>
            <p><strong>Festival:</strong> ${f.name}</p>
            <p><strong>Official Date:</strong> ${formatDatePretty(f.date)}</p>
            <p><strong>Tradition:</strong> ${f.religion ? f.religion.toUpperCase() : "Cultural"}</p>
            <p class="muted" style="font-size: 0.88rem;">${f.description || ""}</p>
          </div>

          <div class="mashup-subcard">
            <h4>💡 Rule-Based Planning Recommendation</h4>
            <div class="recommendation-callout ${recClass}">
              <span class="rec-badge">${recBadgeText}</span>
              <p class="rec-text">${data.planning_suggestion}</p>
            </div>
          </div>
        </div>

        <div class="mashup-column">
          <div class="mashup-subcard">
            <h4>🌦️ Weather for Celebration Date (${formatDatePretty(data.selected_date)})</h4>
            ${
              forecast
                ? `
              <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.75rem;">
                <span style="font-size: 2.8rem;">${weatherCodeToIcon(forecast.weather_code)}</span>
                <div>
                  <div style="font-size: 1.5rem; font-weight: 700;">${forecast.weather_text}</div>
                  <div style="color: var(--text-secondary);">Max: ${forecast.temp_max_c}°C &bull; Min: ${forecast.temp_min_c}°C</div>
                </div>
              </div>
              <div style="background: #fff; padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-light);">
                <strong>Precipitation Probability:</strong> ${forecast.precipitation_probability !== null ? `${forecast.precipitation_probability}%` : "Not available"}
              </div>
            `
                : `
              <div class="empty-state" style="padding: 1.5rem 1rem;">
                <p>The celebration date (<strong>${formatDatePretty(data.selected_date)}</strong>) falls outside Open-Meteo's 7-day high-precision forecast window.</p>
                <p class="muted" style="font-size: 0.85rem;">Current ${loc.city} temperature is <strong>${current.temperature_c ?? "N/A"}°C</strong> with ${current.weather_text || "clear sky"}. Re-check closer to the date for daily forecasts.</p>
              </div>
            `
            }
          </div>
        </div>
      </div>

      <div class="mashup-footer">
        <small class="muted">${data.disclaimer}</small>
        <small class="muted">Mashup Pipeline: Indian Festival API &bull; Open-Meteo API</small>
      </div>
    </article>
  `;
}

async function quickSavePlanFromMashup(festivalId, city, celebrationDate) {
  if (!state.token) {
    showToast("Please sign in first.", true);
    return;
  }
  const payload = {
    festival_id: festivalId,
    city,
    celebration_date: celebrationDate,
    notes: "Created via Festival Planner Mashup",
  };
  const { response, data } = await apiFetch("/api/plans", { method: "POST", body: JSON.stringify(payload) });
  if (!response.ok) {
    showToast(data.error || "Unable to save plan.", true);
    return;
  }
  showToast("Plan added to your schedule!");
  await loadPlans();
  await loadDashboard();
}

// ==========================================================================
// WEATHER INTEGRATION
// ==========================================================================

async function loadWeather() {
  const city = document.getElementById("weather-city").value;
  const resultEl = document.getElementById("weather-result");

  resultEl.innerHTML = `<div class="loading-state card"><div class="spinner"></div><p>Fetching forecast from Open-Meteo...</p></div>`;

  const { response, data } = await apiFetch(`/api/weather?city=${encodeURIComponent(city)}`);
  if (!response.ok) {
    resultEl.innerHTML = `<div class="card empty-state"><p class="muted">${data.error || "Unable to load weather."}</p></div>`;
    return;
  }

  const cur = data.current || {};
  const forecastDays = data.forecast || [];

  const daysHtml = forecastDays
    .map((day) => {
      const icon = weatherCodeToIcon(day.weather_code);
      const rain = day.precipitation_probability !== null ? `${day.precipitation_probability}% rain` : "N/A";
      return `
      <div class="forecast-day-card">
        <span class="forecast-date-str">${formatDatePretty(day.date)}</span>
        <span class="forecast-icon">${icon}</span>
        <span style="font-size: 0.82rem; color: var(--text-secondary);">${day.weather_text}</span>
        <span class="forecast-temp-range">${day.temp_max_c}° / ${day.temp_min_c}°</span>
        <span class="forecast-rain-pill">${rain}</span>
      </div>
    `;
    })
    .join("");

  resultEl.innerHTML = `
    <div class="weather-hero">
      <div class="weather-hero-left">
        <h3>${data.city}</h3>
        <p class="muted" style="color: #cbd5e1; margin: 0 0 0.5rem 0;">Coordinates: Lat ${data.coordinates.latitude}, Lon ${data.coordinates.longitude}</p>
        <div class="weather-condition-text">${cur.weather_text || "Clear sky"}</div>
      </div>
      <div class="weather-temp-big">
        <span>${weatherCodeToIcon(cur.weather_code)}</span>
        <span>${cur.temperature_c ?? "--"}°C</span>
      </div>
    </div>

    <h4 style="font-family: var(--font-heading); color: var(--royal-indigo); margin-bottom: 0.85rem;">7-Day Daily Forecast</h4>
    <div class="forecast-days-grid">${daysHtml}</div>
  `;
}

// ==========================================================================
// SAVED FESTIVALS (JWT AUTHENTICATED)
// ==========================================================================

async function loadSavedFestivals() {
  const badgeEl = document.getElementById("saved-badge");
  const listEl = document.getElementById("saved-list");

  if (!state.token) {
    badgeEl.textContent = "0";
    listEl.innerHTML = `
      <div class="empty-state card">
        <div class="empty-icon">🔐</div>
        <h3>Sign In Required</h3>
        <p class="muted">Sign in with Google to bookmark and track your favorite festivals.</p>
      </div>
    `;
    return;
  }

  const { response, data } = await apiFetch("/api/saved-festivals");
  if (!response.ok) {
    listEl.innerHTML = `<div class="card empty-state"><p class="muted">${data.error || "Unable to load saved festivals."}</p></div>`;
    return;
  }

  state.savedFestivals = data.data || [];
  badgeEl.textContent = String(state.savedFestivals.length);

  if (!state.savedFestivals.length) {
    listEl.innerHTML = `
      <div class="empty-state card">
        <div class="empty-icon">⭐</div>
        <h3>No saved festivals yet</h3>
        <p class="muted">Explore festivals and click the star icon to save celebrations here.</p>
        <button class="btn btn-primary" onclick="setActiveSection('explore')">Explore Festivals</button>
      </div>
    `;
    return;
  }

  listEl.innerHTML = state.savedFestivals
    .map(
      (item) => `
    <article class="festival-card">
      <div>
        <div class="festival-card-top">
          <h3 class="festival-name">${item.festival_name}</h3>
          <button class="festival-save-btn saved" title="Remove from saved" onclick="deleteSavedFestival(${item.id})">★</button>
        </div>
        <div class="festival-tags">
          ${item.festival_date ? `<span class="tag tag-date">${formatDatePretty(item.festival_date)}</span>` : ""}
          ${item.religion ? `<span class="tag tag-religion">${item.religion}</span>` : ""}
        </div>
      </div>
      <div>
        <div class="festival-meta-footer">
          <span>Saved: ${formatDatePretty(item.created_at.split("T")[0])}</span>
        </div>
        <div class="festival-actions">
          <button class="btn btn-sm btn-primary" onclick="planFestivalDirect(${item.festival_id})">Plan with Weather 🌤️</button>
          <button class="btn btn-sm btn-danger" onclick="deleteSavedFestival(${item.id})">Remove</button>
        </div>
      </div>
    </article>
  `
    )
    .join("");
}

async function toggleSaveFestival(festivalId) {
  if (!state.token) {
    showToast("Please sign in with Google to save festivals.", true);
    return;
  }

  const existing = state.savedFestivals.find((s) => s.festival_id === festivalId);
  if (existing) {
    await deleteSavedFestival(existing.id);
  } else {
    const { response, data } = await apiFetch("/api/saved-festivals", {
      method: "POST",
      body: JSON.stringify({ festival_id: festivalId }),
    });

    if (!response.ok) {
      showToast(data.error || "Unable to save festival.", true);
      return;
    }

    showToast("Festival saved to your favorites!");
    await loadSavedFestivals();
    await loadDashboard();
    loadFestivals(); // re-render cards with active star
  }
}

async function deleteSavedFestival(savedId) {
  const { response, data } = await apiFetch(`/api/saved-festivals/${savedId}`, { method: "DELETE" });
  if (!response.ok) {
    showToast(data.error || "Unable to delete saved festival.", true);
    return;
  }
  showToast("Festival removed from saved.");
  await loadSavedFestivals();
  await loadDashboard();
  loadFestivals();
}

// ==========================================================================
// MY CELEBRATION PLANS (CRUD OPERATIONS)
// ==========================================================================

async function loadPlans() {
  const badgeEl = document.getElementById("plans-badge");
  const listEl = document.getElementById("plans-list");

  if (!state.token) {
    badgeEl.textContent = "0";
    listEl.innerHTML = `
      <div class="empty-state card">
        <div class="empty-icon">🔐</div>
        <h3>Sign In Required</h3>
        <p class="muted">Sign in with Google to create and manage personal celebration plans.</p>
      </div>
    `;
    return;
  }

  const { response, data } = await apiFetch("/api/plans");
  if (!response.ok) {
    listEl.innerHTML = `<div class="card empty-state"><p class="muted">${data.error || "Unable to load plans."}</p></div>`;
    return;
  }

  state.plans = data.data || [];
  badgeEl.textContent = String(state.plans.length);

  if (!state.plans.length) {
    listEl.innerHTML = `
      <div class="empty-state card">
        <div class="empty-icon">📅</div>
        <h3>No plans scheduled</h3>
        <p class="muted">Schedule a festival celebration above or from the Festival Planner.</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = state.plans
    .map(
      (p) => `
    <article class="card plan-card" id="plan-${p.id}">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
        <h3 style="font-family: var(--font-heading); font-size: 1.25rem; color: var(--royal-indigo); margin: 0;">${p.festival_name}</h3>
        <span class="tag tag-date">${formatDatePretty(p.celebration_date)}</span>
      </div>
      <p><strong>Destination:</strong> ${p.city}</p>
      <p style="color: var(--text-secondary); font-size: 0.9rem;"><strong>Notes:</strong> ${p.notes || "None added"}</p>
      <div class="festival-meta-footer">
        <span>Created: ${formatDatePretty(p.created_at.split("T")[0])}</span>
        <div style="display: flex; gap: 0.4rem;">
          <button class="btn btn-sm btn-secondary" onclick="openEditPlanModal(${p.id})">Edit (PUT/PATCH)</button>
          <button class="btn btn-sm btn-danger" onclick="deletePlan(${p.id})">Delete</button>
        </div>
      </div>
    </article>
  `
    )
    .join("");
}

async function createPlan() {
  if (!state.token) {
    showToast("Please sign in first.", true);
    return;
  }

  const festivalId = document.getElementById("plan-festival-select").value;
  const city = document.getElementById("plan-city").value;
  const celebrationDate = document.getElementById("plan-date").value;
  const notes = document.getElementById("plan-notes").value.trim();

  if (!festivalId) return showToast("Please select a festival.", true);
  if (!celebrationDate) return showToast("Please pick a celebration date.", true);

  const payload = {
    festival_id: Number(festivalId),
    city,
    celebration_date: celebrationDate,
    notes: notes || null,
  };

  const { response, data } = await apiFetch("/api/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    showToast(data.error || "Unable to create plan.", true);
    return;
  }

  showToast("Celebration plan created!");
  document.getElementById("plan-notes").value = "";
  await loadPlans();
  await loadDashboard();
}

function openEditPlanModal(planId) {
  const plan = state.plans.find((p) => p.id === planId);
  if (!plan) return;

  state.editingPlanId = planId;
  document.getElementById("edit-plan-id").value = plan.id;
  document.getElementById("edit-plan-festival-name").textContent = `${plan.festival_name} (ID: #${plan.festival_id})`;
  document.getElementById("edit-plan-city").value = plan.city;
  document.getElementById("edit-plan-date").value = plan.celebration_date;
  document.getElementById("edit-plan-notes").value = plan.notes || "";

  document.getElementById("plan-edit-modal").classList.add("open");
}

function closeEditPlanModal() {
  document.getElementById("plan-edit-modal").classList.remove("open");
  state.editingPlanId = null;
}

async function saveEditedPlan() {
  const planId = state.editingPlanId;
  if (!planId) return;

  const city = document.getElementById("edit-plan-city").value;
  const celebrationDate = document.getElementById("edit-plan-date").value;
  const notes = document.getElementById("edit-plan-notes").value.trim();

  const payload = {
    city,
    celebration_date: celebrationDate,
    notes: notes || null,
  };

  // Uses PATCH for partial updates
  const { response, data } = await apiFetch(`/api/plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    showToast(data.error || "Unable to update plan.", true);
    return;
  }

  showToast("Plan updated successfully!");
  closeEditPlanModal();
  await loadPlans();
  await loadDashboard();
}

async function deletePlan(planId) {
  if (!confirm("Are you sure you want to delete this celebration plan?")) return;

  const { response, data } = await apiFetch(`/api/plans/${planId}`, { method: "DELETE" });
  if (!response.ok) {
    showToast(data.error || "Unable to delete plan.", true);
    return;
  }

  showToast("Plan deleted.");
  await loadPlans();
  await loadDashboard();
}

// ==========================================================================
// REST API EXPLORER CONSOLE (LAB DEMONSTRATION)
// ==========================================================================

const API_PRESETS = {
  get_festivals: { method: "GET", endpoint: "/api/festivals", body: "", sendToken: true },
  get_festivals_upcoming: { method: "GET", endpoint: "/api/festivals?upcoming=true", body: "", sendToken: true },
  get_festival_id: { method: "GET", endpoint: "/api/festivals/1", body: "", sendToken: true },
  get_weather: { method: "GET", endpoint: "/api/weather?city=Mumbai", body: "", sendToken: true },
  get_mashup: { method: "GET", endpoint: "/api/mashup/festival-plan?festival_id=1&city=Mumbai", body: "", sendToken: true },
  get_me: { method: "GET", endpoint: "/api/me", body: "", sendToken: true },
  patch_me: { method: "PATCH", endpoint: "/api/me", body: JSON.stringify({ preferred_city: "Jaipur" }, null, 2), sendToken: true },
  get_saved: { method: "GET", endpoint: "/api/saved-festivals", body: "", sendToken: true },
  post_saved: { method: "POST", endpoint: "/api/saved-festivals", body: JSON.stringify({ festival_id: 1 }, null, 2), sendToken: true },
  get_plans: { method: "GET", endpoint: "/api/plans", body: "", sendToken: true },
  post_plans: {
    method: "POST",
    endpoint: "/api/plans",
    body: JSON.stringify({ festival_id: 1, city: "Delhi", celebration_date: "2026-11-08", notes: "Booking venue" }, null, 2),
    sendToken: true,
  },
  put_plan: {
    method: "PUT",
    endpoint: "/api/plans/1",
    body: JSON.stringify({ festival_id: 1, city: "Chennai", celebration_date: "2026-11-09", notes: "Replaced full plan" }, null, 2),
    sendToken: true,
  },
  patch_plan: {
    method: "PATCH",
    endpoint: "/api/plans/1",
    body: JSON.stringify({ notes: "Partially patched notes" }, null, 2),
    sendToken: true,
  },
  delete_plan: { method: "DELETE", endpoint: "/api/plans/1", body: "", sendToken: true },
  get_stats: { method: "GET", endpoint: "/api/dashboard/stats", body: "", sendToken: true },
  unauthorized_test: { method: "GET", endpoint: "/api/plans", body: "", sendToken: false },
};

function handleApiPresetChange() {
  const key = document.getElementById("api-preset-select").value;
  if (!key || !API_PRESETS[key]) return;

  const preset = API_PRESETS[key];
  document.getElementById("api-method").value = preset.method;
  document.getElementById("api-endpoint").value = preset.endpoint;
  document.getElementById("api-body").value = preset.body;
  document.getElementById("api-send-token").checked = preset.sendToken;
}

async function executeApiExplorerRequest() {
  const method = document.getElementById("api-method").value;
  const endpoint = document.getElementById("api-endpoint").value.trim();
  const sendToken = document.getElementById("api-send-token").checked;
  const bodyText = document.getElementById("api-body").value.trim();

  const statusBadge = document.getElementById("api-status-badge");
  const latencyBadge = document.getElementById("api-latency-badge");
  const outputEl = document.getElementById("api-output");

  statusBadge.className = "badge badge-subtle";
  statusBadge.textContent = "Executing...";
  outputEl.textContent = "Sending HTTP request...";

  let requestBody = undefined;
  if (["POST", "PUT", "PATCH"].includes(method)) {
    if (bodyText) {
      try {
        JSON.parse(bodyText);
        requestBody = bodyText;
      } catch (err) {
        statusBadge.className = "badge badge-4xx";
        statusBadge.textContent = "Client Error";
        outputEl.textContent = `Invalid JSON Body: ${err.message}`;
        return;
      }
    } else {
      requestBody = "{}";
    }
  }

  const { response, data, elapsed } = await apiFetch(endpoint, {
    method,
    body: requestBody,
    sendToken,
  });

  latencyBadge.textContent = `${elapsed} ms`;
  const status = response.status;
  if (status >= 200 && status < 300) {
    statusBadge.className = "badge badge-2xx";
  } else if (status >= 400 && status < 500) {
    statusBadge.className = "badge badge-4xx";
  } else {
    statusBadge.className = "badge badge-5xx";
  }
  statusBadge.textContent = `${status} ${response.statusText || ""}`;

  outputEl.textContent = JSON.stringify(data, null, 2);
}

// ==========================================================================
// EVENT BINDINGS & BOOTSTRAP
// ==========================================================================

function bindEventListeners() {
  // Navigation sidebar items
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => setActiveSection(btn.dataset.section));
  });

  // Mobile sidebar toggle
  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });

  // Festival search & reset
  document.getElementById("festival-search-btn").addEventListener("click", loadFestivals);
  document.getElementById("festival-reset-btn").addEventListener("click", resetFestivalFilters);
  document.getElementById("festival-search").addEventListener("keypress", (e) => {
    if (e.key === "Enter") loadFestivals();
  });

  // Festival detail modal close
  document.getElementById("modal-close-btn").addEventListener("click", closeFestivalDetailModal);
  document.getElementById("modal-close-action").addEventListener("click", closeFestivalDetailModal);

  // Planner quick buttons and run
  document.getElementById("planner-festival-select").addEventListener("change", triggerFestivalSelectionChange);
  document.getElementById("planner-use-festival-date").addEventListener("click", () => {
    const fId = document.getElementById("planner-festival-select").value;
    const f = state.festivals.find((item) => String(item.id) === String(fId));
    if (f && f.date) document.getElementById("planner-date").value = f.date;
  });
  document.getElementById("planner-use-today").addEventListener("click", () => {
    document.getElementById("planner-date").value = new Date().toISOString().split("T")[0];
  });
  document.getElementById("planner-run-btn").addEventListener("click", runPlannerMashup);

  // Weather button
  document.getElementById("weather-load-btn").addEventListener("click", loadWeather);

  // Plan creation
  document.getElementById("plan-create-btn").addEventListener("click", createPlan);

  // Plan edit modal
  document.getElementById("plan-edit-close-btn").addEventListener("click", closeEditPlanModal);
  document.getElementById("plan-edit-cancel-btn").addEventListener("click", closeEditPlanModal);
  document.getElementById("plan-edit-save-btn").addEventListener("click", saveEditedPlan);

  // API Explorer preset & execute
  document.getElementById("api-preset-select").addEventListener("change", handleApiPresetChange);
  document.getElementById("api-run-btn").addEventListener("click", executeApiExplorerRequest);

  // Preferences & logout
  document.getElementById("save-preference-btn").addEventListener("click", savePreferredCity);
  document.getElementById("logout-btn").addEventListener("click", logout);
}

// Global exposure for inline onclick handlers
window.setActiveSection = setActiveSection;
window.openFestivalDetailModal = openFestivalDetailModal;
window.planFestivalDirect = planFestivalDirect;
window.toggleSaveFestival = toggleSaveFestival;
window.deleteSavedFestival = deleteSavedFestival;
window.openEditPlanModal = openEditPlanModal;
window.deletePlan = deletePlan;
window.quickSavePlanFromMashup = quickSavePlanFromMashup;
window.resetFestivalFilters = resetFestivalFilters;

// Main bootloader
async function boot() {
  bindEventListeners();
  await loadConfig();
  await loadMe();
  await loadDashboard();
  await loadFestivals();
  await loadWeather();
  await loadSavedFestivals();
  await loadPlans();
  initGoogleSignIn();
}

document.addEventListener("DOMContentLoaded", boot);

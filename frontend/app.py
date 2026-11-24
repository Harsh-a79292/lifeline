"""
LifeLine — Real-Time Blood & Donor Network
Streamlit frontend — MVP
"""

import os
import streamlit as st
import requests as req_lib

# ─── CONFIG ──────────────────────────────────────────────────────────────────
# Reads from Streamlit secrets (production) or falls back to localhost (dev)
def get_api_url():
    try:
        return st.secrets["BACKEND_URL"].rstrip("/") + "/api"
    except Exception:
        return os.getenv("BACKEND_URL", "http://localhost:5000").rstrip("/") + "/api"

API_URL = get_api_url()

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
URGENCY_LABELS = {"normal": "🟢 Normal", "urgent": "🟡 Urgent", "critical": "🔴 Critical"}
STATUS_LABELS  = {"pending": "⏳ Pending", "accepted": "✅ Accepted", "fulfilled": "🎉 Fulfilled", "cancelled": "❌ Cancelled"}

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="LifeLine", page_icon="🩸", layout="wide")

# ─── STYLING ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
[data-testid="stAppViewContainer"] { background: #f8fafc; }
[data-testid="stSidebar"] { background: #1e293b; }
[data-testid="stSidebar"] * { color: #f1f5f9 !important; }

/* Typography */
h1 { color: #b91c1c !important; font-weight: 800 !important; letter-spacing: -0.5px; }
h2, h3 { color: #1e293b !important; font-weight: 700 !important; }

/* Primary buttons */
div.stButton > button[kind="primary"],
div.stFormSubmitButton > button {
    background: #b91c1c !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.25rem !important;
    transition: background 0.2s;
}
div.stButton > button[kind="primary"]:hover,
div.stFormSubmitButton > button:hover {
    background: #991b1b !important;
}

/* Secondary buttons */
div.stButton > button {
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* Cards */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    background: #fff;
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Badges */
.badge-critical { background:#fef2f2; color:#b91c1c; padding:2px 10px; border-radius:99px; font-size:0.8rem; font-weight:600; }
.badge-urgent   { background:#fefce8; color:#a16207; padding:2px 10px; border-radius:99px; font-size:0.8rem; font-weight:600; }
.badge-normal   { background:#f0fdf4; color:#15803d; padding:2px 10px; border-radius:99px; font-size:0.8rem; font-weight:600; }

/* Sidebar nav */
.sidebar-title { font-size:1.4rem; font-weight:800; color:#f87171 !important; margin-bottom:0; }
.sidebar-role  { font-size:0.85rem; color:#94a3b8 !important; margin-top:0; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for key, default in [("token", None), ("user", None), ("confirm_cancel", None), ("page", "dashboard")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ─── API HELPER ───────────────────────────────────────────────────────────────
def api(method, endpoint, data=None, timeout=15):
    headers = {"Content-Type": "application/json"}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        resp = req_lib.request(method, f"{API_URL}{endpoint}", json=data, headers=headers, timeout=timeout)
        try:
            result = resp.json()
        except ValueError:
            result = {"message": resp.text or "Unexpected server response"}
        # Token expired / invalid — force logout
        if resp.status_code == 401:
            st.session_state.token = None
            st.session_state.user = None
            st.warning("Your session has expired. Please log in again.")
            st.rerun()
        return resp.status_code, result
    except req_lib.exceptions.ConnectionError:
        return 0, {"message": "Cannot connect to backend. Please check the server."}
    except req_lib.exceptions.Timeout:
        return 0, {"message": "Request timed out. Please try again."}
    except req_lib.exceptions.RequestException as e:
        return 0, {"message": f"Request error: {e}"}


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.confirm_cancel = None
    st.session_state.page = "dashboard"
    st.rerun()


# ─── AUTH SCREENS ─────────────────────────────────────────────────────────────
def show_auth():
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown("<h1 style='text-align:center'>🩸 LifeLine</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#64748b; margin-top:-0.5rem;'>Real-Time Blood & Donor Network</p>", unsafe_allow_html=True)
        st.write("")

        login_tab, reg_tab = st.tabs(["🔑 Login", "📝 Register"])

        with login_tab:
            with st.form("login_form"):
                st.subheader("Welcome Back")
                email    = st.text_input("Email address", placeholder="you@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submitted:
                if not email or not password:
                    st.warning("Please enter both email and password.")
                else:
                    with st.spinner("Logging in…"):
                        status, result = api("POST", "/auth/login", {"email": email, "password": password})
                    if status == 200 and result.get("token"):
                        st.session_state.token = result["token"]
                        st.session_state.user  = result.get("user", {})
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result.get("message", "Login failed. Please try again."))

        with reg_tab:
            with st.form("register_form"):
                st.subheader("Create Account")
                name     = st.text_input("Full Name", placeholder="Ravi Sharma")
                reg_email = st.text_input("Email address", placeholder="you@example.com")
                phone    = st.text_input("Phone Number", placeholder="+91 98765 43210")
                reg_pass = st.text_input("Password (min 6 chars)", type="password")
                role     = st.selectbox("I am a", ["patient", "donor"])
                bg       = st.selectbox("Blood Group", BLOOD_GROUPS)
                city     = st.text_input("City", value="Indore")
                submitted_reg = st.form_submit_button("Create Account", use_container_width=True, type="primary")

            if submitted_reg:
                if not all([name, reg_email, phone, reg_pass, city]):
                    st.warning("Please fill in all fields.")
                elif len(reg_pass) < 6:
                    st.warning("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account…"):
                        status, result = api("POST", "/auth/register", {
                            "name": name, "email": reg_email, "phone": phone,
                            "password": reg_pass, "role": role, "bloodGroup": bg, "city": city,
                        })
                    if status in (200, 201) and result.get("token"):
                        st.session_state.token = result["token"]
                        st.session_state.user  = result.get("user", {})
                        st.success("Account created! Welcome to LifeLine.")
                        st.rerun()
                    else:
                        st.error(result.get("message", "Registration failed. Please try again."))


# ─── SHARED SIDEBAR ───────────────────────────────────────────────────────────
def show_sidebar(user, role):
    with st.sidebar:
        st.markdown(f"<p class='sidebar-title'>🩸 LifeLine</p>", unsafe_allow_html=True)
        st.markdown(f"<p class='sidebar-role'>{user.get('name', 'User')} · {role.capitalize()}</p>", unsafe_allow_html=True)
        st.divider()

        if role == "patient":
            if st.button("📋 My Requests", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
        elif role == "donor":
            if st.button("🔍 Find Requests", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
            if st.button("📂 My Accepted", use_container_width=True):
                st.session_state.page = "my_accepted"
                st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()


# ─── PATIENT DASHBOARD ────────────────────────────────────────────────────────
def patient_dashboard(user):
    st.title("🏥 Patient Dashboard")
    st.caption("Create blood requests and track your status.")
    st.divider()

    # ── Create Request Form ──
    with st.expander("➕ Create New Blood Request", expanded=False):
        with st.form("blood_request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                bg      = st.selectbox("Required Blood Group", BLOOD_GROUPS)
                units   = st.number_input("Units Required", min_value=1, max_value=10, value=1, step=1)
                urgency = st.selectbox("Urgency Level", list(URGENCY_LABELS.keys()),
                                       format_func=lambda x: URGENCY_LABELS[x])
            with c2:
                hospital = st.text_input("Hospital Name", placeholder="City Care Hospital")
                city_val = st.text_input("City", value=user.get("city", "Indore"))
                phone_val = st.text_input("Contact Phone", placeholder="+91 …")

            submitted = st.form_submit_button("🩸 Submit Blood Request", use_container_width=True, type="primary")

        if submitted:
            if not all([hospital, city_val, phone_val]):
                st.warning("Please complete all fields.")
            else:
                with st.spinner("Submitting request…"):
                    status, result = api("POST", "/requests", {
                        "bloodGroup": bg, "units": int(units),
                        "hospitalName": hospital, "city": city_val,
                        "contactPhone": phone_val, "urgency": urgency,
                    })
                if status in (200, 201):
                    st.success("✅ Blood request created successfully!")
                    st.rerun()
                else:
                    st.error(result.get("message", "Failed to create request."))

    st.subheader("📋 My Blood Requests")
    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", key="patient_refresh"):
            st.rerun()

    with st.spinner("Loading your requests…"):
        status, result = api("GET", "/requests/my")

    if status != 200:
        st.error(result.get("message", "Unable to load your requests."))
        return

    requests_list = result.get("requests", [])
    if not requests_list:
        st.info("You haven't created any blood requests yet.")
        return

    for r in requests_list:
        req_status = r.get("status", "pending")
        urgency_key = r.get("urgency", "normal")

        with st.container(border=True):
            top_left, top_right = st.columns([3, 1])
            with top_left:
                st.markdown(
                    f"### 🩸 {r.get('bloodGroup')} — {r.get('units')} unit(s) &nbsp;"
                    f"<span class='badge-{urgency_key}'>{URGENCY_LABELS[urgency_key]}</span>",
                    unsafe_allow_html=True
                )
            with top_right:
                st.markdown(
                    f"<div style='text-align:right; padding-top:8px'>"
                    f"{STATUS_LABELS.get(req_status, req_status)}</div>",
                    unsafe_allow_html=True
                )

            info_col, action_col = st.columns([3, 1])
            with info_col:
                st.write(f"🏥 **Hospital:** {r.get('hospitalName')}")
                st.write(f"📍 **City:** {r.get('city')}")
                st.write(f"📞 **Your Contact:** {r.get('contactPhone')}")

                # Show accepted donor info (safe fields only)
                donor = r.get("acceptedDonor")
                if donor:
                    st.info(
                        f"✅ **Accepted by:** {donor.get('name', 'A donor')} "
                        f"({donor.get('bloodGroup', '—')}, {donor.get('city', '—')})"
                    )

            with action_col:
                rid = r.get("_id")
                if req_status in ("pending", "accepted"):
                    # Confirmation flow for cancel
                    if st.session_state.confirm_cancel == rid:
                        st.warning("Are you sure?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("Yes, cancel", key=f"confirm_yes_{rid}", type="primary"):
                                with st.spinner("Cancelling…"):
                                    cs, cr = api("PATCH", f"/requests/{rid}/cancel")
                                st.session_state.confirm_cancel = None
                                if cs == 200:
                                    st.success("Request cancelled.")
                                    st.rerun()
                                else:
                                    st.error(cr.get("message", "Could not cancel."))
                        with c2:
                            if st.button("No", key=f"confirm_no_{rid}"):
                                st.session_state.confirm_cancel = None
                                st.rerun()
                    else:
                        if st.button("❌ Cancel", key=f"cancel_{rid}"):
                            st.session_state.confirm_cancel = rid
                            st.rerun()


# ─── DONOR: FIND PENDING REQUESTS ────────────────────────────────────────────
def donor_find_requests():
    st.title("🔍 Find Blood Requests")
    st.caption("View pending blood requests in the network and accept one.")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", key="donor_refresh"):
            st.rerun()

    with st.spinner("Loading requests…"):
        status, result = api("GET", "/requests")

    if status != 200:
        st.error(result.get("message", "Unable to load requests."))
        return

    requests_list = result.get("requests", [])
    if not requests_list:
        st.info("No pending blood requests at this time. Check back soon.")
        return

    for r in requests_list:
        urgency_key = r.get("urgency", "normal")
        with st.container(border=True):
            top_left, top_right = st.columns([3, 1])
            with top_left:
                st.markdown(
                    f"### 🩸 {r.get('bloodGroup')} — {r.get('units')} unit(s) &nbsp;"
                    f"<span class='badge-{urgency_key}'>{URGENCY_LABELS[urgency_key]}</span>",
                    unsafe_allow_html=True
                )
            with top_right:
                st.markdown(
                    "<div style='text-align:right; padding-top:8px'>⏳ Pending</div>",
                    unsafe_allow_html=True
                )

            info_col, btn_col = st.columns([3, 1])
            with info_col:
                st.write(f"🏥 **Hospital:** {r.get('hospitalName')}")
                st.write(f"📍 **City:** {r.get('city')}")
                # contactPhone intentionally not shown to donors in pending feed

            with btn_col:
                rid = r.get("_id")
                if st.button("✅ Accept", key=f"accept_{rid}", type="primary"):
                    with st.spinner("Accepting request…"):
                        s, res = api("PATCH", f"/requests/{rid}/accept")
                    if s == 200:
                        st.success("Request accepted! Check 'My Accepted' for details.")
                        st.rerun()
                    else:
                        st.error(res.get("message", "Could not accept request."))


# ─── DONOR: MY ACCEPTED REQUESTS ─────────────────────────────────────────────
def donor_my_accepted():
    st.title("📂 My Accepted Requests")
    st.caption("Blood requests you have accepted or fulfilled.")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", key="accepted_refresh"):
            st.rerun()

    with st.spinner("Loading…"):
        status, result = api("GET", "/requests/my-accepted")

    if status != 200:
        st.error(result.get("message", "Unable to load accepted requests."))
        return

    requests_list = result.get("requests", [])
    if not requests_list:
        st.info("You haven't accepted any blood requests yet.")
        return

    for r in requests_list:
        req_status  = r.get("status", "accepted")
        urgency_key = r.get("urgency", "normal")

        with st.container(border=True):
            top_left, top_right = st.columns([3, 1])
            with top_left:
                st.markdown(
                    f"### 🩸 {r.get('bloodGroup')} — {r.get('units')} unit(s) &nbsp;"
                    f"<span class='badge-{urgency_key}'>{URGENCY_LABELS[urgency_key]}</span>",
                    unsafe_allow_html=True
                )
            with top_right:
                st.markdown(
                    f"<div style='text-align:right; padding-top:8px'>"
                    f"{STATUS_LABELS.get(req_status, req_status)}</div>",
                    unsafe_allow_html=True
                )

            info_col, btn_col = st.columns([3, 1])
            with info_col:
                st.write(f"🏥 **Hospital:** {r.get('hospitalName')}")
                st.write(f"📍 **City:** {r.get('city')}")

            with btn_col:
                rid = r.get("_id")
                if req_status == "accepted":
                    if st.button("🎉 Mark Fulfilled", key=f"fulfill_{rid}", type="primary"):
                        with st.spinner("Marking as fulfilled…"):
                            s, res = api("PATCH", f"/requests/{rid}/fulfill")
                        if s == 200:
                            st.success("Marked as fulfilled. Thank you! 🩸")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Could not mark as fulfilled."))
                else:
                    st.success("Fulfilled ✓")


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.token:
        show_auth()
        return

    user = st.session_state.user or {}
    role = user.get("role", "patient")

    show_sidebar(user, role)

    if role == "patient":
        patient_dashboard(user)

    elif role == "donor":
        page = st.session_state.get("page", "dashboard")
        if page == "my_accepted":
            donor_my_accepted()
        else:
            donor_find_requests()

    else:
        st.error("Unsupported account role. Please contact support.")


main()

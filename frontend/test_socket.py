
import streamlit as st
import requests

API_URL = "http://localhost:5000/api"

st.set_page_config(
    page_title="LifeLine | Blood Network",
    page_icon="🩸",
    layout="wide"
)

# ---------- STYLING ----------
st.markdown("""
<style>
    .stApp {
        background-color: #f5f7fb;
    }
    h1, h2, h3 {
        color: #172554;
    }
    div.stButton > button {
        background-color: #0f766e;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
    }
    div.stButton > button:hover {
        background-color: #115e59;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ---------- SESSION ----------
if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None


# ---------- API HELPERS ----------
def api_request(method, endpoint, data=None):
    headers = {}

    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"

    try:
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            json=data,
            headers=headers,
            timeout=15
        )

        try:
            result = response.json()
        except ValueError:
            result = {"message": response.text}

        return response.status_code, result

    except requests.exceptions.ConnectionError:
        st.error("Backend server is not running.")
        return 0, {}

    except requests.exceptions.RequestException as error:
        st.error(f"Request failed: {error}")
        return 0, {}


def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.rerun()


# ---------- HEADER ----------
st.title("🩸 LifeLine")
st.caption("Real-Time Blood & Donor Network")
st.divider()


# ---------- AUTHENTICATION ----------
if not st.session_state.token:

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        st.subheader("Welcome Back")

        email = st.text_input("Email", key="login_email")
        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login", use_container_width=True):

            if not email or not password:
                st.warning("Please enter email and password.")

            else:
                status, result = api_request(
                    "POST",
                    "/auth/login",
                    {
                        "email": email,
                        "password": password
                    }
                )

                if status == 200 and result.get("token"):
                    st.session_state.token = result["token"]

                    # Backend login response should contain user details.
                    st.session_state.user = result.get("user", {})

                    st.success("Login successful!")
                    st.rerun()

                else:
                    st.error(result.get("message", "Login failed."))

    with register_tab:
        st.subheader("Create Your Account")

        name = st.text_input("Full Name", key="reg_name")
        reg_email = st.text_input("Email", key="reg_email")
        phone = st.text_input("Phone Number", key="reg_phone")

        reg_password = st.text_input(
            "Password",
            type="password",
            key="reg_password"
        )

        role = st.selectbox(
            "Register As",
            ["patient", "donor"]
        )

        blood_group = st.selectbox(
            "Blood Group",
            ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        )

        city = st.text_input("City", value="Indore")

        if st.button("Create Account", use_container_width=True):

            if not all([name, reg_email, phone, reg_password, city]):
                st.warning("Please fill all fields.")

            else:
                status, result = api_request(
                    "POST",
                    "/auth/register",
                    {
                        "name": name,
                        "email": reg_email,
                        "phone": phone,
                        "password": reg_password,
                        "role": role,
                        "bloodGroup": blood_group,
                        "city": city
                    }
                )

                if status in [200, 201] and result.get("token"):
                    st.session_state.token = result["token"]
                    st.session_state.user = result.get("user", {})
                    st.success("Registration successful!")
                    st.rerun()

                else:
                    st.error(
                        result.get("message", "Registration failed.")
                    )


# ---------- DASHBOARD ----------
else:

    user = st.session_state.user or {}
    role = user.get("role", "patient")

    with st.sidebar:
        st.title("LifeLine")
        st.write(f"Welcome, {user.get('name', 'User')}")
        st.write(f"Role: **{role.capitalize()}**")
        st.divider()

        if st.button("Logout", use_container_width=True):
            logout()

    if role == "patient":

        st.header("Patient Dashboard")
        st.write("Create a blood request and track your requests.")

        with st.form("blood_request_form"):

            blood_group = st.selectbox(
                "Required Blood Group",
                ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            )

            units = st.number_input(
                "Units Required",
                min_value=1,
                max_value=10,
                value=1
            )

            hospital = st.text_input("Hospital Name")
            city = st.text_input("City", value=user.get("city", "Indore"))
            phone = st.text_input("Contact Phone")

            urgency = st.selectbox(
                "Urgency",
                ["normal", "urgent", "critical"]
            )

            submitted = st.form_submit_button(
                "Submit Blood Request",
                use_container_width=True
            )

            if submitted:

                if not all([hospital, city, phone]):
                    st.warning("Please complete all fields.")

                else:
                    status, result = api_request(
                        "POST",
                        "/requests",
                        {
                            "bloodGroup": blood_group,
                            "units": int(units),
                            "hospitalName": hospital,
                            "city": city,
                            "contactPhone": phone,
                            "urgency": urgency
                        }
                    )

                    if status in [200, 201]:
                        st.success("Blood request created successfully!")
                    else:
                        st.error(
                            result.get("message", "Could not create request.")
                        )

        st.divider()
        st.subheader("My Blood Requests")

        status, result = api_request("GET", "/requests/my")

        if status == 200:
            requests_list = result.get("requests", [])

            if requests_list:
                for request in requests_list:
                    with st.container(border=True):
                        st.write(
                            f"### {request.get('bloodGroup', 'N/A')} "
                            f"— {request.get('units', 0)} units"
                        )
                        st.write(
                            f"Hospital: {request.get('hospitalName', 'N/A')}"
                        )
                        st.write(
                            f"City: {request.get('city', 'N/A')}"
                        )
                        st.write(
                            f"Urgency: {request.get('urgency', 'normal').upper()}"
                        )
                        st.write(
                            f"Status: {request.get('status', 'pending').upper()}"
                        )
            else:
                st.info("You haven't created any requests yet.")

        else:
            st.error(result.get("message", "Unable to load your requests."))

    elif role == "donor":

        st.header("Donor Dashboard")
        st.write("Find pending blood requests in the network.")

        if st.button("Refresh Requests"):
            st.rerun()

        status, result = api_request("GET", "/requests")

        if status == 200:

            requests_list = result.get("requests", [])

            if requests_list:

                for request in requests_list:
                    with st.container(border=True):

                        st.subheader(
                            f"🩸 {request.get('bloodGroup', 'N/A')} "
                            f"— {request.get('units', 0)} units"
                        )

                        st.write(
                            f"Hospital: {request.get('hospitalName', 'N/A')}"
                        )
                        st.write(f"City: {request.get('city', 'N/A')}")
                        st.write(
                            f"Urgency: {request.get('urgency', 'normal').upper()}"
                        )

                        st.info(
                            "Contact the hospital through its verified "
                            "official channel. Do not rely on this prototype "
                            "for confirmed blood availability."
                        )

            else:
                st.info("No pending blood requests found.")

        else:
            st.error(result.get("message", "Unable to load requests."))

    else:
        st.error("Unsupported account role.")

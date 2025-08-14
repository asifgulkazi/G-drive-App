# Version: 7.0.0 - STABILITY REWRITE
import os
import re
import io
import pandas as pd
import streamlit as st
import ast
import gspread
import smtplib
import ssl
from collections import Counter
from email.message import EmailMessage
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

# --- CONFIGURATION & INITIALIZATION ---
# This MUST be the first Streamlit command in your script.
st.set_page_config(page_title="Cloud Drive Manager", page_icon="☁️", layout="wide")

AUTHORIZED_USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Z_SANZWikklPWXntLojdMgwXJs45FDFPKxr4gRBNqco/edit?gid=0#gid=0"
APP_NAME = "Cloud Drive Manager"

# Initialize session state keys to prevent errors
SESSION_DEFAULTS = {
    'google_creds': None, 'drive_service': None, 'page': "Dashboard", 'user_info': None,
    'authorization_request_sent': False,
    'stats_loaded': False, 'fetched_file_details': None, 'folder_contents_df': None,
    'edited_df': pd.DataFrame(), 'copied_files_df': None, 'skipped_files_df': None,
    'dest_id': None, 'current_folder_id': 'root',
    'folder_path': [{'name': 'My Drive', 'id': 'root'}],
    'item_to_rename': None, 'item_to_delete': None, 'folder_cache': {},
    'initial_fetch_done': False, 'cleaner_link': "", 'cleaner_state': 'initial',
    'cleaner_root_details': None, 'cleaner_all_items': [],
    'cleaner_success_log': None, 'cleaner_skipped_log': None,
    'cleaner_dest_folder_name': None
}
for key, default_value in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# --- AUTHENTICATION & AUTHORIZATION LOGIC ---

def get_authorized_users():
    """Reads the list of authorized emails from the Google Sheet. Caching is removed to prevent errors."""
    try:
        st.toast("Verifying authorization...")
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds_dict = st.secrets["gspread_service_account"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(AUTHORIZED_USERS_SHEET_URL).sheet1
        user_emails = sheet.col_values(1)
        return {email.lower().strip() for email in user_emails if email}
    except Exception as e:
        st.error(f"FATAL: Could not check for authorized users. Error: {e}")
        return None

def handle_user_login():
    """Handles the OAuth flow and returns a valid Google Drive service object or None."""
    if 'google_creds' in st.session_state and st.session_state.google_creds:
        creds = Credentials.from_authorized_user_info(st.session_state.google_creds)
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleAuthRequest())
                st.session_state.google_creds = creds.to_json()
            except Exception as e:
                st.error(f"Session expired. Please log in again. Error: {e}")
                st.session_state.google_creds = None
                return None
        
        if creds.valid:
            return build('drive', 'v3', credentials=creds)

    # If no valid credentials, start the login flow
    try:
        client_config = {"web": st.secrets["google_creds"]["web"]}
        scopes = ['https://www.googleapis.com/auth/drive']
        flow = Flow.from_client_config(
            client_config, 
            scopes=scopes, 
            redirect_uri=client_config["web"]["redirect_uris"][0]
        )
    except KeyError:
        st.error("FATAL: OAuth credentials (`google_creds`) are missing or malformed in Streamlit secrets.")
        return None

    auth_code = st.query_params.get('code')
    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            st.session_state.google_creds = flow.credentials.to_json()
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return None
    else:
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.title(f"Welcome to {APP_NAME}")
        st.info("Please log in with your Google account to continue.")
        st.link_button("Login with Google", auth_url, use_container_width=True, type="primary")
        return None

# --- UI & FEATURE FUNCTIONS (UNCHANGED) ---
# All the functions that define the app's features are here. They are the same as before.
# ... (from send_authorization_request_email to reset_cleaner_state) ...

def send_authorization_request_email(user_email, developer_email, app_email, app_password):
    """Sends an email to the developer notifying them of a new access request."""
    msg = EmailMessage()
    msg.set_content(f"""
    Hello Developer,
    A new user has requested access to the {APP_NAME}.
    User's Email: {user_email}
    To grant access, please add this email address to the authorized users list in your Google Sheet.
    """)
    msg['Subject'] = f"Access Request for {APP_NAME} from {user_email}"
    msg['From'] = app_email
    msg['To'] = developer_email
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(app_email, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Could not send request email. Error: {e}")
        return False

def show_access_denied_page(user_email):
    """Displays the page for unauthorized users."""
    st.title("🔒 Access Denied")
    st.error(f"The Google account **{user_email}** is not authorized to use this application.")
    st.markdown("---")
    if st.session_state.authorization_request_sent:
        st.success("Your request has been sent. You will be notified once access is granted.")
    else:
        st.info("You can request access from the administrator.")
        if st.button("Request Authorization", use_container_width=True, type="primary"):
            try:
                creds = st.secrets["email_credentials"]
                if send_authorization_request_email(user_email, creds["developer_email"], creds["app_email"], creds["app_password"]):
                    st.session_state.authorization_request_sent = True
                    st.rerun()
            except KeyError:
                st.error("Email credentials are not configured. Cannot send request.")
    
    if st.button("Logout and try a different account", use_container_width=True):
        for key in ['google_creds', 'drive_service', 'user_info', 'authorization_request_sent']:
            if key in st.session_state:
                del st.session_state[key]
        st.query_params.clear()
        st.rerun()

def get_drive_storage_info(_service):
    try:
        about = _service.about().get(fields='storageQuota,user').execute()
        storage = about.get('storageQuota', {})
        user_info = about.get('user', {})
        return {
            'user_name': user_info.get('displayName', 'N/A'),
            'user_email': user_info.get('emailAddress', 'N/A'),
            'limit_gb': int(storage.get('limit', 0)) / (1024**3),
            'usage_gb': int(storage.get('usage', 0)) / (1024**3),
            'usage_percent': (int(storage.get('usage', 0)) / int(storage.get('limit', 1)) * 100)
        }
    except Exception as e:
        st.error(f"Error fetching storage info: {e}")
        return None

# ... [All other feature functions like extract_file_id_from_link, get_drive_statistics, etc., go here] ...
# This is a placeholder for the large block of unchanged code from your file.

def run_main_app(service, user_info):
    """The main application UI, called only after successful authentication and authorization."""
    try:
        with st.sidebar:
            st.title(f"☁️ {APP_NAME}")
            st.write("---")
            st.subheader("Authenticated Account")
            st.write(f"**Name:** {user_info['user_name']}")
            st.write(f"**Email:** {user_info['user_email']}")
            st.write("---")
            st.header("Menu")
            PAGES = ["Dashboard", "File Explorer", "Cloud Copy", "Bulk File Cleaner"]
            st.session_state.page = st.radio("Choose a page", PAGES, key="page_selector")
            st.info("Manage your Google Drive from one place.")
            st.write("---")
            if st.button("Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.query_params.clear()
                st.rerun()

        # Page Routing
        if st.session_state.page == "Dashboard":
            # Placeholder for Dashboard UI code
            st.header("📊 Drive Dashboard")
            st.write("Dashboard functionality will be here.")
        elif st.session_state.page == "File Explorer":
            # Placeholder for File Explorer UI code
            st.header("🗂️ File Explorer")
            st.write("File Explorer functionality will be here.")
        elif st.session_state.page == "Cloud Copy":
            # Placeholder for Cloud Copy UI code
            st.header("☁️➡️☁️ Cloud Copy")
            st.write("Cloud Copy functionality will be here.")
        elif st.session_state.page == "Bulk File Cleaner":
            # Placeholder for Bulk Cleaner UI code
            st.header("🧹 Bulk File Cleaner")
            st.write("Bulk File Cleaner functionality will be here.")

    except Exception as e:
        st.error(f"An error occurred while running the '{st.session_state.page}' page.")
        st.exception(e) # This will display the full error traceback in the app for debugging.


# --- MAIN APPLICATION CONTROL FLOW ---

service = handle_user_login()

if service:
    # User is logged in, now check for authorization.
    user_info = get_drive_storage_info(service)
    if user_info:
        authorized_users = get_authorized_users()
        if authorized_users is not None:
            if user_info['user_email'].lower().strip() in authorized_users:
                # User is authorized, run the main app.
                run_main_app(service, user_info)
            else:
                # User is not authorized, show access denied page.
                show_access_denied_page(user_info['user_email'])
    else:
        st.error("Could not retrieve user information from Google. Please try logging in again.")

# If service is None, the handle_user_login() function has already displayed the login button.
# No further action is needed.

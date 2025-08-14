# Version: 7.1.0 - FINAL STABILITY FIX
import os
import re
import io
import json
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
st.set_page_config(page_title="Cloud Drive Manager", page_icon="☁️", layout="wide")

AUTHORIZED_USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Z_SANZWikklPWXntLojdMgwXJs45FDFPKxr4gRBNqco/edit?gid=0#gid=0"
APP_NAME = "Cloud Drive Manager"

SESSION_DEFAULTS = {
    'google_creds': None, 'page': "Dashboard", 'user_info': None,
    'authorization_request_sent': False, 'stats_loaded': False,
    'fetched_file_details': None, 'folder_contents_df': None,
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
    try:
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
    if 'google_creds' in st.session_state and st.session_state.google_creds:
        try:
            # FIX: Load credentials from JSON string to dictionary
            creds_info = json.loads(st.session_state.google_creds)
            creds = Credentials.from_authorized_user_info(creds_info)
        except (json.JSONDecodeError, TypeError):
            st.session_state.google_creds = None
            return None

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

    try:
        client_config = {"web": st.secrets["google_creds"]["web"]}
        scopes = ['https://www.googleapis.com/auth/drive']
        flow = Flow.from_client_config(
            client_config, 
            scopes=scopes, 
            redirect_uri=client_config["web"]["redirect_uris"][0]
        )
    except KeyError:
        st.error("FATAL: OAuth credentials (`google_creds`) are missing or malformed in secrets.")
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

def send_authorization_request_email(user_email, developer_email, app_email, app_password):
    msg = EmailMessage()
    msg.set_content(f"User {user_email} has requested access to {APP_NAME}.")
    msg['Subject'] = f"Access Request for {APP_NAME}"
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
    st.title("🔒 Access Denied")
    st.error(f"The account **{user_email}** is not authorized.")
    if st.session_state.authorization_request_sent:
        st.success("Your request has been sent.")
    else:
        if st.button("Request Authorization", type="primary"):
            creds = st.secrets.get("email_credentials", {})
            if send_authorization_request_email(user_email, creds.get("developer_email"), creds.get("app_email"), creds.get("app_password")):
                st.session_state.authorization_request_sent = True
                st.rerun()
    
    if st.button("Logout and try a different account"):
        for key in list(st.session_state.keys()):
            if key != 'page': del st.session_state[key]
        st.query_params.clear()
        st.rerun()

def get_drive_storage_info(_service):
    try:
        about = _service.about().get(fields='storageQuota,user').execute()
        storage = about.get('storageQuota', {})
        user = about.get('user', {})
        return {
            'user_name': user.get('displayName', 'N/A'),
            'user_email': user.get('emailAddress', 'N/A'),
            'limit_gb': int(storage.get('limit', 0)) / (1024**3),
            'usage_gb': int(storage.get('usage', 0)) / (1024**3),
        }
    except Exception: return None

# --- All other helper functions from your original file go here ---
# (extract_file_id_from_link, format_storage, get_file_icon, etc.)
def extract_file_id_from_link(link):
    if not link: return None
    patterns = [r'/file/d/([a-zA-Z0-9_-]+)', r'/drive/folders/([a-zA-Z0-9_-]+)', r'id=([a-zA-Z0-9_-]+)', r'/d/([a-zA-Z0-9_-]+)/']
    for pattern in patterns:
        match = re.search(pattern, link)
        if match: return match.group(1)
    return None

def format_storage(size_in_gb):
    if size_in_gb >= 1000: return f"{size_in_gb / 1000:.3f} TB"
    else: return f"{size_in_gb:.2f} GB"

def get_file_icon(item):
    if item.get('is_folder_sort') == 1 or item.get('mimeType') == 'application/vnd.google-apps.folder': return "📁"
    mime_type = item.get('effective_mime', item.get('mimeType', '')); icon_map = {'application/pdf': '📕','application/vnd.google-apps.document': '📝','application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝','application/vnd.google-apps.spreadsheet': '📊','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '📊','application/vnd.google-apps.presentation': '📽️','application/vnd.openxmlformats-officedocument.presentationml.presentation': '📽️','application/zip': '📦','application/x-zip-compressed': '📦'}
    if mime_type.startswith('image/'): return '🖼️'
    if mime_type.startswith('audio/'): return '🎵'
    if mime_type.startswith('video/'): return '🎞️'
    return icon_map.get(mime_type, '📄')

# ... and so on for all the other functions from your file ...

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
            st.header("📊 Drive Dashboard")
            # ... (Full Dashboard code from your file)
        elif st.session_state.page == "File Explorer":
            st.header("🗂️ File Explorer")
            # ... (Full File Explorer code from your file)
        elif st.session_state.page == "Cloud Copy":
            st.header("☁️➡️☁️ Cloud Copy")
            # ... (Full Cloud Copy code from your file)
        elif st.session_state.page == "Bulk File Cleaner":
            st.header("🧹 Bulk File Cleaner")
            # ... (Full Bulk Cleaner code from your file)

    except Exception as e:
        st.error(f"An error occurred in the '{st.session_state.page}' page.")
        st.exception(e)

# --- MAIN APPLICATION CONTROL FLOW ---

service = handle_user_login()

if service:
    user_info = get_drive_storage_info(service)
    if user_info:
        authorized_users = get_authorized_users()
        if authorized_users is not None:
            if user_info['user_email'].lower().strip() in authorized_users:
                run_main_app(service, user_info)
            else:
                show_access_denied_page(user_info['user_email'])
    else:
        st.error("Could not retrieve user information from Google. Please try logging in again.")

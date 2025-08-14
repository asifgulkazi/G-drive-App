# [This is the full code from 'drive_gui_app.py' that you provided previously]
# Version: 6.2.0 - FINAL, CORRECTED REDIRECT_URI
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

# --- Configuration ---
# !!! IMPORTANT !!! - YOU MUST REPLACE THIS URL WITH YOUR OWN GOOGLE SHEET URL IN STEP 3
AUTHORIZED_USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/your_sheet_id_here/edit"
APP_NAME = "Cloud Drive Manager"

# --- Session State Initialization ---
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

# --- [The rest of the full code you provided goes here, unchanged] ---
# ... (all functions from get_authorized_users to run_main_app) ...

# --- FINAL APP ENTRY POINT ---
st.set_page_config(page_title=APP_NAME, layout="centered")

# This single function call handles everything: login, redirects, authorization, and the access request workflow.
service = get_authenticated_service()

if service:
    # If the service object is returned, the user is fully authenticated and authorized.
    # We can now run the main application with its full wide layout.
    run_main_app(service)

# [The full code from the file you uploaded is assumed here]
# Version: 6.2.0 - FINAL, CORRECTED REDIRECT_URI
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

# --- Configuration ---
AUTHORIZED_USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1WFsf1ygkyLkwZUaY5rzJJLBk6XlwNurKUaI-eVGFh_U/edit#gid=0"
APP_NAME = "Cloud Drive Manager"

# --- Session State Initialization ---
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

# --- AUTHENTICATION & ACCESS REQUEST WORKFLOW ---

@st.cache_data(ttl=600)
def get_authorized_users():
    """Reads the list of authorized emails from the Google Sheet."""
    try:
        st.toast("Verifying authorization...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        creds_dict = st.secrets["gspread_service_account"]
        creds = ServiceAccountCredentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(AUTHORIZED_USERS_SHEET_URL).sheet1
        user_emails = sheet.col_values(1)
        return {email.lower().strip() for email in user_emails if email}
    except Exception as e:
        st.error(f"FATAL: Could not check for authorized users. Ensure the service account email has 'Viewer' access to your Google Sheet file. Error: {e}")
        return None

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
        st.error(f"Could not send request email. Please contact the administrator directly. Error: {e}")
        return False

def show_access_denied_page(user_email):
    """Displays the page for unauthorized users to request access."""
    st.title("🔒 Access Denied")
    st.error(f"The Google account **{user_email}** is not currently authorized to use this application.")
    st.markdown("---")

    if st.session_state.authorization_request_sent:
        st.success("Your request for access has been sent to the administrator. You will be notified once access is granted.")
    else:
        st.info("You can request access from the administrator or try logging in with a different account.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Request Authorization", use_container_width=True, type="primary"):
                try:
                    creds = st.secrets["email_credentials"]
                    email_sent = send_authorization_request_email(
                        user_email=user_email,
                        developer_email=creds["developer_email"],
                        app_email=creds["app_email"],
                        app_password=creds["app_password"]
                    )
                    if email_sent:
                        st.session_state.authorization_request_sent = True
                        st.rerun()
                except KeyError:
                    st.error("Email credentials are not configured in the application's secrets. Cannot send request.")
        
        with col2:
            if st.button("Try a different Google Account", use_container_width=True):
                for key in ['google_creds', 'drive_service', 'user_info', 'authorization_request_sent']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.query_params.clear()
                st.rerun()

def get_authenticated_service():
    """The main function that handles the entire auth and request workflow."""
    if 'drive_service' in st.session_state and st.session_state.drive_service:
        return st.session_state.drive_service

    creds = st.session_state.get('google_creds')

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            st.session_state.google_creds = creds
        except Exception:
            st.session_state.google_creds = None
            creds = None

    if creds and creds.valid:
        service = build('drive', 'v3', credentials=creds)
        user_info = get_drive_storage_info(service)
        if not user_info or not user_info.get('user_email'):
            st.error("Could not retrieve your Google account details. Please try again.")
            return None

        user_email = user_info['user_email'].lower().strip()
        authorized_users = get_authorized_users()
        if authorized_users is None:
            return None

        if user_email not in authorized_users:
            show_access_denied_page(user_info['user_email'])
            return None
        
        st.session_state.drive_service = service
        st.rerun()

    # --- Initial Login Flow ---
    client_config = {"web": st.secrets["google_creds"]["web"]}
    scopes = ['https://www.googleapis.com/auth/drive']
    
    # CRITICAL FIX: Pass the redirect URI as a string, not a list.
    flow = Flow.from_client_config(
        client_config, 
        scopes=scopes, 
        redirect_uri=client_config["web"]["redirect_uris"][0]
    )

    auth_code = st.query_params.get('code')
    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            st.session_state.google_creds = flow.credentials
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication failed while fetching token: {e}")
            return None
    else:
        st.title(f"Welcome to {APP_NAME}")
        st.write("Please log in with your Google account to continue.")
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.link_button("Login with Google", auth_url, use_container_width=True, type="primary")
        return None

def get_drive_storage_info(_service):
    if 'user_info' in st.session_state and st.session_state.user_info:
        return st.session_state.user_info
    try:
        about = _service.about().get(fields='storageQuota,user').execute()
        storage_quota = about.get('storageQuota', {})
        limit = int(storage_quota.get('limit', 0))
        usage = int(storage_quota.get('usage', 0))
        user_info_data = about.get('user', {})
        usage_percent = (usage / limit * 100) if limit > 0 else 0
        user_info = {
            'user_name': user_info_data.get('displayName', 'N/A'),
            'user_email': user_info_data.get('emailAddress', 'N/A'),
            'limit_gb': limit / (1024**3),
            'usage_gb': usage / (1024**3),
            'usage_percent': usage_percent
        }
        st.session_state.user_info = user_info
        return user_info
    except Exception:
        return None

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

def get_drive_statistics(_service, user_email):
    stats = {'total_files': 0, 'total_folders': 0, 'owned_by_me_files': 0, 'owned_by_me_folders': 0, 'shared_with_me_files': 0, 'shared_with_me_folders': 0, 'total_size_owned_bytes': 0}; all_files, page_token = [], None
    while True:
        try:
            results = _service.files().list(q="trashed=false", fields="nextPageToken, files(id, name, mimeType, size, owners, modifiedTime, webViewLink)", pageSize=1000, supportsAllDrives=True, includeItemsFromAllDrives=True, pageToken=page_token).execute(); files = results.get('files', []); all_files.extend(files)
            for item in files:
                is_folder = item.get('mimeType') == 'application/vnd.google-apps.folder'; is_owned_by_me = item.get('owners', [{}])[0].get('emailAddress', '') == user_email
                if is_folder:
                    stats['total_folders'] += 1
                    if is_owned_by_me: stats['owned_by_me_folders'] += 1
                    else: stats['shared_with_me_folders'] += 1
                else:
                    stats['total_files'] += 1; size = int(item.get('size', 0))
                    if is_owned_by_me: stats['owned_by_me_files'] += 1; stats['total_size_owned_bytes'] += size
                    else: stats['shared_with_me_files'] += 1
            page_token = results.get('nextPageToken')
            if not page_token: break
        except Exception as e: st.error(f"Failed to fetch drive statistics: {e}"); return None
    all_files.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True); stats['recent_files'] = all_files[:10]; return stats

def get_file_details(_service, file_id):
    try: return _service.files().get(fileId=file_id, fields='id, name, mimeType, size, webViewLink, modifiedTime, owners, shortcutDetails, capabilities', supportsAllDrives=True).execute()
    except Exception: return None

def list_folder_contents(service, folder_id):
    all_items, total_size = [], 0; root_details = get_file_details(service, folder_id)
    if not root_details: return [], 0
    def recurse(s, f_id, path_prefix):
        nonlocal total_size; page_token = None
        while True:
            try: results = s.files().list(q=f"'{f_id}' in parents and trashed=false", fields="nextPageToken, files(id, name, mimeType, size, webViewLink, capabilities, owners, modifiedTime)", supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=100, pageToken=page_token).execute()
            except HttpError as e: st.warning(f"Could not access folder: {e}"); break
            for item in results.get('files', []):
                path = os.path.join(path_prefix, item['name']); size = int(item.get('size', 0)); total_size += size; all_items.append({**item, 'Path': path})
                if item['mimeType'] == 'application/vnd.google-apps.folder': recurse(s, item['id'], path)
            page_token = results.get('nextPageToken')
            if not page_token: break
    recurse(service, folder_id, root_details['name']); return all_items, total_size

def get_owner_and_all_items_recursive(_service, file_id):
    root_details = get_file_details(_service, file_id)
    if not root_details: return None, []
    all_items = []
    def recurse(f_id, path_list):
        page_token = None
        while True:
            try:
                fields_to_get = "nextPageToken, files(id, name, mimeType, webViewLink, capabilities, owners, modifiedTime, size)"; results = _service.files().list(q=f"'{f_id}' in parents and trashed=false", fields=fields_to_get, supportsAllDrives=True, includeItemsFromAllDrives=True, pageSize=200, pageToken=page_token).execute()
                for item in results.get('files', []):
                    current_path = path_list + [item['name']]; item['path'] = os.path.join(*current_path); all_items.append(item)
                    if item['mimeType'] == 'application/vnd.google-apps.folder': recurse(item['id'], current_path)
                page_token = results.get('nextPageToken')
                if not page_token: break
            except HttpError as e: st.warning(f"Could not access subfolder content: {e}"); break
    if root_details.get('mimeType') == 'application/vnd.google-apps.folder': recurse(file_id, [root_details.get('name', 'Root')])
    return root_details, all_items

def get_user_folders(_service):
    folders = []; page_token = None
    while True:
        try:
            results = _service.files().list(q="mimeType='application/vnd.google-apps.folder' and 'root' in parents and trashed=false", fields="nextPageToken, files(id, name)", pageSize=200, pageToken=page_token).execute()
            folders.extend(results.get('files', [])); page_token = results.get('nextPageToken')
            if not page_token: break
        except Exception as e: st.error(f"Failed to fetch your folders: {e}"); break
    return folders

def get_and_sort_folder_items(_service, folder_id, current_user_email):
    items, page_token = [], None
    while True:
        try:
            fields = "nextPageToken, files(id, name, mimeType, size, webViewLink, modifiedTime, owners, shortcutDetails, capabilities)"; results = _service.files().list(q=f"'{folder_id}' in parents and trashed=false", fields=fields, pageSize=500, pageToken=page_token, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            items.extend(results.get('files', [])); page_token = results.get('nextPageToken')
            if not page_token: break
        except Exception as e: st.error(f"Failed to fetch Drive items: {e}"); break
    processed_items = []
    for item in items:
        is_shortcut = item.get('mimeType') == 'application/vnd.google-apps.shortcut'; effective_mime, effective_owners = item.get('mimeType'), item.get('owners')
        if is_shortcut:
            target_id = item.get('shortcutDetails', {}).get('targetId')
            if not target_id: continue
            target_details = get_file_details(_service, target_id)
            if not target_details: continue
            effective_mime, effective_owners = target_details.get('mimeType'), target_details.get('owners')
        is_folder = effective_mime == 'application/vnd.google-apps.folder'; owner_email = effective_owners[0].get('emailAddress', '') if effective_owners else ''; is_owned_by_me = owner_email == current_user_email
        item.update({'effective_owner_name': effective_owners[0].get('displayName', 'N/A') if effective_owners else "N/A", 'is_owned_by_me': is_owned_by_me, 'effective_mime': effective_mime, 'is_folder_sort': 1 if is_folder else 2, 'is_owned_by_me_sort': 1 if is_owned_by_me else 2, 'name_sort': item.get('name', '').lower()})
        processed_items.append(item)
    processed_items.sort(key=lambda x: (x['is_folder_sort'], x['is_owned_by_me_sort'], x['name_sort'])); return processed_items

def analyze_content(all_items):
    promo_keywords = ['subscribe', 'join', 'channel', 'promo', 'telegram', 'read', 'watch']; names = [item['name'] for item in all_items]; name_counts = Counter(names); repeated_names = {name for name, count in name_counts.items() if count > 1}
    suggested_promo_files = set()
    for name in repeated_names:
        if any(keyword in name.lower() for keyword in promo_keywords): suggested_promo_files.add(name)
    common_text = os.path.commonprefix(names)
    if len(common_text) < 3 or not any(char.isalnum() for char in common_text): common_text = ""
    return common_text, list(suggested_promo_files)

def generate_excel_report(dataframes_dict, filename="report.xlsx"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, dataframe in dataframes_dict.items():
            if dataframe is not None and not dataframe.empty:
                dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
                ws = writer.sheets[sheet_name]
                if 'Link' in dataframe.columns:
                    url_col_idx = dataframe.columns.get_loc('Link') + 1
                    for row_idx in range(2, ws.max_row + 1):
                        cell = ws.cell(row=row_idx, column=url_col_idx)
                        if cell.value and 'http' in cell.value: cell.hyperlink, cell.style = cell.value, "Hyperlink"
    return output.getvalue(), filename

def create_standard_dataframe(items_list, select_status=False):
    processed_content = []
    for item in items_list:
        owner_name = item.get('owners', [{}])[0].get('displayName', 'N/A'); mod_time = pd.to_datetime(item.get('modifiedTime')).strftime('%Y-%m-%d %H:%M') if item.get('modifiedTime') else 'N/A'; size_mb = float(f"{int(item.get('size', 0)) / (1024*1024):.2f}") if 'size' in item and item['size'] is not None else 0.0
        processed_content.append({**item, 'Select': select_status, 'Name': item.get('name', 'N/A'), 'Type': 'Folder' if item.get('mimeType') == 'application/vnd.google-apps.folder' else 'File', 'Size (MB)': size_mb, 'Modified': mod_time, 'Owner': owner_name, 'Link': item.get('webViewLink', '#'), 'Path': item.get('Path', item.get('name'))})
    return pd.DataFrame(processed_content)

def reset_cleaner_state():
    st.session_state.cleaner_state = 'initial'; st.session_state.cleaner_link = ""; st.session_state.cleaner_root_details = None; st.session_state.cleaner_all_items = []; st.session_state.cleaner_success_log = None; st.session_state.cleaner_skipped_log = None; st.session_state.cleaner_dest_folder_name = None

def run_main_app(service):
    """Contains the entire Cloud Drive Manager application UI."""
    st.set_page_config(page_title=APP_NAME, page_icon="☁️", layout="wide")
    
    with st.sidebar:
        st.title(f"☁️ {APP_NAME}")
        st.write("---")
        st.subheader("Authenticated Account")
        user_name_placeholder, user_email_placeholder = st.empty(), st.empty()
        st.write("---")
        st.header("Menu")
        PAGES = ["Dashboard", "File Explorer", "Cloud Copy", "Bulk File Cleaner"]
        current_page_index = PAGES.index(st.session_state.page) if st.session_state.page in PAGES else 0
        selected_page = st.radio("Choose a page", PAGES, index=current_page_index, key="page_selector")
        if selected_page != st.session_state.page:
            st.session_state.page = selected_page
            if st.session_state.page != "Bulk File Cleaner": reset_cleaner_state()
            st.session_state.stats_loaded = False; st.rerun()
        st.info("Manage your Google Drive from one place.")
        st.write("---")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Logout", use_container_width=True, help="Log out of the app completely."):
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
        with col2:
            if st.button("Switch Account", use_container_width=True, help="Log out of the current Google Account to connect a different one."):
                for key in ['google_creds', 'drive_service', 'user_info', 'authorization_request_sent']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.query_params.clear()
                st.rerun()

    storage = get_drive_storage_info(service)
    if storage:
        user_name_placeholder.write(f"**Name:** {storage['user_name']}")
        user_email_placeholder.write(f"**Email:** {storage['user_email']}")
    else:
        st.error("Could not retrieve your account information from Google Drive. Logging out.")
        st.session_state.clear(); st.rerun()
    
    # --- Page Routing ---
    if st.session_state.page == "Dashboard":
        st.header("📊 Drive Dashboard"); st.markdown("---"); st.subheader("📦 Storage Overview")
        if 'usage_percent' in storage:
            st.progress(storage['usage_percent'] / 100, text=f"{storage['usage_percent']:.2f}% Used")
            c1, c2, c3 = st.columns(3); 
            c1.metric("Used Storage", f"{format_storage(storage['usage_gb'])}")
            c2.metric("Free Space", f"{format_storage(storage['limit_gb'] - storage['usage_gb'])}")
            c3.metric("Total Storage", f"{format_storage(storage['limit_gb'])}")
        else:
            st.info("Storage information is not available for this account type.")
        
        st.markdown("---")
        if not st.session_state.stats_loaded:
            if st.button("📊 Get Drive Statistics"): st.session_state.stats_loaded = True; st.rerun()
            st.caption("This may take some time to load for large drives.")
        else:
            if st.button("🔄 Refresh Statistics"):
                st.rerun()
            drive_stats = get_drive_statistics(service, storage['user_email'])
            if drive_stats:
                with st.expander("🔍 Drive Content Analysis", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1: st.markdown("#### Overall Summary"); c1a, c2a, c3a = st.columns(3); c1a.metric("Total Items", f"{drive_stats['total_files'] + drive_stats['total_folders']:,}"); c2a.metric("Total Files", f"{drive_stats['total_files']:,}"); c3a.metric("Total Folders", f"{drive_stats['total_folders']:,}")
                    with c2: st.markdown("#### Ownership Breakdown"); owned_total = drive_stats['owned_by_me_files'] + drive_stats['owned_by_me_folders']; shared_total = drive_stats['shared_with_me_files'] + drive_stats['shared_with_me_folders']; c1b, c2b = st.columns(2); c1b.metric("Owned by You", f"{owned_total:,}"); c2b.metric("Shared with You", f"{shared_total:,}")
                    st.markdown(f"""- **Your Content:**\n    - Files: `{drive_stats['owned_by_me_files']:,}`\n    - Folders: `{drive_stats['owned_by_me_folders']:,}`\n    - Storage Used by Your Files: `{format_storage(drive_stats['total_size_owned_bytes'] / (1024**3))}`\n- **Shared Content:**\n    - Files: `{drive_stats['shared_with_me_files']:,}`\n    - Folders: `{drive_stats['shared_with_me_folders']:,}`""")
                with st.expander("🕒 Recent Activity", expanded=True):
                    st.write("Top 10 most recently modified files in your Drive.")
                    if drive_stats['recent_files']: recent_files_data = [{"Name": item.get('name', 'N/A'), "Type": "Folder" if item.get('mimeType') == 'application/vnd.google-apps.folder' else "File", "Last Modified": pd.to_datetime(item.get('modifiedTime')).strftime('%Y-%m-%d %H:%M'), "Link": item.get('webViewLink', '#')} for item in drive_stats['recent_files']]; st.dataframe(pd.DataFrame(recent_files_data), column_config={"Link": st.column_config.LinkColumn("Open")}, hide_index=True, use_container_width=True)
                    else: st.info("No recent files found.")
            else: st.warning("Could not retrieve detailed drive statistics.")
    elif st.session_state.page == "Cloud Copy":
        st.header("☁️➡️☁️ Cloud Copy"); st.info("Paste a Google Drive file or folder link below to begin the copy process.")
        def fetch_source_details(service, link):
            st.session_state.fetched_file_details, st.session_state.folder_contents_df, st.session_state.copied_files_df, st.session_state.dest_id = None, None, None, None; st.session_state.skipped_files_df = None
            file_id = extract_file_id_from_link(link)
            if file_id:
                with st.spinner("Fetching details..."):
                    details = get_file_details(service, file_id)
                    if details:
                        st.session_state.fetched_file_details = details
                        if details['mimeType'] == 'application/vnd.google-apps.folder':
                            contents, total = list_folder_contents(service, file_id)
                            if contents: st.session_state.folder_contents_df = create_standard_dataframe(contents)
                            st.session_state.fetched_file_details['size'] = total
                        else: st.session_state.folder_contents_df = create_standard_dataframe([details])
            else: st.error("Invalid or empty link provided.")
        if 'drive_link_input' not in st.session_state: st.session_state.drive_link_input = ""
        if st.session_state.pop('auto_fetch_on_load', False): link_to_process = st.session_state.pop('link_to_copy', ""); st.session_state.drive_link_input = link_to_process; fetch_source_details(service, link_to_process)
        st.text_input("Google Drive Shareable Link", key="drive_link_input");
        if st.button("Fetch Details", key="fetch_details_button"): fetch_source_details(service, st.session_state.drive_link_input)
        if st.session_state.fetched_file_details:
            details = st.session_state.fetched_file_details; st.markdown("---"); st.subheader(f"Source Details: {get_file_icon(details)} {details.get('name')}")
            is_owner = details.get('owners', [{}])[0].get('emailAddress') == storage['user_email']
            if is_owner: st.success("✅ This is your own file/folder.")
            else: st.warning("🤝 This is a shared file/folder. Content can only be copied to your drive.")
            if st.session_state.folder_contents_df is not None and not st.session_state.folder_contents_df.empty:
                st.markdown("##### File Contents"); c1, c2, c3 = st.columns(3)
                with c1: select_all = st.checkbox("Select/Deselect All", value=True, key="cc_select_all"); st.caption("If none selected, ALL files will be copied.")
                with c2: show_raw = st.checkbox("Show Raw Data", value=False)
                with c3: excel_data, _ = generate_excel_report({'File List': st.session_state.folder_contents_df}); st.download_button("📥 Download List as Excel", excel_data, f"{details.get('name', 'file_list')}.xlsx")
                df = st.session_state.folder_contents_df.copy(); df['Select'] = select_all; visible_columns = ['Select', 'Name', 'Type', 'Size (MB)', 'Modified', 'Owner', 'Link', 'Path']; column_config = { "Link": st.column_config.LinkColumn("File Link", display_text="LINK"), "Size (MB)": st.column_config.NumberColumn(format="%.2f MB") }
                if not show_raw:
                    for col in df.columns:
                        if col not in visible_columns: column_config[col] = None
                st.session_state.edited_df = st.data_editor(df, column_order=visible_columns, column_config=column_config, use_container_width=True, hide_index=True, key="cc_data_editor")
            st.markdown("---"); st.subheader("Copy Destination"); user_folders = get_user_folders(service); folder_names, folder_ids = ["My Drive (Root)"] + [f['name'] for f in user_folders], ["root"] + [f['id'] for f in user_folders]; selected_folder_name, new_folder_name = st.selectbox("Select Destination Folder", options=folder_names), st.text_input("New Folder Name (Optional, creates a sub-folder)")
            if st.button("🚀 Start Copy Process"):
                edited_data = st.session_state.edited_df
                if not edited_data.Select.any(): selected_files = edited_data
                else: selected_files = edited_data[edited_data.Select]
                if selected_files.empty: st.warning("No files found to copy.")
                else:
                    st.session_state.copied_files_df = None; st.session_state.skipped_files_df = None; dest_id = folder_ids[folder_names.index(selected_folder_name)]; final_dest_name = new_folder_name if new_folder_name else selected_folder_name
                    if new_folder_name:
                        with st.spinner(f"Creating folder '{new_folder_name}'..."): new_folder = service.files().create(body={'name': new_folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [dest_id]}, fields='id').execute(); dest_id = new_folder['id']
                    st.session_state.dest_id = dest_id; copied_files_list, skipped_files_list = [], []; progress_bar = st.progress(0, text="Starting copy process...")
                    for i, row in enumerate(selected_files.itertuples(name="Pandas")):
                        progress_text = f"Processing ({i+1}/{len(selected_files)}): {row.Name}"; progress_bar.progress((i + 1) / len(selected_files), text=progress_text)
                        try: caps_dict = ast.literal_eval(row.capabilities) if isinstance(row.capabilities, str) else row.capabilities
                        except: caps_dict = {}
                        if not caps_dict.get('canCopy', True): skipped_files_list.append({'Name': row.Name, 'Reason': 'Copying disabled by owner'}); continue
                        file_meta = {'name': row.Name.replace('📁 ', '').replace('📄 ', ''), 'parents': [dest_id]}
                        try:
                            copied_file = service.files().copy(fileId=row.id, body=file_meta, supportsAllDrives=True, fields='id, name, webViewLink, size, mimeType').execute()
                            copied_files_list.append({'Name': copied_file['name'], 'Type': row.Type, 'Size (MB)': float(f"{int(copied_file.get('size', 0)) / (1024*1024):.2f}") if copied_file.get('size') else row._asdict().get('Size (MB)'),'Modified': row.Modified, 'Owner': storage['user_name'], 'Link': copied_file.get('webViewLink', '#'), 'Path': os.path.join(final_dest_name, copied_file['name'])})
                        except HttpError as e: skipped_files_list.append({'Name': row.Name, 'Reason': f"Error: {e.reason}"}); continue
                    st.session_state.copied_files_df = pd.DataFrame(copied_files_list) if copied_files_list else pd.DataFrame(); st.session_state.skipped_files_df = pd.DataFrame(skipped_files_list) if skipped_files_list else pd.DataFrame(); st.toast("✅ Copy process completed!", icon="🎉")
        if (st.session_state.copied_files_df is not None and not st.session_state.copied_files_df.empty) or (st.session_state.skipped_files_df is not None and not st.session_state.skipped_files_df.empty):
            st.markdown("---"); st.subheader("Process Results"); visible_columns = ['Name', 'Type', 'Size (MB)', 'Modified', 'Owner', 'Link', 'Path']; column_config = { "Link": st.column_config.LinkColumn("File Link", display_text="LINK"), "Size (MB)": st.column_config.NumberColumn(format="%.2f MB"), "Path": st.column_config.TextColumn("Destination Path") }
            if st.session_state.copied_files_df is not None and not st.session_state.copied_files_df.empty: st.write("#### ✅ Copied Files"); df_results = st.session_state.copied_files_df; display_cols = [col for col in visible_columns if col in df_results.columns]; st.dataframe(df_results, column_order=display_cols, column_config=column_config, hide_index=True, use_container_width=True)
            if st.session_state.skipped_files_df is not None and not st.session_state.skipped_files_df.empty: st.write("#### ⚠️ Skipped Files"); st.dataframe(st.session_state.skipped_files_df, hide_index=True, use_container_width=True)
            report_dfs = {'Copied_Files': st.session_state.copied_files_df, 'Skipped_Files': st.session_state.skipped_files_df}; excel_data, _ = generate_excel_report(report_dfs, "copy_report.xlsx"); st.download_button("📥 Download Full Report as Excel", excel_data, "copy_report.xlsx")
    elif st.session_state.page == "File Explorer":
        st.header("🗂️ My Drive Explorer")
        def fetch_and_set_initial_items():
            with st.spinner("Performing initial fetch..."): fetched_items = get_and_sort_folder_items(service, st.session_state.current_folder_id, storage['user_email']); st.session_state.folder_cache[st.session_state.current_folder_id] = fetched_items; st.toast(f"Fetched {len(fetched_items)} items.", icon="✅")
            st.session_state.initial_fetch_done = True
        if not st.session_state.initial_fetch_done: st.markdown("<br>", unsafe_allow_html=True); c1, c2, c3 = st.columns([1,2,1]); c2.button("🚀 Start Exploring My Drive", on_click=fetch_and_set_initial_items, use_container_width=True, type="primary")
        else:
            st.markdown("<a id='top'></a>", unsafe_allow_html=True); toolbar_cols = st.columns([4, 1])
            with toolbar_cols[0]:
                nav_items = [];
                if len(st.session_state.folder_path) > 1: nav_items.append({'type': 'back', 'name': '⬅️ Back'})
                for i, folder in enumerate(st.session_state.folder_path): nav_items.append({'type': 'breadcrumb', 'name': folder['name'], 'id': folder['id'], 'index': i})
                nav_cols = st.columns(len(nav_items))
                for i, item in enumerate(nav_items):
                    with nav_cols[i]:
                        if item['type'] == 'back':
                            if st.button(item['name'], key='nav_back', use_container_width=True): st.session_state.folder_path.pop(); st.session_state.update(current_folder_id=st.session_state.folder_path[-1]['id'], item_to_rename=None, item_to_delete=None); st.rerun()
                        elif item['type'] == 'breadcrumb':
                            if st.button(item['name'], key=f"path_{item['id']}", use_container_width=True, help=item['name']): st.session_state.update(current_folder_id=item['id'], folder_path=st.session_state.folder_path[:item['index']+1], item_to_rename=None, item_to_delete=None); st.rerun()
            current_folder_id = st.session_state.current_folder_id
            if current_folder_id not in st.session_state.folder_cache:
                with st.spinner("Loading folder..."): fetched_items = get_and_sort_folder_items(service, current_folder_id, storage['user_email']); st.session_state.folder_cache[current_folder_id] = fetched_items
                st.rerun()
            items_to_display = st.session_state.folder_cache.get(current_folder_id)
            with toolbar_cols[1]:
                if items_to_display:
                    export_data = [{'Name': item['name'], 'Type': "Folder" if item['is_folder_sort'] == 1 else "File", 'Size (MB)': f"{int(item.get('size', 0))/(1024*1024):.2f}" if item['is_folder_sort'] != 1 and item.get('size') else "", 'Modified Date': pd.to_datetime(item['modifiedTime']).strftime('%Y-%m-%d %H:%M'), 'Owner': item.get('effective_owner_name', 'N/A'), 'URL': item.get('webViewLink', '')} for item in items_to_display]; df_export = pd.DataFrame(export_data); output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Folder_Contents'); ws = writer.sheets['Folder_Contents']
                        for row_idx in range(2, ws.max_row + 1):
                            cell = ws.cell(row=row_idx, column=df_export.columns.get_loc('URL') + 1)
                            if cell.value: cell.hyperlink, cell.style = cell.value, "Hyperlink"
                    st.download_button(label="📥 Download Excel", data=output.getvalue(), file_name=f"{st.session_state.folder_path[-1]['name'].replace(' ', '_')}_contents.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            st.markdown("---")
            st.markdown("""<style>.sticky-header{position:sticky;top:50px;background-color:white;z-index:10;display:flex;flex-direction:row;align-items:center;padding:10px 5px;border-bottom:1px solid #e6e6e6;}.header-col{font-weight:bold;text-align:left;padding:0 4px;color:#262730;}.back-to-top{position:fixed;bottom:20px;right:25px;font-size:25px;background-color:rgba(0,0,0,0.4);color:white;width:50px;height:50px;text-align:center;border-radius:50%;cursor:pointer;opacity:0.7;transition:opacity .3s;text-decoration:none;line-height:50px;z-index:1000;}.back-to-top:hover{opacity:1;}</style>""", unsafe_allow_html=True); st.markdown('<a href="#top" class="back-to-top">⬆️</a>', unsafe_allow_html=True)
            if items_to_display is not None:
                if not items_to_display: st.info("This folder is empty.")
                else:
                    col_widths, headers = [0.8, 4, 1, 1, 1.5, 1.5, 2], ["", "Name", "Type", "Size", "Modified", "Owner", "Actions"]; header_html = ''.join([f'<div class="header-col" style="flex-grow:{w};flex-basis:0;">{h}</div>' for h, w in zip(headers, col_widths)]); st.markdown(f'<div class="sticky-header">{header_html}</div>', unsafe_allow_html=True)
                    for item in items_to_display:
                        row_cols = st.columns(col_widths); is_folder = item['is_folder_sort'] == 1; nav_id = item.get('shortcutDetails', {}).get('targetId') or item['id']
                        if is_folder:
                            if row_cols[0].button("➡️", key=f"open_{item['id']}", help="Open folder"): st.session_state.update(current_folder_id=nav_id, folder_path=st.session_state.folder_path + [{'name': item['name'], 'id': nav_id}], item_to_rename=None, item_to_delete=None); st.rerun()
                        elif item.get('webViewLink'): row_cols[0].link_button("🔗", item['webViewLink'], help="Open file in new tab")
                        with row_cols[1]:
                            if st.session_state.item_to_rename == item['id']:
                                with st.form(key=f"rename_form_{item['id']}"):
                                    new_name = st.text_input("New Name", value=item['name'], label_visibility="collapsed"); form_cols = st.columns(2)
                                    if form_cols[0].form_submit_button("💾", use_container_width=True):
                                        try: service.files().update(fileId=item['id'], body={'name': new_name}, supportsAllDrives=True).execute(); get_and_sort_folder_items.clear(); st.session_state.folder_cache.pop(st.session_state.current_folder_id, None); st.toast(f"Renamed to '{new_name}'", icon="✏️")
                                        except HttpError as e: st.error(f"Rename failed: {e}")
                                        st.session_state.item_to_rename = None; st.rerun()
                                    if form_cols[1].form_submit_button("❌", use_container_width=True): st.session_state.item_to_rename = None; st.rerun()
                            else: prefix = "🤝 " if not item.get('is_owned_by_me', True) else ""; st.write(f"{prefix}{get_file_icon(item)} {item['name']}")
                        row_cols[2].write("Folder" if is_folder else "File"); row_cols[3].write(f"{int(item.get('size', 0)) / (1024*1024):.2f} MB" if not is_folder and item.get('size') else ""); row_cols[4].write(pd.to_datetime(item['modifiedTime']).strftime('%y-%m-%d %H:%M')); row_cols[5].write(item.get('effective_owner_name', 'N/A'))
                        with row_cols[6]:
                            action_cols = st.columns(3)
                            if action_cols[0].button("✏️", key=f"rename_btn_{item['id']}", help="Rename"): st.session_state.item_to_rename = item['id']; st.rerun()
                            if action_cols[1].button("🗑️", key=f"delete_btn_{item['id']}", help="Delete"): st.session_state.item_to_delete = item; st.rerun()
                            if action_cols[2].button("📋", key=f"copy_btn_{item['id']}", help="Copy to my Drive"): st.session_state.update(link_to_copy=item.get('webViewLink'), auto_fetch_on_load=True, page="Cloud Copy"); st.rerun()
                        if st.session_state.item_to_delete and st.session_state.item_to_delete['id'] == item['id']:
                            st.warning(f"Are you sure you want to delete **{st.session_state.item_to_delete['name']}**?"); del_cols = st.columns([1,1,4])
                            if del_cols[0].button("✅ Yes, Delete", key=f"confirm_del_{item['id']}"):
                                try: service.files().delete(fileId=st.session_state.item_to_delete['id'], supportsAllDrives=True).execute(); get_and_sort_folder_items.clear(); st.session_state.folder_cache.pop(st.session_state.current_folder_id, None); st.toast(f"Deleted '{st.session_state.item_to_delete['name']}'", icon="🗑️")
                                except HttpError as e: st.error(f"Delete failed: {e}")
                                st.session_state.item_to_delete = None; st.rerun()
                            if del_cols[1].button("❌ Cancel", key=f"cancel_del_{item['id']}"): st.session_state.item_to_delete = None; st.rerun()
    elif st.session_state.page == "Bulk File Cleaner":
        st.header("🧹 Bulk File Cleaner"); st.info("Paste a Google Drive file/folder link to analyze and clean its content.")
        st.text_input("Google Drive Link", key="cleaner_link")
        if st.button("Fetch & Analyze", key="cleaner_fetch"):
            file_id = extract_file_id_from_link(st.session_state.cleaner_link)
            if file_id:
                root, items = get_owner_and_all_items_recursive(service, file_id)
                if root: st.session_state.cleaner_root_details = root; st.session_state.cleaner_all_items = items; st.session_state.cleaner_state = 'analyzed'; st.session_state.cleaner_success_log = None; st.session_state.cleaner_skipped_log = None
                else: st.error("Could not fetch details. Check the link and permissions.")
            else: st.error("Invalid Google Drive link provided.")
        if st.session_state.cleaner_state in ['analyzed', 'finished']:
            root = st.session_state.cleaner_root_details; items = st.session_state.cleaner_all_items; capabilities = root.get('capabilities', {}); can_edit_directly = capabilities.get('canDelete', False) and capabilities.get('canRename', False); all_content = [root] + items if root.get('mimeType') == 'application/vnd.google-apps.folder' else [root]
            st.markdown("---"); st.subheader(f"{get_file_icon(root)} {root.get('name')}")
            if can_edit_directly: st.success(f"✅ You have full edit permissions for this item.")
            else: st.warning(f"🤝 You have view/comment access. Content can only be copied to your drive.")
            c1, c2 = st.columns(2)
            with c1: show_raw = st.checkbox("Show Raw Data", value=False)
            with c2:
                df_full_list = create_standard_dataframe(all_content)
                if not df_full_list.empty: excel_data, excel_filename = generate_excel_report({'File_List': df_full_list}, f"{root.get('name', 'drive_content')}_full_list.xlsx"); st.download_button("📥 Download Full List as Excel", excel_data, excel_filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.markdown("---"); st.subheader("Analysis and Cleaning Actions"); suggested_tag, suggested_promo_files = analyze_content(all_content)
            st.markdown("**1. Rename Files**"); st.info("For shared content, name changes will be applied when files are copied to your drive."); tag_to_remove = st.text_input("Suggested promotional tag to remove from all names:", value=suggested_tag, key="cleaner_tag_remover")
            st.markdown("**2. Select Files to Process**"); select_all = st.checkbox("Select/Deselect All", value=True, key="cleaner_select_all"); st.caption("Note: If no files are selected, ALL files will be processed."); st.caption("Click on a cell in the 'Action' column to change it.")
            df_items = create_standard_dataframe(all_content, select_status=select_all); edited_df = pd.DataFrame()
            if not df_items.empty:
                df_items['New_Name'] = df_items['Name'].str.replace(st.session_state.cleaner_tag_remover, '', regex=False) if st.session_state.cleaner_tag_remover else df_items['Name']
                if can_edit_directly: df_items['Action'] = df_items.apply(lambda row: 'Delete' if row['Name'] in suggested_promo_files else 'Rename', axis=1)
                else: df_items['Action'] = df_items.apply(lambda row: 'Exclude' if row['Name'] in suggested_promo_files else 'Copy', axis=1)
                visible_columns = ['Select', 'Name', 'Type', 'Size (MB)', 'Modified', 'Owner', 'Link', 'Path', 'New_Name', 'Action']; column_config = { "Link": st.column_config.LinkColumn("File Link", display_text="LINK"), "Size (MB)": st.column_config.NumberColumn(format="%.2f MB"), "Action": st.column_config.SelectboxColumn("Action", options=["Copy", "Exclude"] if not can_edit_directly else ["Rename", "Delete", "Keep"], required=True), "Name": st.column_config.TextColumn("File Name", disabled=True), }
                if not show_raw:
                    for col in df_items.columns:
                        if col not in visible_columns: column_config[col] = None
                edited_df = st.data_editor(df_items, column_order=visible_columns, column_config=column_config, use_container_width=True, height=400, key="cleaner_data_editor", hide_index=True)
            with st.form("submission_form"):
                st.markdown("**3. Choose Destination (for copying shared content)**"); user_folders = get_user_folders(service); folder_names, folder_ids = ["My Drive (Root)"] + [f['name'] for f in user_folders], ["root"] + [f['id'] for f in user_folders]; dest_col1, dest_col2 = st.columns(2)
                with dest_col1: dest_folder_id = st.selectbox("Select Destination Folder", options=folder_ids, format_func=lambda x: dict(zip(folder_ids, folder_names)).get(x, "N/A"), disabled=can_edit_directly)
                with dest_col2: new_folder_name = st.text_input("New Folder Name (Optional)", disabled=can_edit_directly, help="If blank, the original folder name will be used.")
                button_text = "🚀 Start Cleaning Process" if can_edit_directly else "🚀 Start Copying and Cleaning Process"; submitted = st.form_submit_button(button_text, type="primary")
                if submitted and not edited_df.empty:
                    if not edited_df.Select.any(): actions_to_perform = edited_df
                    else: actions_to_perform = edited_df[edited_df['Select']]
                    log_entries = []; final_dest_id = dest_folder_id; new_root_folder_name = ""
                    with st.spinner("Processing files... Please wait."):
                        if not can_edit_directly:
                            new_root_folder_name = new_folder_name if new_folder_name else root.get('name'); st.session_state.cleaner_dest_folder_name = new_root_folder_name; st.text(f"Creating new root folder: '{new_root_folder_name}'"); new_folder_meta = {'name': new_root_folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [dest_folder_id]}; new_folder = service.files().create(body=new_folder_meta, fields='id', supportsAllDrives=True).execute(); final_dest_id = new_folder.get('id')
                        progress_bar = st.progress(0)
                        for i, row in enumerate(actions_to_perform.itertuples(name='Pandas')):
                            progress_bar.progress((i + 1) / len(actions_to_perform), text=f"Processing: {row.Name}"); log_entry = {'Status': 'Skipped', 'Name': row.Name, 'New Name': row.New_Name, 'Path': row.Path, 'Size (MB)': row._asdict().get('Size (MB)'), 'Link': 'N/A', 'Owner': row.Owner, 'Modified': row.Modified, 'Type': row.Type}
                            if can_edit_directly:
                                if row.Action == 'Delete':
                                    try: service.files().delete(fileId=row.id, supportsAllDrives=True).execute(); log_entry.update({'Status': 'Deleted', 'New Name': 'N/A', 'Size (MB)': 'N/A'})
                                    except HttpError as e: log_entry.update({'Status': f'Error Deleting: {e.reason}'})
                                elif row.Action == 'Rename' and row.Name != row.New_Name:
                                    try: updated_file = service.files().update(fileId=row.id, body={'name': row.New_Name}, supportsAllDrives=True, fields='webViewLink, size').execute(); log_entry.update({'Status': 'Renamed', 'Link': updated_file.get('webViewLink'), 'Size (MB)': float(f"{int(updated_file.get('size', 0)) / (1024*1024):.2f}") if updated_file.get('size') else 'N/A', 'Path': row.Path})
                                    except HttpError as e: log_entry.update({'Status': f'Error Renaming: {e.reason}'})
                            else: # Copying logic
                                if row.Action == 'Copy':
                                    try: capabilities_dict = ast.literal_eval(row.capabilities) if isinstance(row.capabilities, str) else row.capabilities
                                    except (ValueError, SyntaxError): capabilities_dict = {}
                                    if not capabilities_dict.get('canCopy', False): log_entry['Status'] = 'Skipped (Copy restricted)'
                                    else:
                                        try:
                                            file_meta = {'name': row.New_Name, 'parents': [final_dest_id]}; copied_file = service.files().copy(fileId=row.id, body=file_meta, supportsAllDrives=True, fields='id, name, webViewLink, size').execute(); dest_path = os.path.join(new_root_folder_name, os.path.basename(row.Path)) if row.Path else new_root_folder_name
                                            log_entry.update({'Status': 'Copied to Drive', 'New Name': copied_file['name'], 'Path': dest_path, 'Size (MB)': float(f"{int(copied_file.get('size', 0)) / (1024*1024):.2f}") if copied_file.get('size') else 'N/A', 'Link': copied_file.get('webViewLink'), 'Owner': storage['user_name']})
                                        except HttpError as e: log_entry['Status'] = f'Error Copying: {e.reason}'
                            log_entries.append(log_entry)
                    if log_entries: df_log = pd.DataFrame(log_entries); st.session_state.cleaner_success_log = df_log[df_log['Status'].isin(['Renamed', 'Deleted', 'Copied to Drive'])]; st.session_state.cleaner_skipped_log = df_log[~df_log['Status'].isin(['Renamed', 'Deleted', 'Copied to Drive'])]
                    else: st.session_state.cleaner_success_log = pd.DataFrame(); st.session_state.cleaner_skipped_log = pd.DataFrame()
                    st.session_state.cleaner_state = 'finished'; st.rerun()
        if st.session_state.cleaner_state == 'finished':
            st.subheader("✅ Process Complete")
            if st.session_state.cleaner_dest_folder_name: st.info(f"Files were copied to a new folder named: **{st.session_state.cleaner_dest_folder_name}**")
            results_config = {"Link": st.column_config.LinkColumn("File Link", display_text="LINK"),"Size (MB)": st.column_config.NumberColumn(format="%.2f MB"),"Path": st.column_config.TextColumn("Destination Path"),"Name": st.column_config.TextColumn("File Name")}
            if st.session_state.cleaner_success_log is not None and not st.session_state.cleaner_success_log.empty: st.write("#### Successful Actions"); df_success = st.session_state.cleaner_success_log; st.dataframe(df_success, use_container_width=True, hide_index=True, column_config=results_config)
            if st.session_state.cleaner_skipped_log is not None and not st.session_state.cleaner_skipped_log.empty: st.write("#### ⚠️ Skipped Files & Errors"); df_skipped = st.session_state.cleaner_skipped_log; st.dataframe(df_skipped, use_container_width=True, hide_index=True)
            report_dfs = {'Successful_Actions': st.session_state.cleaner_success_log, 'Skipped_and_Errors': st.session_state.cleaner_skipped_log}; excel_data, _ = generate_excel_report(report_dfs, "cleaning_report.xlsx"); st.download_button("📥 Download Full Report", excel_data, "cleaning_report.xlsx")
            if (st.session_state.cleaner_success_log is None or st.session_state.cleaner_success_log.empty) and (st.session_state.cleaner_skipped_log is None or st.session_state.cleaner_skipped_log.empty): st.info("No actions were performed.")
            st.button("Start New Task", on_click=reset_cleaner_state)

# --- FINAL APP ENTRY POINT ---
st.set_page_config(page_title=APP_NAME, layout="centered")

# This single function call handles everything: login, redirects, authorization, and the access request workflow.
service = get_authenticated_service()

if service:
    # If the service object is returned, the user is fully authenticated and authorized.
    # We can now run the main application with its full wide layout.
    run_main_app(service)

# If 'service' is None, the get_authenticated_service() function has already displayed the necessary UI
# (e.g., the "Login with Google" button or the "Access Denied" page). No further action is needed here.

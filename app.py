import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Configuration ---
# These scopes grant permission to view, edit, create, and delete files in Google Drive.
SCOPES = ['https://www.googleapis.com/auth/drive']

# --- Helper Functions ---
def get_redirect_uri():
    """Returns the hardcoded redirect URI for the deployed app."""
    # This now uses your specific app URL to ensure Google redirects correctly.
    return "https://g-drive-app.streamlit.app"

def initialize_google_flow():
    """Initializes the Google OAuth flow."""
    try:
        # Construct the client_config from Streamlit secrets
        client_config = {
            "web": {
                "client_id": st.secrets["google_credentials"]["client_id"],
                "project_id": st.secrets["google_credentials"]["project_id"],
                "auth_uri": st.secrets["google_credentials"]["auth_uri"],
                "token_uri": st.secrets["google_credentials"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["google_credentials"]["auth_provider_x509_cert_url"],
                "client_secret": st.secrets["google_credentials"]["client_secret"],
                "redirect_uris": [get_redirect_uri()]
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=get_redirect_uri())
        return flow
    except KeyError as e:
        st.error(f"Missing Google credential in Streamlit secrets: {e}. Please check your secrets configuration in Streamlit Cloud.")
        return None
    except Exception as e:
        st.error(f"An error occurred during Google Flow initialization: {e}")
        return None

def get_drive_service():
    """Returns an authenticated Google Drive API service instance."""
    if 'credentials' not in st.session_state or not st.session_state.credentials:
        return None
    
    try:
        creds = Credentials.from_authorized_user_info(st.session_state.credentials, SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Failed to build Drive service: {e}")
        # Clear potentially corrupted credentials
        del st.session_state.credentials
        st.rerun()
        return None

# --- Main App Logic ---
st.set_page_config(layout="centered")
st.title("G-Drive Manager")
st.write("A simple web app to list, upload, and delete files in your Google Drive.")

# Initialize the OAuth flow
flow = initialize_google_flow()
if not flow:
    st.stop()

# Handle the OAuth callback
query_params = st.query_params
if 'code' in query_params and 'credentials' not in st.session_state:
    try:
        code = query_params['code']
        flow.fetch_token(code=code)
        # Store credentials in session state as a dictionary
        creds_info = {
            'token': flow.credentials.token,
            'refresh_token': flow.credentials.refresh_token,
            'token_uri': flow.credentials.token_uri,
            'client_id': flow.credentials.client_id,
            'client_secret': flow.credentials.client_secret,
            'scopes': flow.credentials.scopes
        }
        st.session_state.credentials = creds_info
        # Clear the query params to prevent re-running this block
        st.query_params.clear()
        st.rerun() # Rerun to update the UI
    except Exception as e:
        st.error(f"Failed to fetch token: {e}")
        st.stop()

# --- UI Rendering ---
# Check if user is authenticated
if 'credentials' not in st.session_state:
    # User is not authenticated, show login button
    auth_url, _ = flow.authorization_url(prompt='consent')
    st.link_button("Login with Google", auth_url)
else:
    # User is authenticated, show the main app
    st.success("You are logged in.")
    drive_service = get_drive_service()

    if drive_service:
        tab1, tab2, tab3 = st.tabs(["List Files", "Upload File", "Delete File"])

        with tab1:
            st.header("Your Google Drive Files")
            if st.button("Refresh File List"):
                st.rerun()
            try:
                # List the 15 most recent files
                results = drive_service.files().list(
                    pageSize=15, fields="nextPageToken, files(id, name, mimeType)").execute()
                items = results.get('files', [])

                if not items:
                    st.info("No files found in your Google Drive.")
                else:
                    for item in items:
                        st.write(f"📄 {item['name']} (ID: `{item['id']}`)")
            except HttpError as error:
                st.error(f'An error occurred: {error}')

        with tab2:
            st.header("Upload a File to Drive")
            uploaded_file = st.file_uploader("Choose a file to upload")

            if uploaded_file is not None:
                if st.button("Upload Now"):
                    with st.spinner('Uploading...'):
                        try:
                            file_metadata = {'name': uploaded_file.name}
                            media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), mimetype=uploaded_file.type)
                            file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                            st.success(f"File uploaded successfully! File ID: `{file.get('id')}`")
                        except HttpError as error:

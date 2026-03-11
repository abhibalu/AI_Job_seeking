import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

OAUTH_CREDENTIALS_FILE = 'google-authentication.json'
TOKEN_FILE = 'google-token.json'


def get_credentials():
    """Gets valid user credentials via OAuth2.
    First run opens a browser for login. After that, uses cached token.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(OAUTH_CREDENTIALS_FILE):
                logger.error(f"OAuth credentials file not found: {OAUTH_CREDENTIALS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds


def _get_or_create_folder(drive_service, folder_name: str, parent_id: str) -> str:
    """Find an existing folder by name inside a parent, or create it.
    Returns the folder ID.
    """
    query = (
        f"name = '{folder_name}' "
        f"and '{parent_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    results = drive_service.files().list(q=query, fields='files(id)', pageSize=1).execute()
    files = results.get('files', [])

    if files:
        return files[0]['id']

    # Create the folder
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    logger.info(f"Created Drive folder: {folder_name}")
    return folder['id']


def _find_existing_doc(drive_service, doc_title: str, folder_id: str) -> str | None:
    """Find an existing doc by title inside a folder. Returns file ID or None."""
    query = (
        f"name = '{doc_title}' "
        f"and '{folder_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and trashed = false"
    )
    results = drive_service.files().list(q=query, fields='files(id)', pageSize=1).execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None


def create_tailored_resume_doc(job_title: str, company: str, resume_data: dict, folder_id: str = None) -> str:
    """Creates (or replaces) a Google Doc with the tailored resume content.

    Folder structure: OtooCV / <Company Name> / <Resume Doc>
    If a doc with the same title already exists in the company folder, it is replaced.

    Returns the URL of the Google Doc.
    """
    creds = get_credentials()
    if not creds:
        raise ValueError("Google API credentials are not configured.")

    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)

    # 1. Resolve the company subfolder
    company_name = company.strip() if company else 'Other'
    if folder_id:
        company_folder_id = _get_or_create_folder(drive_service, company_name, folder_id)
    else:
        company_folder_id = None

    # 2. Check for existing doc to replace
    doc_title = f"{resume_data.get('fullName', 'Resume')} - {job_title} @ {company_name}"
    existing_doc_id = None
    if company_folder_id:
        existing_doc_id = _find_existing_doc(drive_service, doc_title, company_folder_id)

    if existing_doc_id:
        # Clear existing doc content and reuse it
        document_id = existing_doc_id
        doc_info = docs_service.documents().get(documentId=document_id).execute()
        content = doc_info.get('body', {}).get('content', [])
        end_index = content[-1].get('endIndex', 1) - 1 if content else 1

        requests = []
        if end_index > 1:
            requests.append({
                'deleteContentRange': {
                    'range': {'startIndex': 1, 'endIndex': end_index}
                }
            })
        # Insert new content
        text = _build_resume_text(resume_data)
        requests.append({
            'insertText': {
                'location': {'index': 1},
                'text': text
            }
        })
        docs_service.documents().batchUpdate(
            documentId=document_id, body={'requests': requests}
        ).execute()
        logger.info(f"Replaced existing doc: {doc_title}")
    else:
        # Create new doc
        file_metadata = {
            'name': doc_title,
            'mimeType': 'application/vnd.google-apps.document',
        }
        if company_folder_id:
            file_metadata['parents'] = [company_folder_id]

        created_file = drive_service.files().create(body=file_metadata, fields='id').execute()
        document_id = created_file.get('id')

        text = _build_resume_text(resume_data)
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': text
            }
        }]
        docs_service.documents().batchUpdate(
            documentId=document_id, body={'requests': requests}
        ).execute()
        logger.info(f"Created new doc: {doc_title}")

    return f"https://docs.google.com/document/d/{document_id}/edit"


def _build_resume_text(data: dict) -> str:
    """Build plain text resume content from the resume data dict."""
    lines = []

    # Header
    lines.append(data.get('fullName', ''))
    contact = []
    if data.get('phone'):
        contact.append(data['phone'])
    if data.get('email'):
        contact.append(data['email'])
    if data.get('websites'):
        contact.extend(data['websites'])
    if contact:
        lines.append(' | '.join(contact))
    lines.append('')

    # Summary
    if data.get('summary'):
        lines.append('PROFILE')
        lines.append(data['summary'])
        lines.append('')

    # Skills
    if data.get('skills'):
        lines.append('SKILLS AND TECHNOLOGY')
        for skill in data['skills']:
            if isinstance(skill, dict):
                name = skill.get('name', '')
                keywords = ', '.join(skill.get('keywords', []))
                lines.append(f'{name}: {keywords}')
            else:
                lines.append(str(skill))
        lines.append('')

    # Experience
    if data.get('experience'):
        lines.append('WORK EXPERIENCE')
        for exp in data['experience']:
            period = exp.get('period', '')
            location = exp.get('location', '')
            lines.append(f'{period} — {location}')
            lines.append(f"{exp.get('role', '')} — {exp.get('company', '')}")
            for achievement in exp.get('achievements', []):
                lines.append(f'  • {achievement}')
            lines.append('')

    # Education
    if data.get('education'):
        lines.append('EDUCATION & QUALIFICATIONS')
        for edu in data['education']:
            lines.append(f"{edu.get('institution', '')} — {edu.get('degree', '')} ({edu.get('period', '')})")
        lines.append('')

    return '\n'.join(lines)

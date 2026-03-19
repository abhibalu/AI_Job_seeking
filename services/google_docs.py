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
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.exception("OAuth token refresh failed")
                # Delete stale token so next call triggers re-auth
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                raise ValueError(
                    "Google OAuth token has been expired or revoked. "
                    "Delete google-token.json and re-authenticate."
                ) from e
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
    safe_name = folder_name.replace("'", "\\'")
    query = (
        f"name = '{safe_name}' "
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
    safe_title = doc_title.replace("'", "\\'")
    query = (
        f"name = '{safe_title}' "
        f"and '{folder_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.document' "
        f"and trashed = false"
    )
    results = drive_service.files().list(q=query, fields='files(id)', pageSize=1).execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None


def _extract_doc_paragraphs(docs_service, doc_id: str) -> list[str]:
    """Return all non-empty paragraph texts from a GDoc, preserving order."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs = []
    for element in doc.get('body', {}).get('content', []):
        para = element.get('paragraph', {})
        text = ''.join(
            run.get('textRun', {}).get('content', '')
            for run in para.get('elements', [])
        ).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_doc_structure(docs_service, doc_id: str) -> list[dict]:
    """Return every non-empty paragraph with its text and position indices.

    Used to find insertion points after replaceAllText has been applied.
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs = []
    for element in doc.get('body', {}).get('content', []):
        para = element.get('paragraph', {})
        text = ''.join(
            run.get('textRun', {}).get('content', '')
            for run in para.get('elements', [])
        ).strip()
        if text:
            paragraphs.append({
                "text": text,
                "start": element.get('startIndex', 0),
                "end": element.get('endIndex', 0),
            })
    return paragraphs


def _find_paragraph_in_structure(
    target_text: str, doc_structure: list[dict]
) -> dict | None:
    """Find the doc_structure entry whose word overlap with target is highest (>= 0.5)."""
    target_words = set(target_text.lower().split())
    if not target_words:
        return None
    best, best_score = None, 0.0
    for para in doc_structure:
        para_words = set(para["text"].lower().split())
        if not para_words:
            continue
        score = len(target_words & para_words) / max(len(target_words), len(para_words))
        if score > best_score:
            best_score = score
            best = para
    return best if best_score >= 0.5 else None


def _find_best_gdoc_match(target: str, paragraphs: list[str]) -> str | None:
    """Find the paragraph whose word overlap with target is highest (>= 0.5)."""
    target_words = set(target.lower().split())
    best_para, best_score = None, 0.0
    for para in paragraphs:
        para_words = set(para.lower().split())
        if not para_words:
            continue
        score = len(target_words & para_words) / max(len(target_words), len(para_words))
        if score > best_score:
            best_score = score
            best_para = para
    return best_para if best_score >= 0.5 else None


def _build_gdoc_replacements(
    gdoc_paragraphs: list[str],
    base_data: dict,
    tailored_data: dict,
) -> tuple[dict[str, str], list[dict]]:
    """Build {gdoc_paragraph: tailored_text} for every field that changed,
    plus a list of insertions for new items not present in the base.

    Uses the DB master resume (base_data) as the bridge to locate the right
    GDoc paragraph, since the GDoc is the source of truth for exact wording.

    Returns: (replacements, insertions)
        insertions: [{"after_text": str, "new_text": str}, ...]
        after_text is the tailored (post-replacement) text of the sibling paragraph.
    """
    replacements: dict[str, str] = {}
    insertions: list[dict] = []

    def _match_and_add(base_text: str, tailored_text: str) -> None:
        base_text = (base_text or '').strip()
        tailored_text = (tailored_text or '').strip()
        if not base_text or not tailored_text or base_text == tailored_text:
            return
        gdoc_para = _find_best_gdoc_match(base_text, gdoc_paragraphs)
        if gdoc_para and gdoc_para != tailored_text:
            replacements[gdoc_para] = tailored_text
            logger.debug(f"Replacement matched:\n  GDoc: {gdoc_para!r}\n  → {tailored_text!r}")
        else:
            logger.warning(f"No GDoc match for base text: {base_text!r}")

    # Summary
    _match_and_add(base_data.get('summary', ''), tailored_data.get('summary', ''))

    # Experience bullets (positional match)
    for b_job, t_job in zip(base_data.get('experience', []), tailored_data.get('experience', [])):
        for b_bullet, t_bullet in zip(b_job.get('achievements', []), t_job.get('achievements', [])):
            _match_and_add(b_bullet, t_bullet)

    # Skills — only process when both lists use the same format.
    # Base GDoc may have "Category: kw, kw" lines while tailored data has bare
    # keywords.  Positional zip across incompatible formats destroys formatting.
    base_skills = base_data.get('skills', [])
    tailored_skills = tailored_data.get('skills', [])
    base_has_categories = any(':' in str(s) for s in base_skills)
    tailored_has_categories = any(':' in str(s) for s in tailored_skills)
    skills_compatible = base_has_categories == tailored_has_categories

    if skills_compatible:
        for b_skill, t_skill in zip(base_skills, tailored_skills):
            _match_and_add(str(b_skill), str(t_skill))

        # ── Extra skills beyond what the base has ────────────────────────────
        if len(tailored_skills) > len(base_skills) and base_skills:
            last_idx = len(base_skills) - 1
            after_text = str(tailored_skills[last_idx])
            for extra in tailored_skills[len(base_skills):]:
                insertions.append({"after_text": after_text, "new_text": str(extra)})
                # All extras reference the same sibling — reversed processing in
                # _apply_insertions handles ordering correctly
    else:
        logger.warning(
            "Skills format mismatch (structured vs keywords) — "
            "skipping skills replacement to preserve GDoc formatting"
        )

    # Extra experience bullets
    for b_job, t_job in zip(
        base_data.get('experience', []), tailored_data.get('experience', [])
    ):
        b_bullets = b_job.get('achievements', [])
        t_bullets = t_job.get('achievements', [])
        if len(t_bullets) > len(b_bullets) and b_bullets:
            last_idx = len(b_bullets) - 1
            after_text = t_bullets[last_idx]
            for extra in t_bullets[len(b_bullets):]:
                insertions.append({"after_text": after_text, "new_text": extra})

    return replacements, insertions


def _build_replace_requests(replacements: dict) -> list[dict]:
    """Build replaceAllText batchUpdate requests from a {old: new} map."""
    return [
        {'replaceAllText': {
            'containsText': {'text': old, 'matchCase': True},
            'replaceText': new
        }}
        for old, new in replacements.items()
        if old.strip() and old != new
    ]


def _apply_insertions(
    docs_service, doc_id: str, insertions: list[dict]
) -> None:
    """Insert new paragraphs (skills lines, experience bullets) into the GDoc.

    Each insertion specifies after_text (the sibling to insert after) and
    new_text (the content to add).  Insertions are processed bottom-to-top
    so that earlier inserts don't shift the indices of later ones.

    The new paragraph inherits the paragraph style (font, spacing, indent,
    bullet style) of the sibling because insertText with \\n splits the
    paragraph and the new paragraph copies the style.
    """
    if not insertions:
        return

    # Re-read doc structure to get fresh indices (after replaceAllText shifted things)
    doc_structure = _extract_doc_structure(docs_service, doc_id)

    # Build insertion requests — process bottom-to-top (reversed) so that
    # indices computed from the current doc state remain valid.
    requests = []
    for ins in reversed(insertions):
        sibling = _find_paragraph_in_structure(ins["after_text"], doc_structure)
        if sibling:
            # Insert \n + new text just before the sibling's trailing newline.
            # This creates a new paragraph that inherits the sibling's style.
            insert_index = sibling["end"] - 1
            requests.append({
                'insertText': {
                    'location': {'index': insert_index},
                    'text': '\n' + ins["new_text"]
                }
            })
        else:
            logger.warning(
                f"No sibling paragraph found for insertion after: {ins['after_text']!r}"
            )

    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={'requests': requests}
        ).execute()
        logger.info(f"Applied {len(requests)} text insertions to {doc_id}")


def create_tailored_resume_doc(
    job_title: str,
    company: str,
    resume_data: dict,
    folder_id: str = None,
    base_doc_id: str | None = None,
    base_resume_data: dict | None = None,
) -> str:
    """Creates (or replaces) a Google Doc with the tailored resume content.

    Folder structure: OtooCV / <Company Name> / <Resume Doc>
    If a doc with the same title already exists in the company folder, it is replaced.

    When base_doc_id is provided, copies the base resume GDoc (preserving all
    formatting) and swaps in tailored text via replaceAllText. base_resume_data
    (DB master, frontend format) is used to locate the right GDoc paragraph for
    each changed field — the actual GDoc text is used as the match target so that
    LLM-parsing drift between the GDoc and DB doesn't break replacements.

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

    # 2. Doc title (same for both paths)
    doc_title = f"{resume_data.get('fullName', 'Resume')} - {job_title} @ {company_name}"

    # ── Copy-and-fill path (formatted output) ────────────────────────────────
    if base_doc_id:
        # Delete any existing doc with this title so we start from a clean copy
        if company_folder_id:
            existing_doc_id = _find_existing_doc(drive_service, doc_title, company_folder_id)
            if existing_doc_id:
                drive_service.files().delete(fileId=existing_doc_id).execute()
                logger.info(f"Deleted existing doc before copy: {doc_title}")

        # Copy the base resume GDoc (inherits all formatting)
        copy_body: dict = {'name': doc_title}
        if company_folder_id:
            copy_body['parents'] = [company_folder_id]

        copied = drive_service.files().copy(fileId=base_doc_id, body=copy_body, fields='id').execute()
        document_id = copied['id']
        logger.info(f"Copied base doc {base_doc_id} → {document_id} ({doc_title})")

        # Build replacements from actual GDoc paragraph texts (not DB-parsed text)
        if base_resume_data:
            gdoc_paragraphs = _extract_doc_paragraphs(docs_service, document_id)
            replacements, insertions = _build_gdoc_replacements(
                gdoc_paragraphs, base_resume_data, resume_data
            )
            replace_requests = _build_replace_requests(replacements)
            if replace_requests:
                docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': replace_requests}
                ).execute()
                logger.info(f"Applied {len(replace_requests)} text replacements to {document_id}")
            else:
                logger.info("No text differences found between base and tailored resume")

            # Insert new paragraphs (extra skills lines, experience bullets)
            if insertions:
                _apply_insertions(docs_service, document_id, insertions)

        return f"https://docs.google.com/document/d/{document_id}/edit"

    # ── Plain-text fallback path (original behaviour) ─────────────────────────
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


def read_google_doc(document_id: str) -> str:
    """Read plain text content from a Google Doc."""
    creds = get_credentials()
    if not creds:
        raise ValueError("Google API credentials are not configured.")

    docs_service = build('docs', 'v1', credentials=creds)
    doc = docs_service.documents().get(documentId=document_id).execute()

    # Extract text from document body
    text_parts = []
    for element in doc.get('body', {}).get('content', []):
        paragraph = element.get('paragraph', {})
        for run in paragraph.get('elements', []):
            text_run = run.get('textRun', {})
            if text_run.get('content'):
                text_parts.append(text_run['content'])

    return ''.join(text_parts)


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

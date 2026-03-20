import os
import re
import logging
from dataclasses import dataclass, field
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


# ── Export Result Model (Layer 1) ─────────────────────────────────────────────

@dataclass
class ExportFieldResult:
    section: str        # "summary", "experience.0.achievements.2", "skills.3"
    action: str         # "replace" | "insert"
    status: str         # "applied" | "skipped" | "failed"
    reason: str | None = None  # None if applied; "no_match", "no_sibling", "format_mismatch", "api_no_match", "verification_failed"
    base_snippet: str = ""     # first 80 chars, for debugging


@dataclass
class ExportResult:
    doc_url: str
    doc_id: str
    path: str                                   # "copy_and_fill" | "plain_text"
    fields: list[ExportFieldResult] = field(default_factory=list)
    verified: bool = False
    verification_mismatches: int = 0

    @property
    def status(self) -> str:
        if not self.fields:
            return "no_changes"
        applied = sum(1 for f in self.fields if f.status == "applied")
        total = len(self.fields)
        if applied == 0:
            return "failed"
        if applied < total:
            return "partial"
        return "success"

    @property
    def summary(self) -> dict:
        applied = sum(1 for f in self.fields if f.status == "applied")
        skipped = sum(1 for f in self.fields if f.status in ("skipped", "failed"))
        return {"total": len(self.fields), "applied": applied, "skipped": skipped}

    @property
    def skipped_fields(self) -> list[dict]:
        return [
            {"section": f.section, "reason": f.reason or "unknown"}
            for f in self.fields
            if f.status in ("skipped", "failed")
        ]


# ── Text Normalization (Layer 2) ─────────────────────────────────────────────

_BULLET_RE = re.compile(r'^[\u2022\-\*\u25E6\u25AA\u2023\u25CF]\s*')
_WHITESPACE_RE = re.compile(r'\s+')
_SMART_QUOTES = str.maketrans({
    '\u2018': "'", '\u2019': "'",   # smart single quotes → ASCII
    '\u201C': '"', '\u201D': '"',   # smart double quotes → ASCII
    '\u2013': '-', '\u2014': '-',   # en/em dash → hyphen
})


def _normalize_text(text: str) -> str:
    """Strip bullets, collapse whitespace, normalize smart quotes."""
    text = _BULLET_RE.sub('', text)
    text = text.translate(_SMART_QUOTES)
    text = _WHITESPACE_RE.sub(' ', text).strip()
    return text

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
    """Find the doc_structure entry whose word overlap with target is highest (>= 0.6).

    Uses normalized text comparison with prefix priority and length guard.
    """
    norm_target = _normalize_text(target_text)
    target_words = set(norm_target.lower().split())
    if not target_words:
        return None

    # Try exact prefix match first (first 40 chars)
    prefix = norm_target[:40]
    for para in doc_structure:
        if _normalize_text(para["text"]).startswith(prefix):
            return para

    best, best_score = None, 0.0
    for para in doc_structure:
        norm_para = _normalize_text(para["text"])
        para_words = set(norm_para.lower().split())
        if not para_words:
            continue
        # Length guard: skip if lengths differ by more than 2x
        if len(norm_para) > 2 * len(norm_target) or len(norm_target) > 2 * len(norm_para):
            continue
        score = len(target_words & para_words) / max(len(target_words), len(para_words))
        if score > best_score:
            best_score = score
            best = para
    return best if best_score >= 0.6 else None


def _find_best_gdoc_match(
    target: str,
    paragraphs: list[str],
    consumed: set[int] | None = None,
) -> str | None:
    """Find the paragraph whose word overlap with target is highest (>= 0.6).

    Improvements over original:
    - Normalizes text before comparison (strips bullets, collapses whitespace, normalizes quotes)
    - Tries exact prefix match (first 40 chars) before fuzzy overlap
    - Consumed tracking: matched paragraphs are excluded from future matches
    - Raised threshold to 0.6 + length guard (2x)
    """
    if consumed is None:
        consumed = set()

    norm_target = _normalize_text(target)
    target_words = set(norm_target.lower().split())
    if not target_words:
        return None

    # Try exact prefix match first
    prefix = norm_target[:40]
    for i, para in enumerate(paragraphs):
        if i in consumed:
            continue
        if _normalize_text(para).startswith(prefix):
            consumed.add(i)
            return para

    # Fuzzy word overlap
    best_para, best_score, best_idx = None, 0.0, -1
    for i, para in enumerate(paragraphs):
        if i in consumed:
            continue
        norm_para = _normalize_text(para)
        para_words = set(norm_para.lower().split())
        if not para_words:
            continue
        # Length guard: skip if lengths differ by more than 2x
        if len(norm_para) > 2 * len(norm_target) or len(norm_target) > 2 * len(norm_para):
            continue
        score = len(target_words & para_words) / max(len(target_words), len(para_words))
        if score > best_score:
            best_score = score
            best_para = para
            best_idx = i

    if best_score >= 0.6 and best_idx >= 0:
        consumed.add(best_idx)
        return best_para
    return None


def _build_gdoc_replacements(
    gdoc_paragraphs: list[str],
    base_data: dict,
    tailored_data: dict,
) -> tuple[dict[str, str], list[dict], list[ExportFieldResult]]:
    """Build {gdoc_paragraph: tailored_text} for every field that changed,
    plus a list of insertions for new items not present in the base,
    plus per-field tracking results.

    Uses the DB master resume (base_data) as the bridge to locate the right
    GDoc paragraph, since the GDoc is the source of truth for exact wording.

    Returns: (replacements, insertions, field_results)
    """
    replacements: dict[str, str] = {}
    insertions: list[dict] = []
    field_results: list[ExportFieldResult] = []
    consumed: set[int] = set()  # Track matched GDoc paragraph indices

    def _match_and_add(section: str, base_text: str, tailored_text: str) -> None:
        base_text = (base_text or '').strip()
        tailored_text = (tailored_text or '').strip()
        if not base_text or not tailored_text or base_text == tailored_text:
            return
        gdoc_para = _find_best_gdoc_match(base_text, gdoc_paragraphs, consumed)
        if gdoc_para and gdoc_para != tailored_text:
            replacements[gdoc_para] = tailored_text
            field_results.append(ExportFieldResult(
                section=section, action="replace", status="applied",
                base_snippet=base_text[:80],
            ))
            logger.debug(f"Replacement matched:\n  GDoc: {gdoc_para!r}\n  → {tailored_text!r}")
        else:
            field_results.append(ExportFieldResult(
                section=section, action="replace", status="skipped",
                reason="no_match", base_snippet=base_text[:80],
            ))
            logger.warning(f"No GDoc match for base text: {base_text!r}")

    # Summary
    _match_and_add("summary", base_data.get('summary', ''), tailored_data.get('summary', ''))

    # Experience bullets (positional match)
    for job_idx, (b_job, t_job) in enumerate(
        zip(base_data.get('experience', []), tailored_data.get('experience', []))
    ):
        for bullet_idx, (b_bullet, t_bullet) in enumerate(
            zip(b_job.get('achievements', []), t_job.get('achievements', []))
        ):
            _match_and_add(
                f"experience.{job_idx}.achievements.{bullet_idx}",
                b_bullet, t_bullet,
            )

    # Skills — only process when both lists use the same format.
    base_skills = base_data.get('skills', [])
    tailored_skills = tailored_data.get('skills', [])
    base_has_categories = any(':' in str(s) for s in base_skills)
    tailored_has_categories = any(':' in str(s) for s in tailored_skills)
    skills_compatible = base_has_categories == tailored_has_categories

    if skills_compatible:
        for skill_idx, (b_skill, t_skill) in enumerate(zip(base_skills, tailored_skills)):
            _match_and_add(f"skills.{skill_idx}", str(b_skill), str(t_skill))

        # ── Extra skills beyond what the base has ────────────────────────────
        if len(tailored_skills) > len(base_skills) and base_skills:
            last_idx = len(base_skills) - 1
            after_text = str(tailored_skills[last_idx])
            for extra_idx, extra in enumerate(tailored_skills[len(base_skills):]):
                insertions.append({"after_text": after_text, "new_text": str(extra)})
                field_results.append(ExportFieldResult(
                    section=f"skills.{len(base_skills) + extra_idx}",
                    action="insert", status="applied",
                    base_snippet=str(extra)[:80],
                ))
    else:
        logger.warning(
            "Skills format mismatch (structured vs keywords) — "
            "skipping skills replacement to preserve GDoc formatting"
        )
        # Record skipped fields for all skills
        for skill_idx in range(max(len(base_skills), len(tailored_skills))):
            field_results.append(ExportFieldResult(
                section=f"skills.{skill_idx}", action="replace",
                status="skipped", reason="format_mismatch",
                base_snippet=str(base_skills[skill_idx])[:80] if skill_idx < len(base_skills) else "",
            ))

    # Extra experience bullets
    for job_idx, (b_job, t_job) in enumerate(
        zip(base_data.get('experience', []), tailored_data.get('experience', []))
    ):
        b_bullets = b_job.get('achievements', [])
        t_bullets = t_job.get('achievements', [])
        if len(t_bullets) > len(b_bullets) and b_bullets:
            last_idx = len(b_bullets) - 1
            after_text = t_bullets[last_idx]
            for extra_idx, extra in enumerate(t_bullets[len(b_bullets):]):
                insertions.append({"after_text": after_text, "new_text": extra})
                field_results.append(ExportFieldResult(
                    section=f"experience.{job_idx}.achievements.{len(b_bullets) + extra_idx}",
                    action="insert", status="applied",
                    base_snippet=extra[:80],
                ))

    return replacements, insertions, field_results


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
    docs_service, doc_id: str, insertions: list[dict],
    field_results: list[ExportFieldResult],
) -> None:
    """Insert new paragraphs (skills lines, experience bullets) into the GDoc.

    Each insertion specifies after_text (the sibling to insert after) and
    new_text (the content to add).  Insertions are processed bottom-to-top
    so that earlier inserts don't shift the indices of later ones.

    The new paragraph inherits the paragraph style (font, spacing, indent,
    bullet style) of the sibling because insertText with \\n splits the
    paragraph and the new paragraph copies the style.

    Updates field_results in-place for failed insertions (no_sibling).
    """
    if not insertions:
        return

    # Re-read doc structure to get fresh indices (after replaceAllText shifted things)
    doc_structure = _extract_doc_structure(docs_service, doc_id)

    # Build insertion requests — process bottom-to-top (reversed) so that
    # indices computed from the current doc state remain valid.
    requests = []
    failed_texts: set[str] = set()
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
            failed_texts.add(ins["new_text"])
            logger.warning(
                f"No sibling paragraph found for insertion after: {ins['after_text']!r}"
            )

    # Mark failed insertions in field_results
    if failed_texts:
        for fr in field_results:
            if fr.action == "insert" and fr.base_snippet in failed_texts:
                fr.status = "failed"
                fr.reason = "no_sibling"

    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={'requests': requests}
        ).execute()
        logger.info(f"Applied {len(requests)} text insertions to {doc_id}")


def _check_occurrences_changed(
    batch_response: dict,
    replace_requests: list[dict],
    replacements: dict[str, str],
    field_results: list[ExportFieldResult],
) -> None:
    """Check batchUpdate response for replaceAllText replies with 0 occurrences.

    Marks corresponding field_results as failed with reason="api_no_match".
    This is a free check — no extra API call needed.
    """
    replies = batch_response.get('replies', [])
    # Build mapping: old_text → field_result for applied replacements
    old_texts = list(replacements.keys())

    for i, reply in enumerate(replies):
        rat_reply = reply.get('replaceAllText', {})
        occurrences = rat_reply.get('occurrencesChanged', 0)
        if occurrences == 0 and i < len(old_texts):
            old_text = old_texts[i]
            # Find the field_result that matches this replacement
            for fr in field_results:
                if (
                    fr.action == "replace"
                    and fr.status == "applied"
                    and fr.base_snippet == old_text[:80]
                ):
                    fr.status = "failed"
                    fr.reason = "api_no_match"
                    logger.warning(
                        f"replaceAllText returned 0 occurrences for: {old_text[:60]!r}"
                    )
                    break


def _verify_export(
    docs_service, doc_id: str, field_results: list[ExportFieldResult],
    replacements: dict[str, str],
) -> int:
    """Re-read the doc after mutations and verify tailored text is present.

    Returns the number of mismatches found. Updates failed fields' status.
    """
    paragraphs = _extract_doc_paragraphs(docs_service, doc_id)
    all_text = '\n'.join(paragraphs)
    mismatches = 0

    for fr in field_results:
        if fr.status != "applied":
            continue
        # Find the tailored text for this field
        tailored_text = None
        if fr.action == "replace":
            # Look up in replacements by base_snippet
            for old, new in replacements.items():
                if old[:80] == fr.base_snippet:
                    tailored_text = new
                    break
        elif fr.action == "insert":
            tailored_text = fr.base_snippet  # For inserts, base_snippet is the new text

        if not tailored_text:
            continue

        # Check if tailored text appears in doc (exact substring first)
        if tailored_text in all_text:
            continue

        # Fuzzy fallback: check word overlap >= 0.8
        tailored_words = set(tailored_text.lower().split())
        found = False
        for para in paragraphs:
            para_words = set(para.lower().split())
            if not para_words or not tailored_words:
                continue
            overlap = len(tailored_words & para_words) / max(len(tailored_words), len(para_words))
            if overlap >= 0.8:
                found = True
                break

        if not found:
            fr.status = "failed"
            fr.reason = "verification_failed"
            mismatches += 1

    return mismatches


def _append_missed_changes(
    docs_service, doc_id: str, field_results: list[ExportFieldResult],
    replacements: dict[str, str],
) -> None:
    """Append a demarcated section at the bottom of the doc with missed changes.

    Tier 2 fallback: when copy-and-fill partially succeeds, list the changes
    that couldn't be auto-applied so the user can manually place them.
    """
    missed: list[tuple[str, str]] = []  # (section, tailored_text)
    for fr in field_results:
        if fr.status not in ("skipped", "failed"):
            continue
        tailored_text = None
        if fr.action == "replace":
            for old, new in replacements.items():
                if old[:80] == fr.base_snippet:
                    tailored_text = new
                    break
        elif fr.action == "insert":
            tailored_text = fr.base_snippet
        if tailored_text:
            missed.append((fr.section, tailored_text))

    if not missed:
        return

    # Build the fallback text
    lines = [
        "\n\n--- Changes not auto-applied ---\n",
        "The following tailored text could not be matched to the document. "
        "Please copy into the correct sections manually.\n",
    ]
    for section, text in missed:
        lines.append(f"\n[{section}]\n{text}")

    fallback_text = '\n'.join(lines)

    # Get doc end index and append
    doc_structure = _extract_doc_structure(docs_service, doc_id)
    if doc_structure:
        end_index = doc_structure[-1]["end"] - 1
    else:
        end_index = 1

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': [{'insertText': {
            'location': {'index': end_index},
            'text': fallback_text,
        }}]}
    ).execute()
    logger.info(f"Appended {len(missed)} missed changes to doc bottom")


def create_tailored_resume_doc(
    job_title: str,
    company: str,
    resume_data: dict,
    folder_id: str = None,
    base_doc_id: str | None = None,
    base_resume_data: dict | None = None,
) -> ExportResult:
    """Creates (or replaces) a Google Doc with the tailored resume content.

    Folder structure: OtooCV / <Company Name> / <Resume Doc>
    If a doc with the same title already exists in the company folder, it is replaced.

    When base_doc_id is provided, copies the base resume GDoc (preserving all
    formatting) and swaps in tailored text via replaceAllText. base_resume_data
    (DB master, frontend format) is used to locate the right GDoc paragraph for
    each changed field — the actual GDoc text is used as the match target so that
    LLM-parsing drift between the GDoc and DB doesn't break replacements.

    Returns an ExportResult with per-field tracking, verification status, and
    the URL of the Google Doc.
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
    if base_doc_id and base_resume_data:
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
        doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
        logger.info(f"Copied base doc {base_doc_id} → {document_id} ({doc_title})")

        # Build replacements from actual GDoc paragraph texts (not DB-parsed text)
        gdoc_paragraphs = _extract_doc_paragraphs(docs_service, document_id)
        replacements, insertions, field_results = _build_gdoc_replacements(
            gdoc_paragraphs, base_resume_data, resume_data
        )

        # ── Pre-flight gate (Layer 2) ────────────────────────────────────
        total_changed = len([f for f in field_results if f.action == "replace"])
        matched = len([f for f in field_results if f.action == "replace" and f.status == "applied"])
        match_rate = matched / total_changed if total_changed > 0 else 1.0

        if total_changed > 0 and match_rate < 0.5:
            # Tier 3: Pre-flight match rate too low — fall through to plain-text
            logger.warning(
                f"Pre-flight match rate {match_rate:.0%} ({matched}/{total_changed}) below 50%% — "
                f"falling back to plain-text path"
            )
            # Delete the copy we just made
            drive_service.files().delete(fileId=document_id).execute()
            # Fall through to plain-text path below
        else:
            # Apply replacements
            replace_requests = _build_replace_requests(replacements)
            if replace_requests:
                batch_response = docs_service.documents().batchUpdate(
                    documentId=document_id,
                    body={'requests': replace_requests}
                ).execute()
                logger.info(f"Applied {len(replace_requests)} text replacements to {document_id}")

                # Layer 3a: Check occurrencesChanged from API response
                _check_occurrences_changed(
                    batch_response, replace_requests, replacements, field_results
                )
            else:
                logger.info("No text differences found between base and tailored resume")

            # Insert new paragraphs (extra skills lines, experience bullets)
            if insertions:
                _apply_insertions(docs_service, document_id, insertions, field_results)

            # Layer 3b: Post-export verification (re-read doc)
            mismatches = _verify_export(
                docs_service, document_id, field_results, replacements
            )

            result = ExportResult(
                doc_url=doc_url,
                doc_id=document_id,
                path="copy_and_fill",
                fields=field_results,
                verified=True,
                verification_mismatches=mismatches,
            )

            # Tier 2: If verification < 80% applied, append missed changes
            applied = result.summary["applied"]
            total = result.summary["total"]
            if total > 0 and applied / total < 0.8:
                _append_missed_changes(
                    docs_service, document_id, field_results, replacements
                )

            logger.info(
                f"Export result: status={result.status}, "
                f"applied={applied}/{total}, mismatches={mismatches}"
            )
            return result

    # ── Plain-text fallback path (Tier 3 or no base_doc_id) ───────────────────
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

    doc_url = f"https://docs.google.com/document/d/{document_id}/edit"
    return ExportResult(
        doc_url=doc_url,
        doc_id=document_id,
        path="plain_text",
        fields=[],
        verified=False,
        verification_mismatches=0,
    )


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

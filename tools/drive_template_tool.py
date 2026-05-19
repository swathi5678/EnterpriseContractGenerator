import re
import urllib.request
from urllib.parse import unquote

from langchain_core.tools import tool


def _extract_drive_id(source: str) -> tuple[str, str]:
    doc_match = re.search(r"docs\.google\.com/document/d/([^/]+)", source)
    if doc_match:
        return doc_match.group(1), "doc"

    file_match = re.search(r"drive\.google\.com/file/d/([^/]+)", source)
    if file_match:
        return file_match.group(1), "file"

    query_match = re.search(r"[?&]id=([^&]+)", source)
    if query_match:
        return query_match.group(1), "file"

    if re.fullmatch(r"[-\w]{20,}", source.strip()):
        return source.strip(), "file"

    raise ValueError("Enter a valid Google Drive shared link, Google Docs link, or file id.")


def _download(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_confirm_download(content: str) -> str | None:
    match = re.search(r'href="(/uc\?export=download[^"]+)"', content)
    if not match:
        return None
    return "https://drive.google.com" + unquote(match.group(1).replace("&amp;", "&"))


@tool
def load_google_drive_template(source: str) -> str:
    """Load an HTML template from a public Google Drive or Google Docs link."""
    file_id, source_type = _extract_drive_id(source)
    if source_type == "doc":
        url = f"https://docs.google.com/document/d/{file_id}/export?format=html"
    else:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"

    content = _download(url)
    confirm_url = _extract_confirm_download(content)
    if confirm_url:
        content = _download(confirm_url)

    if "<html" not in content.lower():
        content = f"<html><body>{content}</body></html>"
    return content

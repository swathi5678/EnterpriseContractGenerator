from pathlib import Path
from uuid import uuid4

from langchain_core.tools import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"


@tool
def save_document(html_content: str) -> str:
    """Save the final HTML document and return the saved file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"nda_contract_{uuid4().hex[:10]}.html"
    output_path.write_text(html_content, encoding="utf-8")
    return str(output_path)


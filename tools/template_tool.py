from pathlib import Path

from langchain_core.tools import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@tool
def load_template(template_name: str = "nda_template.html") -> str:
    """Load an HTML contract template from the templates directory."""
    template_path = PROJECT_ROOT / "templates" / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


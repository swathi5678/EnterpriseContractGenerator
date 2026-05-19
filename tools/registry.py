from tools.pdf_tool import generate_pdf
from tools.storage_tool import save_document
from tools.template_tool import load_template
from tools.drive_template_tool import load_google_drive_template


# This architecture follows MCP-style principles where tools are modular and
# independently consumable by agents through a centralized registry.
TOOLS = {
    "pdf_generator": generate_pdf,
    "document_storage": save_document,
    "template_loader": load_template,
    "drive_template_loader": load_google_drive_template,
}


def get_tool(name: str):
    if name not in TOOLS:
        raise KeyError(f"Unknown tool requested: {name}")
    return TOOLS[name]


def list_tools():
    return list(TOOLS.values())

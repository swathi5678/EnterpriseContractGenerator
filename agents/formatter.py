import html
import logging
import re

from tools.registry import get_tool


logger = logging.getLogger(__name__)


def _contract_to_sections(contract_text: str) -> str:
    lines = [line.strip() for line in contract_text.splitlines() if line.strip()]
    section_html = []
    current = []
    title = "Agreement Overview"

    heading_pattern = re.compile(r"^(\d+[\).\s-]*)?(Introduction|Confidentiality|Obligations|Termination|Governing Law|Signatures|Signature)(:)?$", re.I)
    for line in lines:
        clean = re.sub(r"^[#*\s]+|[*\s]+$", "", line)
        if heading_pattern.match(clean):
            if current:
                section_html.append(_render_section(title, current))
            title = clean.rstrip(":")
            current = []
        else:
            current.append(clean)
    if current:
        section_html.append(_render_section(title, current))
    return "\n".join(section_html)


def _render_section(title: str, paragraphs: list[str]) -> str:
    body = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    return f"<section class='contract-section'><h2>{html.escape(title)}</h2>{body}</section>"


def formatter_agent(state: dict) -> dict:
    logger.info("Formatter Agent running")
    template_loader = get_tool("template_loader")
    storage = get_tool("document_storage")

    template = template_loader.invoke({"template_name": "nda_template.html"})
    sections = _contract_to_sections(state["final_contract"])
    html_content = template.replace("{{ contract_title }}", "Non-Disclosure Agreement")
    html_content = html_content.replace("{{ user_prompt }}", html.escape(state["user_prompt"]))
    html_content = html_content.replace("{{ contract_sections }}", sections)
    html_content = html_content.replace("{{ compliance_report }}", html.escape(state["compliance_report"]))

    state["html_content"] = html_content
    state["html_path"] = storage.invoke({"html_content": html_content})
    state["current_agent"] = "Formatter"
    state.setdefault("messages", []).append("Formatter loaded the template and saved final HTML.")
    return state


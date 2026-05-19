import html
import logging
import re

from tools.registry import get_tool


logger = logging.getLogger(__name__)


def extract_placeholders(template_html: str) -> list[str]:
    curly = re.findall(r"{{\s*([a-zA-Z0-9_. -]+)\s*}}", template_html)
    square = re.findall(r"\[([A-Za-z][A-Za-z0-9 ,./&()'-]{2,80})\]", template_html)
    placeholders = curly + square
    return sorted({item.strip() for item in placeholders})


def _polish_generated_nda_html(html_content: str) -> str:
    html_content = html_content.replace("**", "")
    html_content = re.sub(
        r"<p>As a contract compliance reviewer.*?</p>\s*<p>Here is the corrected and enhanced final NDA:</p>\s*<p>---</p>",
        "",
        html_content,
        flags=re.S,
    )
    html_content = re.sub(
        r"<p>Summary of Changes and Rationale:.*?</section>",
        "</section>",
        html_content,
        flags=re.S,
    )
    html_content = re.sub(r"<p>---</p>", "", html_content)
    return html_content


def fill_template_agent(state: dict) -> dict:
    logger.info("Template Filler Agent running")
    storage = get_tool("document_storage")

    filled_html = state["template_html"]
    for key, value in state["fill_values"].items():
        safe_value = html.escape(str(value))
        filled_html = re.sub(r"{{\s*" + re.escape(key) + r"\s*}}", safe_value, filled_html)
        filled_html = filled_html.replace(f"[{key}]", safe_value)

    filled_html = _polish_generated_nda_html(filled_html)
    state["html_content"] = filled_html
    state["html_path"] = storage.invoke({"html_content": filled_html})
    state["current_agent"] = "Template Filler"
    state.setdefault("messages", []).append("Template Filler injected confirmed user details.")
    return state

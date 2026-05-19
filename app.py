from pathlib import Path
import re

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from agents.template_filler import extract_placeholders
from graph.workflow import run_contract_workflow, run_template_fill_workflow
from tools.registry import get_tool


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Multi-Agent Enterprise Contract Generator",
    page_icon=":page_facing_up:",
    layout="wide",
)

st.markdown(
    """
    <style>
      :root { color-scheme: light; }
      .stApp { background: #f4f7fb; color: #111827; }
      .block-container { padding-top: 1.2rem; max-width: 1440px; }
      [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #dbe3ef; }
      [data-testid="stSidebar"] * { color: #111827; }
      .app-header {
        border: 1px solid #dbe3ef;
        border-left: 5px solid #2563eb;
        padding: 18px 20px;
        background: #ffffff;
        margin-bottom: 16px;
      }
      .app-header h1 { margin: 0; font-size: 28px; color: #0f172a; letter-spacing: 0; }
      .app-header p { margin: 5px 0 0; color: #475569; }
      .metric-row {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-bottom: 12px;
      }
      .metric-card {
        border: 1px solid #dbe3ef;
        background: #fff;
        padding: 12px;
      }
      .metric-card span { color: #64748b; font-size: 12px; }
      .metric-card strong { display: block; color: #0f172a; font-size: 15px; margin-top: 3px; }
      div[data-testid="stChatMessage"] {
        border: 1px solid #e2e8f0;
        background: #ffffff;
        color: #0f172a;
        border-radius: 8px;
      }
      div[data-testid="stChatMessage"] * { color: #0f172a; }
      .stButton > button, .stDownloadButton > button {
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        background: #ffffff;
        color: #0f172a;
      }
      .stButton > button[kind="primary"] {
        background: #2563eb;
        border-color: #2563eb;
        color: #ffffff;
      }
      .stDownloadButton > button {
        background: #111827;
        color: #ffffff;
        border-color: #111827;
      }
      input, textarea {
        background: #ffffff !important;
        color: #111827 !important;
        border: 1px solid #cbd5e1 !important;
      }
      label, p, h1, h2, h3, h4, span, div { letter-spacing: 0; }
      .panel {
        background: #ffffff;
        border: 1px solid #dbe3ef;
        border-radius: 8px;
        padding: 16px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
      <h1>Multi-Agent Enterprise Contract Generator</h1>
      <p>Chat with the contract agent, fill Drive templates, review the rendered document, and export polished PDFs.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def init_state():
    defaults = {
        "chat_messages": [
            {
                "role": "assistant",
                "content": "Send an NDA request or paste a Google Drive template link. I will generate, fill, and prepare the PDF.",
            }
        ],
        "workflow_messages": [],
        "last_result": None,
        "editor_html": "",
        "drive_template_html": "",
        "drive_placeholders": [],
        "mode": "Generate NDA",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()


def update_progress(message: str, messages: list[str]):
    st.session_state["workflow_messages"] = messages
    workflow_status.update(label=message, state="running")


def store_result(result: dict, assistant_message: str):
    st.session_state["last_result"] = result
    st.session_state["editor_html"] = result.get("html_content", "")
    st.session_state["workflow_messages"] = result.get("messages", [])
    st.session_state["chat_messages"].append({"role": "assistant", "content": assistant_message})


def is_drive_link(text: str) -> bool:
    return bool(re.search(r"(drive\.google\.com|docs\.google\.com)", text, re.I))


def build_preview_html(html_content: str) -> str:
    return f"""
    <div style="height:760px; overflow:auto; background:#e5e7eb; padding:24px;">
      <div style="background:white; max-width:794px; min-height:1123px; margin:0 auto; padding:42px; box-shadow:0 10px 34px rgba(15,23,42,.16); color:#111827;">
        {html_content}
      </div>
    </div>
    """


def replace_first_text(html_content: str, find_text: str, replacement: str) -> str:
    if not find_text:
        return html_content
    return html_content.replace(find_text, replacement, 1)


with st.sidebar:
    st.subheader("Workspace")
    st.session_state["mode"] = st.radio(
        "Mode",
        ["Generate NDA", "Fill Drive Template"],
        index=0 if st.session_state["mode"] == "Generate NDA" else 1,
    )

    st.markdown(
        """
        <div class="metric-row">
          <div class="metric-card"><span>Agents</span><strong>5 Active</strong></div>
          <div class="metric-card"><span>Tools</span><strong>Registry</strong></div>
          <div class="metric-card"><span>Export</span><strong>PDF</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    samples = [
        "Generate an NDA between Acme Corp and John Doe for a 12-month AI consulting engagement.",
        "Create a mutual NDA for Contoso Ltd and Apex Robotics covering a 6-month product evaluation.",
        "Draft an NDA under Delaware law for a confidential data migration project.",
    ]
    with st.expander("Sample prompts", expanded=False):
        for sample in samples:
            if st.button(sample, key=sample, use_container_width=True):
                st.session_state["pending_prompt"] = sample

    st.divider()
    st.subheader("Document")
    result = st.session_state.get("last_result")
    if result and result.get("pdf_path"):
        st.success("PDF ready")
        if result.get("html_path"):
            st.caption(f"HTML: {Path(result['html_path']).name}")
    else:
        st.caption("No document generated yet.")

workflow_status = st.status("Ready", expanded=False)

left, right = st.columns([0.44, 0.56], gap="large")

with left:
    st.subheader("Contract Chat")
    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.session_state.pop("pending_prompt", None) or st.chat_input(
        "Ask for an NDA or paste a Google Drive template link..."
    )

    if prompt:
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        try:
            if st.session_state["mode"] == "Generate NDA" and not is_drive_link(prompt):
                workflow_status.update(label="Starting multi-agent NDA workflow", state="running")
                result = run_contract_workflow(prompt, progress_callback=update_progress)
                workflow_status.update(label="NDA generated", state="complete")
                store_result(result, "Generated the NDA. Preview and edit it in the document panel.")
                st.rerun()
            else:
                st.session_state["mode"] = "Fill Drive Template"
                workflow_status.update(label="Loading Drive template", state="running")
                loader = get_tool("drive_template_loader")
                template_html = loader.invoke({"source": prompt.strip()})
                placeholders = extract_placeholders(template_html)
                st.session_state["drive_template_html"] = template_html
                st.session_state["drive_placeholders"] = placeholders
                workflow_status.update(label="Template loaded", state="complete")
                if placeholders:
                    st.session_state["chat_messages"].append(
                        {
                            "role": "assistant",
                            "content": f"Template loaded. I found {len(placeholders)} fields. Fill them in the document panel, then generate the completed PDF.",
                        }
                    )
                else:
                    st.session_state["chat_messages"].append(
                        {
                            "role": "assistant",
                            "content": "Template loaded, but I could not find fillable fields.",
                        }
                    )
                st.rerun()
        except Exception as exc:
            workflow_status.update(label="Workflow failed", state="error")
            st.session_state["chat_messages"].append({"role": "assistant", "content": f"Error: {exc}"})
            st.rerun()

with right:
    header_col, download_col = st.columns([0.58, 0.42])
    with header_col:
        st.subheader("Document Panel")
    with download_col:
        result = st.session_state.get("last_result")
        if result and result.get("pdf_path") and Path(result["pdf_path"]).exists():
            pdf_path = Path(result["pdf_path"])
            st.download_button(
                "Download PDF",
                data=pdf_path.read_bytes(),
                file_name=pdf_path.name,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    if st.session_state["mode"] == "Fill Drive Template":
        placeholders = st.session_state.get("drive_placeholders", [])
        if placeholders:
            st.markdown("**Template Fields**")
            fill_values = {}
            for placeholder in placeholders:
                label = placeholder.replace("_", " ").title()
                fill_values[placeholder] = st.text_input(label, key=f"fill_{placeholder}")

            if st.button("Generate Filled PDF", type="primary", use_container_width=True):
                missing = [key for key, value in fill_values.items() if not value.strip()]
                if missing:
                    st.error("Fill all fields first.")
                else:
                    try:
                        workflow_status.update(label="Filling template", state="running")
                        result = run_template_fill_workflow(
                            st.session_state["drive_template_html"],
                            fill_values,
                            progress_callback=update_progress,
                        )
                        workflow_status.update(label="Filled PDF generated", state="complete")
                        store_result(result, "Filled the Drive template and generated the PDF.")
                        st.rerun()
                    except Exception as exc:
                        workflow_status.update(label="Template fill failed", state="error")
                        st.error(str(exc))
        else:
            st.info("Paste a Drive or Docs template link in chat to load fillable fields.")

    st.markdown("**Preview**")
    editor_value = st.session_state.get("editor_html", "")
    if editor_value.strip():
        components.html(build_preview_html(editor_value), height=790, scrolling=False)
    else:
        st.info("Generated document preview will appear here.")

    with st.expander("Edit visible text", expanded=False):
        find_text = st.text_area("Text to replace", height=90)
        replacement_text = st.text_area("Replacement text", height=90)
        if st.button("Apply Text Edit", use_container_width=True, disabled=not editor_value.strip()):
            st.session_state["editor_html"] = replace_first_text(editor_value, find_text, replacement_text)
            st.rerun()

    with st.expander("Advanced HTML", expanded=False):
        editor_value = st.text_area(
            "HTML editor",
            value=st.session_state.get("editor_html", ""),
            height=260,
            label_visibility="collapsed",
        )
        st.session_state["editor_html"] = editor_value

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Regenerate PDF From Edits", use_container_width=True, disabled=not editor_value.strip()):
            try:
                storage = get_tool("document_storage")
                pdf_generator = get_tool("pdf_generator")
                html_path = storage.invoke({"html_content": editor_value})
                pdf_path = pdf_generator.invoke({"html_content": editor_value})
                result = {
                    "html_content": editor_value,
                    "html_path": html_path,
                    "pdf_path": pdf_path,
                    "messages": ["Manual editor saved HTML.", "PDF Tool regenerated edited PDF."],
                }
                store_result(result, "Regenerated the PDF from your edits.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with c2:
        if st.button("Clear Workspace", use_container_width=True):
            for key in ["last_result", "editor_html", "drive_template_html", "drive_placeholders", "workflow_messages"]:
                st.session_state[key] = "" if key != "drive_placeholders" else []
            st.session_state["chat_messages"] = [
                {"role": "assistant", "content": "Workspace cleared. Send a new request when ready."}
            ]
            st.rerun()

    if st.session_state.get("workflow_messages"):
        with st.expander("Workflow Trace", expanded=False):
            for item in st.session_state["workflow_messages"]:
                st.write(f"- {item}")

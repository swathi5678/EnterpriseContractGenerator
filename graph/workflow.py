import logging
import os
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from agents.compliance import compliance_agent
from agents.formatter import formatter_agent
from agents.planner import planner_agent
from agents.supervisor import supervisor_agent
from agents.template_filler import fill_template_agent
from agents.writer import legal_writer_agent
from tools.registry import get_tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
load_dotenv(PROJECT_ROOT / ".env")


class ContractState(TypedDict, total=False):
    user_prompt: str
    llm: Any
    current_agent: str
    messages: list[str]
    outline: str
    draft: str
    final_contract: str
    compliance_report: str
    html_content: str
    html_path: str
    pdf_path: str
    template_html: str
    fill_values: dict[str, str]


def pdf_tool_node(state: ContractState) -> ContractState:
    logging.info("PDF Tool running")
    pdf_generator = get_tool("pdf_generator")
    state["pdf_path"] = pdf_generator.invoke({"html_content": state["html_content"]})
    state.setdefault("messages", []).append("PDF Tool generated the final PDF.")
    state["current_agent"] = "PDF Tool"
    return state


def build_workflow():
    graph = StateGraph(ContractState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("planner", planner_agent)
    graph.add_node("writer", legal_writer_agent)
    graph.add_node("compliance", compliance_agent)
    graph.add_node("formatter", formatter_agent)
    graph.add_node("pdf_tool", pdf_tool_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "planner")
    graph.add_edge("planner", "writer")
    graph.add_edge("writer", "compliance")
    graph.add_edge("compliance", "formatter")
    graph.add_edge("formatter", "pdf_tool")
    graph.add_edge("pdf_tool", END)
    return graph.compile()


def build_template_fill_workflow():
    graph = StateGraph(ContractState)
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("template_filler", fill_template_agent)
    graph.add_node("pdf_tool", pdf_tool_node)

    graph.set_entry_point("supervisor")
    graph.add_edge("supervisor", "template_filler")
    graph.add_edge("template_filler", "pdf_tool")
    graph.add_edge("pdf_tool", END)
    return graph.compile()


def run_contract_workflow(user_prompt: str, progress_callback=None) -> ContractState:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    llm = ChatGoogleGenerativeAI(model=model, temperature=0.25)
    app = build_workflow()
    state: ContractState = {"user_prompt": user_prompt, "llm": llm, "messages": []}
    final_state = state

    for step in app.stream(state):
        node_name, node_state = next(iter(step.items()))
        final_state = node_state
        message = f"{node_name.replace('_', ' ').title()} completed"
        logging.info(message)
        if progress_callback:
            progress_callback(message, node_state.get("messages", []))
    return final_state


def run_template_fill_workflow(template_html: str, fill_values: dict[str, str], progress_callback=None) -> ContractState:
    app = build_template_fill_workflow()
    state: ContractState = {
        "user_prompt": "Fill confirmed Google Drive template",
        "template_html": template_html,
        "fill_values": fill_values,
        "messages": [],
    }
    final_state = state

    for step in app.stream(state):
        node_name, node_state = next(iter(step.items()))
        final_state = node_state
        message = f"{node_name.replace('_', ' ').title()} completed"
        logging.info(message)
        if progress_callback:
            progress_callback(message, node_state.get("messages", []))
    return final_state

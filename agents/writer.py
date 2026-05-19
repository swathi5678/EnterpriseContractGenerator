import logging

from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


def legal_writer_agent(state: dict) -> dict:
    logger.info("Legal Writer Agent running")
    llm = state["llm"]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior enterprise legal drafting agent. Draft a professional NDA in polished legal prose. Include Introduction, Confidentiality, Obligations, Termination, Governing Law, and Signatures.",
            ),
            ("human", "Request: {user_prompt}\n\nOutline:\n{outline}"),
        ]
    )
    response = (prompt | llm).invoke(
        {"user_prompt": state["user_prompt"], "outline": state["outline"]}
    )
    state["draft"] = response.content
    state["current_agent"] = "Legal Writer"
    state.setdefault("messages", []).append("Legal Writer drafted NDA clauses.")
    return state


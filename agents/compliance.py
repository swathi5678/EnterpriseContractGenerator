import logging

from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)
REQUIRED_SECTIONS = ["Introduction", "Confidentiality", "Obligations", "Termination", "Governing Law", "Signatures"]


def compliance_agent(state: dict) -> dict:
    logger.info("Compliance Agent running")
    llm = state["llm"]
    missing = [s for s in REQUIRED_SECTIONS if s.lower() not in state["draft"].lower()]
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a contract compliance reviewer. Return a corrected final NDA that is complete, professional, consistently formatted, and includes every required section.",
            ),
            ("human", "Missing sections detected: {missing}\n\nDraft:\n{draft}"),
        ]
    )
    response = (prompt | llm).invoke({"missing": ", ".join(missing) or "None", "draft": state["draft"]})
    state["final_contract"] = response.content
    state["compliance_report"] = "Checked required sections, tone, and formatting consistency."
    state["current_agent"] = "Compliance"
    state.setdefault("messages", []).append("Compliance reviewed and finalized the contract text.")
    return state


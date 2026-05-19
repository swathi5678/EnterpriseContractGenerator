import logging

from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


def planner_agent(state: dict) -> dict:
    logger.info("Planner Agent running")
    llm = state["llm"]
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are an enterprise contract planning agent. Produce a concise structured NDA outline with required sections."),
            ("human", "User request: {user_prompt}"),
        ]
    )
    response = (prompt | llm).invoke({"user_prompt": state["user_prompt"]})
    state["outline"] = response.content
    state["current_agent"] = "Planner"
    state.setdefault("messages", []).append("Planner created the contract outline.")
    return state


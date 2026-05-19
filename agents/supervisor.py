import logging


logger = logging.getLogger(__name__)


def supervisor_agent(state: dict) -> dict:
    logger.info("Supervisor Agent running")
    state["current_agent"] = "Supervisor"
    state.setdefault("messages", []).append("Supervisor routed the contract request.")
    return state


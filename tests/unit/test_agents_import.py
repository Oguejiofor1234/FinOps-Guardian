from google.adk.agents import Agent
from google.adk.workflow import Workflow

from agents import analyst_agent, auditor_agent, root_agent


def test_agents_importable() -> None:
    """Verifies that all FinOps Guardian agents can be successfully imported and are instances of correct ADK classes."""
    assert isinstance(root_agent, Workflow)
    assert isinstance(auditor_agent, Agent)
    assert isinstance(analyst_agent, Agent)

    assert root_agent.name == "root_compliance_agent"
    assert auditor_agent.name == "auditor_agent"
    assert analyst_agent.name == "analyst_agent"

from google.adk.apps import App

from workflows.finops_workflow import finops_workflow

root_agent = finops_workflow

# Expose compliance orchestrator workflow as the root agent
app = App(
    root_agent=root_agent,
    name="app",
)

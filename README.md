# 🛡️ FinOps Guardian

FinOps Guardian is an intelligent corporate expense compliance system. It acts as an automated agent-driven gatekeeper, checking every submitted corporate expense claim against policies, redacting Personally Identifiable Information (PII), flagging security risks, mapping expense items to tax codes, and committing verified records to an ERP database ledger.

---

## 🏛️ 1. Project Directory Structure

```
finops-guardian/
├── app/                        # Main application logic
│   ├── __init__.py             # Exposes the App object
│   ├── agent.py                # Defines LLM Agents and the Workflow graph
│   ├── fast_api_app.py         # FastAPI backend server
│   ├── app_utils/              # Internal utilities (A2A protocol, logging)
│   ├── guardrails/             # Security filters (PII, Prompt Injection)
│   │   ├── __init__.py
│   │   ├── pii_shield.py       # Scans and redacts credit cards and SSNs
│   │   └── injection_shield.py # Blocks prompt injection attacks
│   ├── skills/                 # Guidelines and rules teaching agents how to audit & map
│   │   ├── __init__.py         # Helper to load policy rules into prompt context
│   │   └── expense_policy.md   # Mathematical boundaries & tax mapping rules
│   ├── mcp_servers/            # Model Context Protocol (MCP) server mock tools
│   │   ├── __init__.py
│   │   └── db_mcp.py           # Mock PostgreSQL ERP ledger writes & Slack notification tool
│   └── static/                 # Web dashboard UI files (HTML, CSS, JS)
│       ├── index.html          # Interactive executive dashboard
│       ├── style.css           # Premium dark mode glassmorphic styling
│       └── main.js             # Form submittals & WebSocket simulation scripts
├── tests/                      # Testing directory
│   ├── unit/                   # Deterministic python tests (guardrails, limits)
│   │   ├── test_dummy.py
│   │   └── test_guardrails.py  # Verifies PII & injection shields
│   ├── integration/            # Multi-agent connection and workflow test suites
│   │   ├── test_agent.py
│   │   └── test_server_e2e.py
│   └── eval/                   # ADK Quality evaluation framework
│       ├── eval_config.yaml    # Evaluation configuration and metrics list
│       ├── metrics.py          # Custom LLM-as-judge scoring class
│       └── datasets/
│           ├── basic-dataset.json
│           └── finops-dataset.json # Mock claims (normal, high risk, jailbreak attempts)
├── Dockerfile                  # Packaging instructions for container hosting (Cloud Run/GKE)
├── pyproject.toml              # Project dependencies configuration (uv based)
├── GEMINI.md                   # AI-assisted development instructions
└── README.md                   # This project guide
```

---

## 📁 2. Folder Explanations

- **`app/`**: Root folder of the python codebase. Initiates the ADK runner and exposes serving routing.
  - **`app/guardrails/`**: Holds deterministic modules to filter inputs. This sanitizes user queries before reaching LLM models to prevent PII leakage (credit cards, SSNs) and hijack commands.
  - **`app/skills/`**: Stores markdown documents and prompt directives containing corporate rules. The agent reads this context to evaluate limits, weekends, receipts, and map expense types to tax codes.
  - **`app/mcp_servers/`**: Contains Model Context Protocol (MCP) integrations. In this system, this represents tools that write to a PostgreSQL ERP ledger and post success/alert alerts to Slack/Email.
  - **`app/static/`**: Houses the rich user interface. A dashboard displaying audited claim metrics, a dropzone submission form, a live agent trace stream, and a manager queue (Human-in-the-loop).
- **`tests/unit/`**: Verifies deterministic, non-AI logic (e.g. math checks, regex scrubs).
- **`tests/integration/`**: Verifies Python server routes, database linkages, and full multi-agent flows.
- **`tests/eval/`**: The Core Quality gate. Runs evaluations across testing scenarios and scores responses using an LLM-as-judge to verify agent compliance, hallucination flags, and task success.

---

## 🛠️ 3. How `uvx google-agents-cli setup` Supports the Project

Running the `uvx google-agents-cli setup` command sets up the local developer system with Google's **Agent Development Kit (ADK)** environment:

1. **Authentication Configuration**: It configures local Application Default Credentials (ADC) to safely query Vertex AI models under your active Google Cloud identity.
2. **Global & Project-Local Skills**: It downloads and links seven (7) standardized development skills into your agent folder:
   - `google-agents-cli-workflow`: Overall lifecycle guidelines (Phase 0-7).
   - `google-agents-cli-scaffold`: Commands to set up base project parameters.
   - `google-agents-cli-adk-code`: SDK design patterns, callbacks, and memory bank templates.
   - `google-agents-cli-eval`: Standard dataset schemas, LLM-judge rubrics, and optimization cycles.
   - `google-agents-cli-deploy`: GCP deployment target details (Agent Runtime, Cloud Run, GKE).
   - `google-agents-cli-publish`: Integration procedures for Gemini Enterprise.
   - `google-agents-cli-observability`: Prompt logging and tracing setups.
3. **Automatic Dependency Locking**: Sets up the `uv` toolchain to run virtual environment scripts synchronously, ensuring high-speed packages ingestion.

---

## ⚡ 4. Quick Start (Running Locally)

### Prerequisites
Make sure you have `uv` installed. If not, install it using the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/index.md).

### 1. Install Project Dependencies
Run from the workspace directory:
```bash
agents-cli install
```

### 2. Run Unit Tests
Verify the deterministic guardrails and dummy components:
```bash
uv run pytest tests/unit
```

### 3. Run Agent Evaluations
Execute the evaluation loop against the custom FinOps claims dataset:
```bash
agents-cli eval run --dataset tests/eval/datasets/finops-dataset.json --config tests/eval/eval_config.yaml
```
Evaluation traces will save to `artifacts/traces/`, and scored grading results will save to `artifacts/grade_results/results_<timestamp>.html`. Open the HTML file in any browser to inspect the LLM judge's scorecard.

### 4. Start the Agent Playground
Interact with the agent or view the API spec locally:
```bash
agents-cli playground
```
This boots up a local web server (defaults to port `18080`) providing a web UI to test user messages. You can also view the static compliance dashboard by navigating to `http://localhost:8000/static/index.html` once the FastAPI backend is running.

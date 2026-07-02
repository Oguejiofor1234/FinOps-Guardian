# Study Notes: FinOps Guardian Project Architecture

Welcome to your comprehensive study guide for the **FinOps Guardian** project. This document explains the full architecture, components, workflows, and testing plans of this intelligent corporate expense compliance system in a beginner-friendly manner.

---

## 🏛️ 1. System Architecture Explanation

The FinOps Guardian is an automated, AI-driven corporate compliance system. It acts as an intelligent gatekeeper, checking every submitted expense claim against policies, redacting personal data, flagging security risks, mapping items to tax codes, and committing the records to an ERP database ledger.

### The System Layers:
1. **Users:** Employees (submitters), Managers (approvers/reviewers), and Finance Admins (auditors).
2. **Frontend (Dashboard):** A web portal where employees submit receipts and managers view charts, metrics (Total Spend, Approved/Rejected claims, Risk ratios), and pending approvals.
3. **FastAPI Backend:** The server coordinating backend operations. It handles API requests, validates users, manages receipt uploads, and streams real-time logs to the frontend via WebSockets.
4. **ADK Orchestration Layer (Multi-Agent System):** The core intelligence brain containing three specialized AI agents (Root, Auditor, and Analyst) cooperating in a structured pipeline.
5. **Model Context Protocol (MCP) Servers:** Lightweight external tools connecting the AI agents directly to PostgreSQL database ledgers and Slack/Email alert systems.
6. **Data & Infrastructure Layer:** Employs Redis for caching, PostgreSQL for operational logs, directories for storing scanned receipt uploads, and Secret Manager for secure storage of keys.

---

## 🔄 2. Workflow Explanation

When an employee submits an expense claim (e.g., a taxi ride, dinner, or software purchase), the system processes it through a sequential pipeline:

```
[Expense Ingestion]
       │
       ▼
[PII & Injection Guardrails]  ──(Flagged Malicious)──► [Manager HITL Portal]
       │                                                      │
    (Clean)                                                (Rejected)
       │                                                      │
       ▼                                                      ▼
[Policy & Duplicate Auditor]  ──(High Risk/Audit Alert)──► [Notification MCP]
       │                                                      │
  (Low Risk)                                                  ▼
       │                                                 [End Session]
       ▼
[Analyst & Tax Mapper Agent]
       │
       ▼
[PostgreSQL ERP Ledger Write]
       │
       ▼
[Slack / Email Notification Alerts]
```

1. **Submission:** An employee fills in the submission form.
2. **Ingestion & Guardrails:** The text is scanned. Credit card details are redacted, and prompt injections are blocked.
3. **Routing:** Clear claims proceed to policy checks; malicious attempts route directly to the manager.
4. **Policy Audit:** The claims are audited against mathematical rules (limits, weekends, receipts). Flagged claims go to the manager's queue.
5. **Human Approval (HITL):** The manager approves or rejects flagged claims.
6. **Accounting Analysis:** Approved claims are classified for tax deductibility by the analyst.
7. **Database Commit:** The claim is written to the ERP database.
8. **Notification:** Success notifications are posted to Slack.

---

## 🕸️ 3. Workflow Graph Explanation

The workflow is constructed as a **directed graph** using the ADK 2.0 Graph API:
* **Nodes:** Steps in the pipeline. Nodes can be Python functions (guardrails), LLM agents (analyst), or tools (MCP writes).
* **Edges:** Connections representing the control path. Edges can be *unconditional* (always follow the arrow) or *conditional* (route path depends on output values like `"CLEAN"`, `"FLAGGED_RISK"`, `"APPROVED"`, or `"REJECTED"`).
* **START & END:** The workflow entry and exit points.

---

## 📁 4. Project Folder Structure

The project directory follows the recommended template from `agents-cli`:

```
spend_sentinel/
├── app/                        # Main application logic
│   ├── __init__.py             # Exposes the App object
│   ├── agent.py                # Defines LLM Agents and the Workflow graph
│   ├── guardrails/             # Security filters (PII, Prompt Injection)
│   ├── skills/                 # Guidelines teaching agents how to parse & map
│   ├── mcp_servers/            # MCP PostgreSQL & Notification servers
│   ├── static/                 # Web dashboard UI files (HTML, CSS, JS)
│   └── fast_api_app.py         # FastAPI backend server
├── tests/                      # Testing directory
│   ├── unit/                   # Tests for deterministic python code
│   └── integration/            # Multi-agent connection tests
├── evals/                      # ADK Quality evaluation framework
│   ├── eval_config.yaml        # Evaluation thresholds & metrics
│   └── datasets/               # Mock dataset claims
├── pyproject.toml              # Project dependencies configuration
├── Dockerfile                  # Packaging instructions for container hosting
└── README.md                   # Setup and usage guide
```

---

## 🛠️ 5. Technologies to Use

* **Google Antigravity ADK 2.0:** The primary library for agent declaration and workflow graph construction.
* **FastAPI:** A high-performance Python web framework for exposing REST API endpoints and WebSocket streams.
* **Uvicorn:** The ASGI web server hosting FastAPI.
* **PostgreSQL:** The core operational relational database and simulated ERP backend.
* **Redis:** In-memory key-value database for caching sessions.
* **Model Context Protocol (MCP):** The open standard protocol allowing agents to communicate with database tools.
* **Pydantic:** Data validation library used to enforce input and output JSON shapes.
* **uv:** Fast Python package installer and virtual environment runner.
* **Docker:** Packaging application code into lightweight server containers.

---

## 📖 6. Beginner-Friendly Glossary

* **Agent (AI Agent):** An intelligent, LLM-powered assistant configured with specific instructions, schemas, and tools to act autonomously on tasks.
* **ADK (Agent Development Kit):** A Python SDK built by Google to define, structure, run, and orchestrate AI agents and workflows.
* **MCP (Model Context Protocol):** A standard that lets AI systems securely connect with local/remote data sources, databases, and APIs.
* **Guardrail:** A security layer acting as a shield to sanitize inputs and filter out hacking attempts before they reach the main AI models.
* **PII (Personally Identifiable Information):** Private data (SSNs, credit card numbers, email addresses) that must be redacted to protect privacy.
* **Prompt Injection:** An attack where a user inputs commands attempting to hijack or override the system instructions of an AI model.
* **HITL (Human-in-the-Loop):** A design pattern that pauses autonomous AI workflows to wait for manual human approval or input.
* **Observability:** Logging, tracing, and monitoring tools that help developers inspect how systems execute and see what agents are thinking in real time.
* **Evaluation (Eval):** Systematic testing of non-deterministic AI models using a "judge" model to grade outputs on accuracy, safety, and compliance.

---

## 🧪 7. Testing Plan

We verify system behavior in three distinct ways:

1. **Unit Testing (Pytest):** Tests the deterministic python modules (PII regex scrubbing, prompt injection regex matches, and threshold limit mathematics) to guarantee core code correctness.
2. **Integration & End-to-End Testing:** Verifies that API endpoints correctly receive JSON inputs, trigger workflow graph runs, process states, and save data records to the ERP tables.
3. **ADK Evaluation System:** Evaluates LLM agent responses. It runs a mock dataset of test claims (including weekend claims, missing receipts, and jailbreak attempts) and uses an LLM judge to grade accuracy and verify safety gates.

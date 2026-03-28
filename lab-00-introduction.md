# Lab 00 — Introduction to the Microsoft Agent Framework Workshop

## Welcome

This hands-on workshop takes you from building your first AI agent to orchestrating sophisticated multi-agent systems — all using the **Microsoft Agent Framework** and Python. By the end, you'll have built and deployed a production-ready multi-agent web application on Azure.

---

## What is Microsoft Agent Framework?

Microsoft Agent Framework is an open-source SDK that unifies the best of **AutoGen** (simple agent abstractions, multi-agent patterns) and **Semantic Kernel** (enterprise-grade session management, type safety, middleware, telemetry) into a single, next-generation framework.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Microsoft Agent Framework                        │
│                                                                     │
│  ┌──────────────────────┐     ┌──────────────────────────────────┐  │
│  │       AutoGen         │ +   │       Semantic Kernel            │  │
│  │  Simple abstractions  │     │  Enterprise features             │  │
│  │  Multi-agent patterns │     │  Session mgmt, type safety       │  │
│  │  Conversational agents│     │  Middleware, telemetry            │  │
│  └──────────────────────┘     └──────────────────────────────────┘  │
│                                                                     │
│  NEW: Graph-based Workflows · Explicit multi-agent orchestration   │
│       Checkpointing · Human-in-the-loop · MCP integration          │
└─────────────────────────────────────────────────────────────────────┘
```

**Key capabilities:**

| Category | Description |
|----------|-------------|
| **Agents** | Individual agents that use LLMs to process inputs, call tools and MCP servers, and generate responses. Supports Azure OpenAI, OpenAI, Anthropic, Ollama, and more. |
| **Workflows** | Graph-based workflows that connect agents and functions for multi-step tasks with type-safe routing, checkpointing, and human-in-the-loop support. |

---

## Agents vs Workflows — When to Use What

| Use an **Agent** when… | Use a **Workflow** when… |
|------------------------|--------------------------|
| The task is open-ended or conversational | The process has well-defined steps |
| You need autonomous tool use and planning | You need explicit control over execution order |
| A single LLM call (possibly with tools) suffices | Multiple agents or functions must coordinate |

> **Rule of thumb:** If you can write a function to handle the task, do that instead of using an AI agent.

---

## Workshop Architecture — The 5 Orchestration Patterns

This workshop covers all five multi-agent orchestration patterns from the [Azure Architecture Guide](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns):

```
                        Multi-Agent Orchestration Patterns
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │  1. SEQUENTIAL           2. CONCURRENT                     │
    │  ┌───┐ ┌───┐ ┌───┐     ┌───┐                              │
    │  │ A ├─► B ├─► C │     │ A │──┐                            │
    │  └───┘ └───┘ └───┘     ├───┤  ├──► Aggregator              │
    │  Pipeline flow          │ B │──┘                            │
    │                         ├───┤                               │
    │                         │ C │──┘                            │
    │                         └───┘                               │
    │  3. HANDOFF              4. GROUP CHAT                      │
    │  ┌───┐    ┌───┐         ┌─────────────┐                    │
    │  │ A ├───►│ B │         │ Orchestrator │                    │
    │  └───┘    └─┬─┘         └──────┬──────┘                    │
    │         ┌───▼───┐        ┌─────┼─────┐                     │
    │         │   C   │        │ A   │ B   │  Shared thread       │
    │         └───────┘        └─────┼─────┘                     │
    │  Dynamic delegation            │ C                          │
    │                                                             │
    │  5. MAGENTIC                                                │
    │  ┌──────────┐ Task Ledger                                   │
    │  │ Manager  ├──────────────┐                                │
    │  └────┬─────┘              │                                │
    │   ┌───┼───┐          ┌────▼────┐                            │
    │   │ A │ B │ C        │ Progress │                           │
    │   └───┴───┘          │ Tracking │                           │
    │  Dynamic planning    └─────────┘                            │
    └─────────────────────────────────────────────────────────────┘
```

---

## Workshop Labs at a Glance

| Lab | Title | Key Concept |
|-----|-------|-------------|
| **00** | Introduction (this lab) | Workshop overview and setup |
| **01** | Your First Agent | Single agent, prompt → response, streaming |
| **02** | Function Tools | Extending agents with custom Python tools |
| **03** | MCP Tools Integration | Microsoft Learn MCP server, MCP protocol |
| **04** | Multi-Turn Conversations | Session management, conversation memory |
| **05** | Agent as Tool | Composing agents — one agent calls another |
| **06** | Sequential Orchestration | Pipeline pattern — agents in series |
| **07** | Concurrent Orchestration | Fan-out/fan-in — agents in parallel |
| **08** | Handoff Orchestration | Dynamic delegation between agents |
| **09** | Group Chat Orchestration | Collaborative debate with speaker selection |
| **10** | Magentic Orchestration | Dynamic planning with task ledger |
| **11** | Multi-Agent Web App | CopilotKit + AG-UI beautiful chat interface |
| **12** | Deploy to Azure | Azure Container Apps deployment |

---

## Prerequisites

Before you begin, ensure you have the following installed and configured:

### Software

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11 or higher | Runtime for all labs |
| **Azure CLI** | Latest | Authentication to Azure |
| **VS Code** | Latest | IDE (recommended) |
| **Node.js** | 18 or higher | Required for Lab 11 (CopilotKit frontend) |
| **Git** | Latest | Version control |

### Azure Access

You must be authenticated to Azure. Verify by running:

```bash
az login
az account show
```

### Model Endpoint

This workshop uses a GPT model already deployed in **Microsoft Foundry**:

| Setting | Value |
|---------|-------|
| **Endpoint** | `https://letsaifoundryprj-resource.openai.azure.com` |
| **Deployment Name** | `gpt-5.2` |
| **Authentication** | `DefaultAzureCredential` (Azure CLI) |

---

## Environment Setup Template

Every lab in this workshop is **standalone** — each has its own virtual environment and dependencies. Here's the common pattern you'll follow:

### 1. Create a `.env` file

Create a `.env` file in the lab directory (or at the workshop root and copy it):

```env
AZURE_OPENAI_ENDPOINT=https://letsaifoundryprj-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

### 2. Create a virtual environment

```bash
# Navigate to the lab directory
cd labXX

# Create a virtual environment
python -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the lab

```bash
python main.py
```

---

## How Authentication Works

This workshop uses `DefaultAzureCredential` from the `azure-identity` package. Since you've already authenticated via Azure CLI (`az login`), the credential chain automatically picks up your session:

```python
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
```

`DefaultAzureCredential` tries multiple authentication methods in order:
1. Environment variables
2. Managed Identity (when deployed to Azure)
3. Azure CLI (`az login`) ← **this is what we use locally**
4. Azure PowerShell
5. Interactive browser

This means the same code works both locally (using your CLI session) and in Azure (using Managed Identity) — no code changes needed for deployment.

---

## Reference Documentation

- [Microsoft Agent Framework Overview](https://learn.microsoft.com/en-us/agent-framework/overview/?pivots=programming-language-python)
- [AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Agent Framework GitHub Repository](https://github.com/microsoft/agent-framework)
- [AG-UI Protocol](https://docs.ag-ui.com/introduction)
- [CopilotKit Documentation](https://docs.copilotkit.ai/)

---

## Next Lab

Ready to build your first agent? Head to **[Lab 01 — Your First Agent](lab-01-first-agent.md)**.

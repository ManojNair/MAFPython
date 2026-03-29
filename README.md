# LetsMAFAgents — Microsoft Agent Framework Workshop

A hands-on workshop that takes you from building your first AI agent to orchestrating sophisticated multi-agent systems using the **Microsoft Agent Framework** and Python.

## What is Microsoft Agent Framework?

Microsoft Agent Framework is an open-source SDK that unifies **AutoGen** (simple agent abstractions, multi-agent patterns) and **Semantic Kernel** (enterprise-grade session management, type safety, middleware, telemetry) into a single, next-generation framework. It supports graph-based workflows, explicit multi-agent orchestration, checkpointing, human-in-the-loop, and MCP integration.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.11+ | Runtime for all labs |
| **Azure CLI** | Latest | Authentication to Azure |
| **VS Code** | Latest | IDE (recommended) |

| **Git** | Latest | Version control |

You must be authenticated to Azure (`az login`) with access to an Azure OpenAI deployment.

## Labs

| Lab | Title | Description | Key Concepts |
|-----|-------|-------------|--------------|
| [00](lab-00-introduction.md) | **Introduction** | Workshop overview, setup instructions, and architecture guide | Microsoft Agent Framework, orchestration patterns overview |
| [01](lab-01-first-agent.md) | **Your First Agent** | Build a single agent that answers questions with streaming support | `AzureOpenAIResponsesClient`, `agent.run()`, streaming responses |
| [02](lab-02-function-tools.md) | **Function Tools** | Extend agents with custom Python functions for real-world capabilities | `@tool` decorator, Annotated types, class-based tools, `FunctionInvocationContext` |
| [03](lab-03-mcp-tools.md) | **MCP Tools Integration** | Connect to external tool servers using the Model Context Protocol | `MCPStreamableHTTPTool`, `MCPStdioTool`, Microsoft Learn MCP server |
| [04](lab-04-multi-turn-conversations.md) | **Multi-Turn Conversations** | Give agents conversation memory using sessions | `AgentSession`, session serialization/restoration, multiple independent sessions |
| [05](lab-05-agent-as-tool.md) | **Agent as Tool** | Compose agents by using one agent as a tool for another | `.as_tool()`, hierarchical agent systems, concierge pattern |
| [06](lab-06-sequential-orchestration.md) | **Sequential Orchestration** | Pipeline pattern — agents execute in series, each building on previous output | `SequentialBuilder`, blog post pipeline (Researcher → Writer → Editor → SEO) |
| [07](lab-07-concurrent-orchestration.md) | **Concurrent Orchestration** | Fan-out/fan-in — agents run in parallel and results are aggregated | `ConcurrentBuilder`, investment analysis with specialist agents, custom aggregator |
| [08](lab-08-handoff-orchestration.md) | **Handoff Orchestration** | Dynamic delegation — agents transfer control based on conversation context | `HandoffBuilder`, customer support system, tool approval (HITL), autonomous mode |
| [09](lab-09-group-chat-orchestration.md) | **Group Chat Orchestration** | Collaborative debate with centralized speaker selection | `GroupChatBuilder`, round-robin & LLM-based selection, shared conversation thread |
| [10](lab-10-magentic-orchestration.md) | **Magentic Orchestration** | Dynamic planning with a manager agent, task ledger, and progress tracking | `MagenticBuilder`, adaptive planning, stall detection, human-in-the-loop plan review |

## Project Structure

```
├── lab-XX-*.md          # Lab instructions (read these!)
├── labXX/
│   ├── main.py          # Lab source code
│   └── requirements.txt # Python dependencies

```

## Getting Started

1. Clone this repository
2. Authenticate with Azure:
   ```bash
   az login
   ```
3. Create a `.env` file with your Azure OpenAI credentials:
   ```env
   AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
   AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment>
   ```
4. Start with [Lab 00 — Introduction](lab-00-introduction.md), then work through each lab sequentially:
   ```bash
   cd lab01
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```

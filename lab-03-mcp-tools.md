# Lab 03 — MCP Tools Integration

## Objective

Connect your agent to external tool servers using the **Model Context Protocol (MCP)**. You'll integrate the **Microsoft Learn MCP server** to give your agent the ability to search and retrieve Azure documentation in real-time, and learn to expose your own agents as MCP servers.

---

## Concepts

### What is MCP (Model Context Protocol)?

MCP is an **open standard** that defines how applications provide tools and contextual data to LLMs. Think of it as a universal adapter — instead of writing custom integration code for every external service, MCP provides a consistent interface.

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Architecture                             │
│                                                                 │
│  ┌──────────────┐    MCP Protocol     ┌──────────────────────┐  │
│  │    Agent      │◄──────────────────►│   MCP Server         │  │
│  │  (MCP Client) │   tool discovery   │  (Microsoft Learn,   │  │
│  │              │   tool invocation    │   Calculator, etc.)  │  │
│  └──────────────┘                     └──────────────────────┘  │
│                                                                 │
│  Transport options:                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  stdio   │  │  HTTP/   │  │ WebSocket│                      │
│  │ (local)  │  │  SSE     │  │          │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Tool Types in Agent Framework

| Tool Class | Transport | Use Case |
|-----------|-----------|----------|
| `MCPStdioTool` | Standard I/O | Local MCP servers running as child processes |
| `MCPStreamableHTTPTool` | HTTP/SSE | Remote MCP servers accessible over the network |
| `MCPWebsocketTool` | WebSocket | Real-time bidirectional MCP servers |

### Microsoft Learn MCP Server

Microsoft provides an MCP server at `https://learn.microsoft.com/api/mcp` that gives agents access to **search and retrieve Microsoft documentation**. This is a perfect example of a remote HTTP-based MCP server.

---

## Setup

```bash
mkdir -p lab03 && cd lab03
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### `requirements.txt`

```txt
agent-framework --pre
azure-identity
python-dotenv
```

### `.env`

```env
AZURE_OPENAI_ENDPOINT=https://letsaifoundryprj-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Code

Create `main.py`:

```python
"""
Lab 03 — MCP Tools Integration
Microsoft Agent Framework Workshop

Demonstrates:
  - MCPStreamableHTTPTool: Connect to Microsoft Learn MCP server (remote HTTP)
  - MCPStdioTool: Connect to a local calculator MCP server (stdio)
  - Combining MCP tools with function tools
  - Exposing an agent as an MCP server
"""

import asyncio
import os

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import Agent, MCPStreamableHTTPTool, MCPStdioTool
from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


async def demo_microsoft_learn_mcp():
    """
    Demo 1: Microsoft Learn MCP Server (HTTP/SSE)

    Connects to the Microsoft Learn MCP server at https://learn.microsoft.com/api/mcp
    to give the agent the ability to search and retrieve Azure documentation.
    """
    print("=" * 60)
    print("DEMO 1: Microsoft Learn MCP Server (HTTP/SSE)")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # MCPStreamableHTTPTool connects to remote MCP servers over HTTP with SSE.
    # The `async with` ensures proper connection lifecycle management.
    async with MCPStreamableHTTPTool(
        name="Microsoft Learn MCP",
        url="https://learn.microsoft.com/api/mcp",
    ) as learn_mcp:
        # Create an agent that uses the Microsoft Learn MCP tools
        agent = client.as_agent(
            name="DocsAssistant",
            instructions=(
                "You are a helpful Azure documentation assistant. "
                "Use the Microsoft Learn tools to search for and retrieve "
                "accurate, up-to-date documentation. Always cite the source "
                "URL when providing information from docs."
            ),
            tools=learn_mcp,
        )

        # Query 1: Search for Azure documentation
        print("\n--- Query 1: Azure Storage documentation ---")
        result = await agent.run(
            "How do I create an Azure Storage account using the Azure CLI?"
        )
        print(f"Agent: {result}\n")

        # Query 2: Another documentation search
        print("--- Query 2: Azure Functions documentation ---")
        result = await agent.run(
            "What are the different hosting plans for Azure Functions?"
        )
        print(f"Agent: {result}\n")


async def demo_local_mcp_calculator():
    """
    Demo 2: Local Calculator MCP Server (stdio)

    Connects to a local MCP server that provides mathematical computation tools.
    The server runs as a child process communicating via standard I/O.

    Prerequisites: Install uv (https://docs.astral.sh/uv/getting-started/installation/)
      curl -LsSf https://astral.sh/uv/install.sh | sh
    """
    print("=" * 60)
    print("DEMO 2: Local Calculator MCP Server (stdio)")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    # MCPStdioTool launches a local process and communicates via stdin/stdout.
    # "uvx" runs a Python package in an isolated environment (like npx for Python).
    async with MCPStdioTool(
        name="calculator",
        command="uvx",
        args=["mcp-server-calculator"],
    ) as calc_mcp:
        agent = client.as_agent(
            name="MathAgent",
            instructions=(
                "You are a precise math assistant. Use the calculator tools "
                "for all computations. Show your work step by step."
            ),
            tools=calc_mcp,
        )

        print("\n--- Query: Complex calculation ---")
        result = await agent.run(
            "What is (15 * 23) + (45 / 9) - (12 ^ 2)?"
        )
        print(f"Agent: {result}\n")


async def demo_combined_mcp_and_function_tools():
    """
    Demo 3: Combining MCP tools with custom function tools

    Shows how to use MCP tools alongside regular function tools,
    giving the agent both external and custom capabilities.
    """
    print("=" * 60)
    print("DEMO 3: Combined MCP + Function Tools")
    print("=" * 60)

    from typing import Annotated
    from pydantic import Field
    from agent_framework import tool

    # Custom function tool for internal knowledge
    @tool(description="Get the company's internal Azure architecture guidelines.")
    def get_internal_guidelines(
        topic: Annotated[str, Field(description="Topic to get guidelines for, e.g. 'storage', 'networking'")],
    ) -> str:
        """Get internal company guidelines."""
        guidelines = {
            "storage": (
                "Company Policy: Use Azure Blob Storage for unstructured data. "
                "Enable geo-redundant storage (GRS) for production. "
                "Use lifecycle management policies to tier data to Cool/Archive after 30/90 days."
            ),
            "networking": (
                "Company Policy: All production resources must be in a VNet. "
                "Use Private Endpoints for PaaS services. "
                "Hub-spoke topology with Azure Firewall in the hub."
            ),
        }
        return guidelines.get(
            topic.lower(),
            f"No specific internal guidelines found for '{topic}'. Check the company wiki."
        )

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    async with MCPStreamableHTTPTool(
        name="Microsoft Learn MCP",
        url="https://learn.microsoft.com/api/mcp",
    ) as learn_mcp:
        # Combine MCP tools with function tools in a single agent
        agent = client.as_agent(
            name="AzureAdvisor",
            instructions=(
                "You are an Azure architecture advisor. You have access to: "
                "1) Microsoft Learn documentation (via MCP) for official Azure guidance "
                "2) Internal company guidelines for org-specific policies. "
                "When answering, combine both official docs and internal policies. "
                "Always note which guidance comes from official docs vs internal policy."
            ),
            tools=[learn_mcp, get_internal_guidelines],
        )

        print("\n--- Query: Combining external docs + internal guidelines ---")
        result = await agent.run(
            "I need to set up Azure Storage for our production environment. "
            "What does Microsoft recommend, and what are our internal requirements?"
        )
        print(f"Agent: {result}\n")


async def demo_agent_as_mcp_server():
    """
    Demo 4: Expose an Agent as an MCP Server

    Shows how to turn an agent into an MCP server that other
    MCP clients (like VS Code Copilot) can discover and use.
    This demo shows the setup code — to actually serve it,
    you'd run it as a standalone process.
    """
    print("=" * 60)
    print("DEMO 4: Agent as MCP Server (Setup Example)")
    print("=" * 60)

    from agent_framework import tool as tool_decorator

    @tool_decorator(description="Get the restaurant's daily specials.")
    def get_specials() -> str:
        """Returns today's specials."""
        return (
            "Today's Specials:\n"
            "- Soup: French Onion\n"
            "- Salad: Mediterranean Quinoa\n"
            "- Entree: Grilled Salmon with Lemon Butter\n"
            "- Dessert: Tiramisu"
        )

    from typing import Annotated
    from pydantic import Field

    @tool_decorator(description="Get the restaurant's menu categories and items.")
    def get_menu(
        category: Annotated[str, Field(description="Menu category: appetizers, mains, desserts, drinks")] = "mains",
    ) -> str:
        """Get menu items by category."""
        menus = {
            "appetizers": "Bruschetta ($8), Calamari ($12), Soup of Day ($7)",
            "mains": "Grilled Salmon ($24), Ribeye Steak ($32), Pasta Primavera ($18)",
            "desserts": "Tiramisu ($10), Cheesecake ($9), Gelato ($7)",
            "drinks": "House Wine ($8), Craft Beer ($7), Espresso ($4)",
        }
        return menus.get(category.lower(), "Category not found. Try: appetizers, mains, desserts, drinks")

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    agent = client.as_agent(
        name="RestaurantAgent",
        description="Answer questions about the restaurant menu and specials.",
        instructions="You are a helpful restaurant assistant. Use the tools to provide accurate menu information.",
        tools=[get_specials, get_menu],
    )

    # Convert the agent to an MCP server
    mcp_server = agent.as_mcp_server()

    print("\nAgent has been converted to an MCP server!")
    print("To serve it via stdio (for VS Code, CLI tools, etc.), you would run:")
    print()
    print("  import anyio")
    print("  from mcp.server.stdio import stdio_server")
    print()
    print("  async def serve():")
    print("      async with stdio_server() as (read_stream, write_stream):")
    print("          await mcp_server.run(read_stream, write_stream,")
    print("                               mcp_server.create_initialization_options())")
    print()
    print("  anyio.run(serve)")
    print()
    print("Other MCP clients can then discover and use the agent's tools.")
    print(f"Server name: {agent.name}")
    print(f"Server description: {agent.description}")

    # You can still use the agent directly too
    print("\n--- Direct agent usage still works ---")
    result = await agent.run("What are today's specials and what desserts do you have?")
    print(f"Agent: {result}\n")


async def main():
    # Run each demo
    await demo_microsoft_learn_mcp()
    await demo_local_mcp_calculator()
    await demo_combined_mcp_and_function_tools()
    await demo_agent_as_mcp_server()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Run It

```bash
python main.py
```

> **Note:** Demo 2 (local calculator) requires `uv` to be installed. Install it with:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
> If `uv` is not available, that demo will show an error; the other demos will still work.

### Expected Output

```
============================================================
DEMO 1: Microsoft Learn MCP Server (HTTP/SSE)
============================================================

--- Query 1: Azure Storage documentation ---
Agent: To create an Azure Storage account using the Azure CLI, use the following command:

  az storage account create \
    --name <account-name> \
    --resource-group <resource-group> \
    --location <location> \
    --sku Standard_LRS

Source: https://learn.microsoft.com/en-us/azure/storage/common/storage-account-create

--- Query 2: Azure Functions documentation ---
Agent: Azure Functions offers three hosting plans:
1. **Consumption Plan** — Scale automatically, pay only for compute time used
2. **Premium Plan** — Pre-warmed instances, VNet connectivity, no cold start
3. **Dedicated (App Service) Plan** — Run on dedicated VMs with full control

Source: https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale

============================================================
DEMO 2: Local Calculator MCP Server (stdio)
============================================================

--- Query: Complex calculation ---
Agent: Let me break this down step by step:
- 15 × 23 = 345
- 45 ÷ 9 = 5
- 12² = 144
- Result: 345 + 5 - 144 = 206

============================================================
DEMO 3: Combined MCP + Function Tools
============================================================

--- Query: Combining external docs + internal guidelines ---
Agent: Here's the combined guidance for Azure Storage in production:

**Official Microsoft Documentation:**
- Use the az storage account create command...

**Internal Company Policy:**
- Use Azure Blob Storage for unstructured data
- Enable geo-redundant storage (GRS) for production
- Use lifecycle management policies...

============================================================
DEMO 4: Agent as MCP Server (Setup Example)
============================================================
Agent has been converted to an MCP server!
...
```

---

## Deep Dive: MCP Architecture

### How MCP Tool Discovery Works

When an agent connects to an MCP server, the following happens:

```
1. Connection    Agent ──────────────► MCP Server
                        "What tools          │
                         do you have?"       │
                                             │
2. Discovery     Agent ◄────────────── MCP Server
                        Tool schemas:        │
                        - search_docs()      │
                        - get_page()         │
                                             │
3. Registration  Agent registers tools with the LLM
                 (same as function tools)
                                             │
4. Invocation    Agent ──────────────► MCP Server
                        "search_docs(        │
                         query='storage')"   │
                                             │
5. Result        Agent ◄────────────── MCP Server
                        Search results...
```

### Security Considerations

When using MCP servers — especially third-party ones — keep these security practices in mind:

1. **Review all data shared** with the MCP server (prompt content is sent with tool calls)
2. **Prefer trusted providers** — use first-party servers like Microsoft Learn
3. **Use authentication headers** for servers that require them
4. **Log tool calls** for auditing purposes
5. **Don't persist API keys** — pass them via `tool_resources` at each run

### Transport Comparison

| Transport | `MCPStdioTool` | `MCPStreamableHTTPTool` | `MCPWebsocketTool` |
|-----------|---------------|------------------------|-------------------|
| **Locality** | Local process | Remote HTTP server | Remote WebSocket |
| **Startup** | Launches child process | Connects to existing server | Connects to existing server |
| **Best for** | Dev tools, local utilities | Cloud-hosted services | Real-time data feeds |
| **Example** | Calculator, file system | Microsoft Learn, GitHub | Market data streams |

---

## Key Takeaways

1. **MCP** is an open standard for connecting agents to external tool servers — no custom integration code needed.
2. **`MCPStreamableHTTPTool`** connects to remote MCP servers over HTTP/SSE (like Microsoft Learn at `https://learn.microsoft.com/api/mcp`).
3. **`MCPStdioTool`** connects to local MCP servers that run as child processes via stdin/stdout.
4. MCP tools work seamlessly alongside custom function tools — combine them freely.
5. **`agent.as_mcp_server()`** exposes your agent as an MCP server, making it discoverable by other MCP clients (VS Code Copilot, other agents).
6. Always use `async with` for MCP tools to ensure proper connection lifecycle management.

---

## What's Next?

In **[Lab 04 — Multi-Turn Conversations](lab-04-multi-turn-conversations.md)**, you'll learn how to give your agent **conversation memory** using sessions, so it remembers context across multiple interactions.

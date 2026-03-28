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
from typing import Annotated

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from pydantic import Field

from agent_framework import Agent, MCPStreamableHTTPTool, MCPStdioTool, tool
from agent_framework.azure import AzureOpenAIResponsesClient

load_dotenv()


async def demo_microsoft_learn_mcp():
    """Demo 1: Microsoft Learn MCP Server (HTTP/SSE)"""
    print("=" * 60)
    print("DEMO 1: Microsoft Learn MCP Server (HTTP/SSE)")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    async with MCPStreamableHTTPTool(
        name="Microsoft Learn MCP",
        url="https://learn.microsoft.com/api/mcp",
    ) as learn_mcp:
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

        print("\n--- Query 1: Azure Storage documentation ---")
        result = await agent.run(
            "How do I create an Azure Storage account using the Azure CLI?"
        )
        print(f"Agent: {result}\n")

        print("--- Query 2: Azure Functions documentation ---")
        result = await agent.run(
            "What are the different hosting plans for Azure Functions?"
        )
        print(f"Agent: {result}\n")


async def demo_local_mcp_calculator():
    """Demo 2: Local Calculator MCP Server (stdio)"""
    print("=" * 60)
    print("DEMO 2: Local Calculator MCP Server (stdio)")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

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
        result = await agent.run("What is (15 * 23) + (45 / 9) - (12 ^ 2)?")
        print(f"Agent: {result}\n")


async def demo_combined_mcp_and_function_tools():
    """Demo 3: Combining MCP tools with custom function tools"""
    print("=" * 60)
    print("DEMO 3: Combined MCP + Function Tools")
    print("=" * 60)

    @tool(description="Get the company's internal Azure architecture guidelines.")
    def get_internal_guidelines(
        topic: Annotated[str, Field(description="Topic: 'storage', 'networking', 'compute'")],
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
            f"No specific internal guidelines found for '{topic}'. Check the company wiki.",
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
    """Demo 4: Expose an Agent as an MCP Server"""
    print("=" * 60)
    print("DEMO 4: Agent as MCP Server (Setup Example)")
    print("=" * 60)

    @tool(description="Get the restaurant's daily specials.")
    def get_specials() -> str:
        """Returns today's specials."""
        return (
            "Today's Specials:\n"
            "- Soup: French Onion\n"
            "- Salad: Mediterranean Quinoa\n"
            "- Entree: Grilled Salmon with Lemon Butter\n"
            "- Dessert: Tiramisu"
        )

    @tool(description="Get the restaurant's menu by category.")
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
    print("To serve it via stdio, you would add:")
    print()
    print("  import anyio")
    print("  from mcp.server.stdio import stdio_server")
    print("  async def serve():")
    print("      async with stdio_server() as (read_stream, write_stream):")
    print("          await mcp_server.run(read_stream, write_stream,")
    print("                               mcp_server.create_initialization_options())")
    print("  anyio.run(serve)")
    print()

    # Direct agent usage still works
    print("--- Direct agent usage still works ---")
    result = await agent.run("What are today's specials and what desserts do you have?")
    print(f"Agent: {result}\n")


async def main():
    await demo_microsoft_learn_mcp()
    await demo_local_mcp_calculator()
    await demo_combined_mcp_and_function_tools()
    await demo_agent_as_mcp_server()


if __name__ == "__main__":
    asyncio.run(main())

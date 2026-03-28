"""
Lab 09 — Group Chat Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - GroupChatBuilder with round-robin speaker selection
  - Agent-based orchestrator for intelligent speaker selection
  - Termination conditions
  - Streaming workflow events with AgentResponseUpdate
  - Maker-checker loop (Writer + Reviewer)
"""

import asyncio
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import AgentResponseUpdate, Message, Role
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

load_dotenv()


async def demo_round_robin():
    """Demo 1: Group Chat with round-robin speaker selection."""
    print("=" * 60)
    print("DEMO 1: Round-Robin Group Chat — Product Review")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    product_manager = client.as_agent(
        name="ProductManager",
        instructions=(
            "You are a Product Manager reviewing a feature proposal. Focus on "
            "user value, market fit, and success criteria. Under 150 words."
        ),
    )

    engineer = client.as_agent(
        name="Engineer",
        instructions=(
            "You are a Senior Engineer reviewing a feature proposal. Focus on "
            "technical feasibility, architecture, and implementation. Under 150 words."
        ),
    )

    designer = client.as_agent(
        name="Designer",
        instructions=(
            "You are a UX Designer reviewing a feature proposal. Focus on "
            "user experience, accessibility, and design consistency. Under 150 words."
        ),
    )

    qa_lead = client.as_agent(
        name="QALead",
        instructions=(
            "You are a QA Lead reviewing a feature proposal. Focus on "
            "test strategy, edge cases, and quality risks. Under 150 words."
        ),
    )

    def round_robin_selector(state: GroupChatState) -> str:
        names = list(state.participants.keys())
        return names[state.current_round % len(names)]

    workflow = GroupChatBuilder(
        participants=[product_manager, engineer, designer, qa_lead],
        termination_condition=lambda conv: len(conv) >= 5,
        selection_func=round_robin_selector,
    ).build()

    task = (
        "Review this feature proposal: Add AI-powered 'Smart Search' to our "
        "e-commerce platform using NLU to let customers describe what they want "
        "in plain English, replacing the existing keyword search."
    )

    print(f"\n📋 Proposal: {task}\n")
    print("-" * 60)

    final_conversation: list[Message] = []
    last_executor_id: str | None = None

    async for event in workflow.run_stream(task):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            eid = event.executor_id
            if eid != last_executor_id:
                if last_executor_id is not None:
                    print()
                print(f"\n🗣️  [{eid}]:", end=" ", flush=True)
                last_executor_id = eid
            print(event.data, end="", flush=True)
        elif event.type == "output":
            final_conversation = cast(list[Message], event.data)

    print("\n\n" + "-" * 60)
    print(f"Discussion ended after {len(final_conversation)} messages.")


async def demo_orchestrator_agent():
    """Demo 2: Group Chat with LLM-based orchestrator (maker-checker)."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Maker-Checker Loop (Writer + Reviewer)")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    writer = client.as_agent(
        name="Writer",
        instructions=(
            "You are a technical writer. Write clear documentation. "
            "When Reviewer gives feedback, revise accordingly. Under 200 words."
        ),
    )

    reviewer = client.as_agent(
        name="Reviewer",
        instructions=(
            "You review documentation for accuracy, clarity, and formatting. "
            "If content is good, say 'APPROVED'. Otherwise give specific feedback. Under 100 words."
        ),
    )

    orchestrator_agent = client.as_agent(
        name="Orchestrator",
        instructions=(
            "Coordinate Writer and Reviewer:\n"
            "- Start with Writer for initial draft\n"
            "- Then Reviewer evaluates\n"
            "- If feedback, send back to Writer\n"
            "- If Reviewer says APPROVED, finish"
        ),
    )

    workflow = GroupChatBuilder(
        participants=[writer, reviewer],
        termination_condition=lambda msgs: (
            len(msgs) >= 6
            or any("APPROVED" in m.text.upper() for m in msgs if m.role == "assistant")
        ),
        orchestrator_agent=orchestrator_agent,
    ).build()

    task = (
        "Write a concise API reference for 'POST /api/users' endpoint — "
        "include parameters, response codes, and example request/response."
    )

    print(f"\n📝 Task: {task}\n")
    print("-" * 60)

    final_conversation: list[Message] = []
    last_executor_id: str | None = None

    async for event in workflow.run_stream(task):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            eid = event.executor_id
            if eid != last_executor_id:
                if last_executor_id is not None:
                    print()
                print(f"\n🗣️  [{eid}]:", end=" ", flush=True)
                last_executor_id = eid
            print(event.data, end="", flush=True)
        elif event.type == "output":
            final_conversation = cast(list[Message], event.data)

    print("\n\n" + "-" * 60)
    print(f"Completed in {len(final_conversation)} messages.")


async def main():
    await demo_round_robin()
    await demo_orchestrator_agent()


if __name__ == "__main__":
    asyncio.run(main())

"""
Lab 10 — Magentic Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - MagenticBuilder for dynamic multi-agent orchestration
  - Manager agent with task ledger
  - Progress tracking with MagenticProgressLedger
  - Streaming intermediate agent outputs
  - Human-in-the-loop plan review
"""

import asyncio
import json
import os
from typing import cast

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agent_framework import Agent, AgentResponseUpdate, Message, WorkflowEvent
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.orchestrations import (
    MagenticBuilder,
    MagenticPlanReviewRequest,
    MagenticPlanReviewResponse,
    MagenticProgressLedger,
)

load_dotenv()


async def demo_basic_magentic():
    """Demo 1: Basic Magentic Orchestration."""
    print("=" * 60)
    print("DEMO 1: Basic Magentic Orchestration")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    researcher = client.as_agent(
        name="ResearcherAgent",
        description="Expert in research and information gathering",
        instructions="You are a Researcher. Gather factual, well-structured research notes. Be thorough but concise.",
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Expert in data analysis and quantitative reasoning",
        instructions="You are a Data Analyst. Analyze data, create comparisons, identify trends. Use tables when helpful.",
    )

    writer = client.as_agent(
        name="WriterAgent",
        description="Expert in writing clear, polished reports",
        instructions="You are a Report Writer. Synthesize research into a well-structured report with executive summary.",
    )

    manager = client.as_agent(
        name="MagenticManager",
        description="Orchestrator that coordinates the research team",
        instructions="You coordinate Researcher, Analyst, and Writer to produce comprehensive reports.",
    )

    workflow = MagenticBuilder(
        participants=[researcher, analyst, writer],
        intermediate_outputs=True,
        manager_agent=manager,
        max_round_count=10,
        max_stall_count=3,
        max_reset_count=2,
    ).build()

    task = (
        "Create a comparative analysis report on AWS, Azure, and GCP for AI/ML workloads. "
        "Compare AI services, pricing, and unique strengths. Recommend the best choice "
        "for a mid-size company starting their AI journey."
    )

    print(f"\n📋 Task: {task}\n")
    print("-" * 60)

    last_message_id: str | None = None
    output_event: WorkflowEvent | None = None

    async for event in workflow.run(task, stream=True):
        if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
            message_id = event.data.message_id
            if message_id != last_message_id:
                if last_message_id is not None:
                    print("\n")
                print(f"🤖 [{event.executor_id}]:", end=" ", flush=True)
                last_message_id = message_id
            print(event.data, end="", flush=True)
        elif event.type == "magentic_orchestrator":
            print(f"\n\n📊 [Orchestrator] {event.data.event_type.name}")
            if isinstance(event.data.content, Message):
                print(f"   Plan: {event.data.content.text[:200]}...")
            elif isinstance(event.data.content, MagenticProgressLedger):
                print(f"   Ledger: {json.dumps(event.data.content.to_dict(), indent=2)[:300]}...")
        elif event.type == "output":
            output_event = event

    if output_event:
        output_messages = cast(list[Message], output_event.data)
        print("\n\n" + "=" * 60)
        print("📄 FINAL REPORT")
        print("=" * 60)
        print(output_messages[-1].text if output_messages else "No output")


async def demo_magentic_with_plan_review():
    """Demo 2: Magentic with HITL Plan Review."""
    print("\n\n" + "=" * 60)
    print("DEMO 2: Magentic with HITL Plan Review")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    researcher = client.as_agent(
        name="ResearcherAgent",
        description="Research specialist",
        instructions="You are a Researcher. Gather comprehensive information. Be concise.",
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Analysis specialist",
        instructions="You are a Data Analyst. Analyze data and identify trends.",
    )

    manager = client.as_agent(
        name="MagenticManager",
        description="Team orchestrator",
        instructions="You coordinate Researcher and Analyst efficiently.",
    )

    workflow = MagenticBuilder(
        participants=[researcher, analyst],
        intermediate_outputs=True,
        enable_plan_review=True,
        manager_agent=manager,
        max_round_count=8,
        max_stall_count=2,
        max_reset_count=1,
    ).build()

    task = (
        "Research the current state of quantum computing in 2026 and analyze "
        "which industries will be most impacted in the next 5 years."
    )

    print(f"\n📋 Task: {task}\n")

    pending_request: WorkflowEvent | None = None
    pending_responses: dict[str, MagenticPlanReviewResponse] | None = None
    output_event: WorkflowEvent | None = None

    while not output_event:
        if pending_responses is not None:
            stream = workflow.run(stream=True, responses=pending_responses)
        else:
            stream = workflow.run(task, stream=True)

        last_message_id: str | None = None
        async for event in stream:
            if event.type == "output" and isinstance(event.data, AgentResponseUpdate):
                message_id = event.data.message_id
                if message_id != last_message_id:
                    if last_message_id is not None:
                        print("\n")
                    print(f"🤖 [{event.executor_id}]:", end=" ", flush=True)
                    last_message_id = message_id
                print(event.data, end="", flush=True)
            elif event.type == "request_info" and event.request_type is MagenticPlanReviewRequest:
                pending_request = event
            elif event.type == "output":
                output_event = event

        pending_responses = None

        if pending_request is not None:
            event_data = cast(MagenticPlanReviewRequest, pending_request.data)
            print(f"\n\n📋 PLAN REVIEW: {event_data.plan.text[:300]}...")
            print("✅ Plan auto-approved for demo.")
            pending_responses = {pending_request.request_id: event_data.approve()}
            pending_request = None

    if output_event:
        output_messages = cast(list[Message], output_event.data)
        print("\n\n" + "=" * 60)
        print("📄 FINAL REPORT")
        print("=" * 60)
        print(output_messages[-1].text[:1000] if output_messages else "No output")


async def main():
    await demo_basic_magentic()
    await demo_magentic_with_plan_review()


if __name__ == "__main__":
    asyncio.run(main())

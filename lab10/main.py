"""
Lab 10 — Magentic Orchestration
Microsoft Agent Framework Workshop

Demonstrates:
  - MagenticBuilder for dynamic multi-agent orchestration
  - Manager agent that creates and adapts plans
  - Progress tracking with MagenticProgressLedger
  - Clear visibility into plan → delegate → assess cycle
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


def print_magentic_events(result) -> list[Message]:
    """Print Magentic orchestration events showing the plan-delegate-assess cycle."""
    conversation: list[Message] = []
    round_num = 0
    current_agent: str | None = None

    for event in result:
        # Manager creates or updates the plan
        if event.type == "magentic_orchestrator":
            data = event.data
            event_name = data.event_type.name if hasattr(data.event_type, 'name') else str(data.event_type)

            if isinstance(data.content, Message) and data.content.text:
                print(f"\n{'=' * 60}")
                print(f"  [Manager] {event_name}")
                print(f"{'=' * 60}")
                plan_text = data.content.text
                if len(plan_text) > 500:
                    plan_text = plan_text[:500] + "..."
                print(f"  {plan_text}")

            elif isinstance(data.content, MagenticProgressLedger):
                ledger = data.content.to_dict()
                print(f"\n{'─' * 60}")
                print(f"  [Manager] Progress Assessment")
                print(f"{'─' * 60}")
                if "is_request_satisfied" in ledger:
                    satisfied = ledger["is_request_satisfied"]
                    print(f"  Task complete: {'Yes' if satisfied.get('answer') else 'No'}")
                    if satisfied.get("reason"):
                        print(f"  Reason: {satisfied['reason']}")
                if "next_speaker" in ledger:
                    ns = ledger["next_speaker"]
                    next_agent = ns.get("answer", "unknown")
                    reason = ns.get("reason", "")
                    print(f"  Next agent: {next_agent}")
                    print(f"  Why: {reason}")

        # Agent is invoked — show the delegation
        elif event.type == "executor_invoked" and event.executor_id:
            agent = event.executor_id
            if agent != current_agent and agent != "magentic_orchestrator":
                round_num += 1
                current_agent = agent
                print(f"\n{'━' * 60}")
                print(f"  Round {round_num} │ Manager delegates to: {agent}")
                print(f"{'━' * 60}")

        # Agent produces output — show a summary
        elif event.type == "output" and isinstance(event.data, list):
            conversation = event.data

        elif event.type == "executor_completed" and event.executor_id:
            agent = event.executor_id
            if agent != "magentic_orchestrator" and event.data:
                if hasattr(event.data, '__iter__'):
                    for item in event.data:
                        if hasattr(item, 'agent_response') and hasattr(item.agent_response, 'text'):
                            text = item.agent_response.text
                            if text:
                                preview = text[:300] + "..." if len(text) > 300 else text
                                print(f"  [{agent}] output: {preview}")

    return conversation


async def demo_basic_magentic():
    """Demo 1: Basic Magentic Orchestration without HITL."""
    print("=" * 60)
    print("DEMO 1: Magentic Orchestration — Plan, Delegate, Assess")
    print("=" * 60)

    client = AzureOpenAIResponsesClient(
        project_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
        credential=DefaultAzureCredential(),
    )

    researcher = client.as_agent(
        name="ResearcherAgent",
        description="Expert in research and information gathering",
        instructions=(
            "You are a Researcher. Gather comprehensive information on the topic. "
            "Provide factual, well-structured research notes with key data points, "
            "statistics, and relevant context. Be thorough but concise."
        ),
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Expert in data analysis and quantitative reasoning",
        instructions=(
            "You are a Data Analyst. Analyze data, perform calculations, "
            "create comparisons, and identify trends. Present findings in "
            "structured format with tables when helpful."
        ),
    )

    writer = client.as_agent(
        name="WriterAgent",
        description="Expert in writing clear, polished reports",
        instructions=(
            "You are a professional Report Writer. Synthesize research and "
            "analysis into a well-structured, readable report. Include an "
            "executive summary, key findings, and recommendations."
        ),
    )

    manager = client.as_agent(
        name="MagenticManager",
        description="Orchestrator that coordinates the research team",
        instructions=(
            "You coordinate a team of Researcher, Analyst, and Writer "
            "to produce comprehensive reports. Break tasks into clear steps "
            "and assign them to the right specialist."
        ),
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
        "Create a comparative analysis report on the three main cloud providers "
        "(AWS, Azure, GCP) for AI/ML workloads. Compare their AI services, "
        "pricing models, and unique strengths. Recommend the best choice for "
        "a mid-size company starting their AI journey."
    )

    print(f"\n📋 Task: {task}\n")
    print("-" * 60)
    print("  The Manager will now plan, delegate to agents, assess progress,")
    print("  and iterate until the task is complete.")
    print("-" * 60)

    conversation: list[Message] = []
    round_num = 0
    current_agent: str | None = None

    async for event in workflow.run(task, stream=True):
        # Manager creates or updates the plan
        if event.type == "magentic_orchestrator":
            data = event.data
            event_name = data.event_type.name if hasattr(data.event_type, 'name') else str(data.event_type)

            if isinstance(data.content, Message) and data.content.text:
                print(f"\n{'=' * 60}")
                print(f"  [Manager] {event_name}")
                print(f"{'=' * 60}")
                plan_text = data.content.text
                if len(plan_text) > 500:
                    plan_text = plan_text[:500] + "..."
                print(f"  {plan_text}", flush=True)

            elif isinstance(data.content, MagenticProgressLedger):
                ledger = data.content.to_dict()
                print(f"\n{'─' * 60}")
                print(f"  [Manager] Progress Assessment")
                print(f"{'─' * 60}")
                if "is_request_satisfied" in ledger:
                    satisfied = ledger["is_request_satisfied"]
                    print(f"  Task complete: {'Yes' if satisfied.get('answer') else 'No'}")
                    if satisfied.get("reason"):
                        print(f"  Reason: {satisfied['reason']}")
                if "next_speaker" in ledger:
                    ns = ledger["next_speaker"]
                    next_agent = ns.get("answer", "unknown")
                    reason = ns.get("reason", "")
                    print(f"  Next agent: {next_agent}")
                    print(f"  Why: {reason}", flush=True)

        # Agent is invoked
        elif event.type == "executor_invoked" and event.executor_id:
            agent = event.executor_id
            if agent != current_agent and agent != "magentic_orchestrator":
                round_num += 1
                current_agent = agent
                print(f"\n{'━' * 60}")
                print(f"  Round {round_num} │ Manager delegates to: {agent}")
                print(f"{'━' * 60}", flush=True)

        # Agent completed
        elif event.type == "executor_completed" and event.executor_id:
            agent = event.executor_id
            if agent != "magentic_orchestrator" and event.data:
                if hasattr(event.data, '__iter__'):
                    for item in event.data:
                        if hasattr(item, 'agent_response') and hasattr(item.agent_response, 'text'):
                            text = item.agent_response.text
                            if text:
                                preview = text[:300] + "..." if len(text) > 300 else text
                                print(f"  [{agent}] output: {preview}", flush=True)

        # Final output
        elif event.type == "output" and isinstance(event.data, list):
            conversation = event.data

    if conversation:
        final_text = ""
        for msg in reversed(conversation):
            if msg.role == "assistant" and msg.text:
                final_text = msg.text
                break
        print("\n\n" + "=" * 60)
        print("  FINAL REPORT")
        print("=" * 60)
        if final_text:
            print(f"\n  {final_text[:1500]}")
            if len(final_text) > 1500:
                print("  ... (truncated)")
        print("\n" + "=" * 60)


async def demo_magentic_with_plan_review():
    """Demo 2: Magentic with Human-in-the-Loop Plan Review."""
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
        description="Expert in research and information gathering",
        instructions="You are a Researcher. Gather comprehensive information. Be thorough but concise.",
    )

    analyst = client.as_agent(
        name="AnalystAgent",
        description="Expert in data analysis",
        instructions="You are a Data Analyst. Analyze data and identify trends.",
    )

    manager = client.as_agent(
        name="MagenticManager",
        description="Orchestrator for the research team",
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
        "Research the current state of quantum computing in 2026 "
        "and analyze which industries will be most impacted in the next 5 years."
    )

    print(f"\n📋 Task: {task}\n")
    print("-" * 60)

    pending_request: WorkflowEvent | None = None
    pending_responses: dict[str, MagenticPlanReviewResponse] | None = None
    conversation: list[Message] = []
    done = False

    while not done:
        if pending_responses is not None:
            stream = workflow.run(responses=pending_responses, stream=True)
        else:
            stream = workflow.run(task, stream=True)

        round_num = 0
        current_agent: str | None = None

        async for event in stream:
            if event.type == "magentic_orchestrator":
                data = event.data
                event_name = data.event_type.name if hasattr(data.event_type, 'name') else str(data.event_type)
                if isinstance(data.content, Message) and data.content.text:
                    print(f"\n{'=' * 60}")
                    print(f"  [Manager] {event_name}")
                    print(f"{'=' * 60}")
                    plan_text = data.content.text
                    if len(plan_text) > 500:
                        plan_text = plan_text[:500] + "..."
                    print(f"  {plan_text}", flush=True)
                elif isinstance(data.content, MagenticProgressLedger):
                    ledger = data.content.to_dict()
                    print(f"\n{'─' * 60}")
                    print(f"  [Manager] Progress Assessment")
                    print(f"{'─' * 60}")
                    if "is_request_satisfied" in ledger:
                        satisfied = ledger["is_request_satisfied"]
                        print(f"  Task complete: {'Yes' if satisfied.get('answer') else 'No'}")
                        if satisfied.get("reason"):
                            print(f"  Reason: {satisfied['reason']}")
                    if "next_speaker" in ledger:
                        ns = ledger["next_speaker"]
                        print(f"  Next agent: {ns.get('answer', 'unknown')}")
                        print(f"  Why: {ns.get('reason', '')}", flush=True)

            elif event.type == "executor_invoked" and event.executor_id:
                agent = event.executor_id
                if agent != current_agent and agent != "magentic_orchestrator":
                    round_num += 1
                    current_agent = agent
                    print(f"\n{'━' * 60}")
                    print(f"  Round {round_num} │ Manager delegates to: {agent}")
                    print(f"{'━' * 60}", flush=True)

            elif event.type == "executor_completed" and event.executor_id:
                agent = event.executor_id
                if agent != "magentic_orchestrator" and event.data:
                    if hasattr(event.data, '__iter__'):
                        for item in event.data:
                            if hasattr(item, 'agent_response') and hasattr(item.agent_response, 'text'):
                                text = item.agent_response.text
                                if text:
                                    preview = text[:300] + "..." if len(text) > 300 else text
                                    print(f"  [{agent}] output: {preview}", flush=True)

            elif event.type == "request_info" and event.request_type is MagenticPlanReviewRequest:
                pending_request = event

            elif event.type == "output" and isinstance(event.data, list):
                conversation = event.data
                done = True

        pending_responses = None

        # Handle plan review request
        if pending_request is not None:
            event_data = cast(MagenticPlanReviewRequest, pending_request.data)
            print("\n" + "=" * 60)
            print("  [HITL] PLAN REVIEW REQUEST")
            print("=" * 60)

            if event_data.current_progress is not None:
                ledger = event_data.current_progress.to_dict()
                print("  Current Progress:")
                print(f"  {json.dumps(ledger, indent=2)[:500]}")

            plan_text = event_data.plan.text[:500] if event_data.plan.text else "(empty)"
            print(f"\n  Proposed Plan:\n  {plan_text}")

            # Auto-approve for demo (in real apps, await human input)
            print("\n  [HITL] Plan auto-approved for demo.")
            pending_responses = {pending_request.request_id: event_data.approve()}
            pending_request = None

    if conversation:
        final_text = ""
        for msg in reversed(conversation):
            if msg.role == "assistant" and msg.text:
                final_text = msg.text
                break
        print("\n\n" + "=" * 60)
        print("  FINAL REPORT")
        print("=" * 60)
        if final_text:
            print(f"\n  {final_text[:1000]}")
            if len(final_text) > 1000:
                print("  ... (truncated)")
        print("\n" + "=" * 60)


async def main():
    await demo_basic_magentic()
    await demo_magentic_with_plan_review()


if __name__ == "__main__":
    asyncio.run(main())
